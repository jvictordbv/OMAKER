import json

import pytest

from omaker.domain.entities import Entity
from omaker.llm.client import OllamaClient
from omaker.llm.entities import extract_entities_llm, merge_entities
from omaker.llm.taxonomy import TAXONOMY_TEXT_LIMIT
from omaker.pipeline import engine as he

TEXT = "Aspirin prevents stroke. Chemotherapy treats the tumor but causes nausea. Aspirin and fever were listed."


def ent(word, typ, nth=0):
    i = -1
    for _ in range(nth + 1):
        i = TEXT.index(word, i + 1)
    return Entity(word, i, i + len(word), typ, 0.99)


LLM_ENTITIES = json.dumps({"entities": [
    {"text": "Aspirin", "type": "DRUG"}, {"text": "stroke", "type": "DISEASE"},
    {"text": "chemotherapy", "type": "DRUG"}, {"text": "tumor", "type": "DISEASE"},
    {"text": "nausea", "type": "SYMPTOM"}, {"text": "fever", "type": "SYMPTOM"},
    {"text": "cancer", "type": "DISEASE"},                      # hallucinated: not in the text
    {"text": "ever", "type": "SYMPTOM"},                        # substring of "fever": must not match
]})


@pytest.fixture
def weak_ner(stub_ner):
    """Like the real DistilBERT on short sentences: only drug names."""
    ner = stub_ner([ent("Aspirin", "DRUG"), ent("Chemotherapy", "DRUG")])
    ner.last_rejected = [("tumor", "Coreference", 0.92)]
    return ner


def test_taxonomy_validation_rejects_bad_llm_output(fake_ollama, stub_ner, monkeypatch):
    # LLM answers, in call order: pair classification (no PURE checkpoint here), then taxonomy.
    # Deliberately includes bad output: a class named like an entity, an unknown parent, a cycle,
    # a Drug entity put under a Disease subclass, and a disjoint group of ancestor/descendant.
    pairs_answer = json.dumps({"results": [
        {"id": 0, "relation": "prevents"},   # Aspirin -> stroke
        {"id": 1, "relation": "treats"},     # Chemotherapy -> tumor
        {"id": 2, "relation": "causes"},     # Chemotherapy -> nausea
        {"id": 3, "relation": "treats"},     # Aspirin -> fever (co-occurrence only, but the LLM said treats)
        {"id": 99, "relation": "causes"},    # out of range: must be ignored
    ]})
    tax_answer = json.dumps({
        "classes": [{"name": "analgesic", "parent": "Drug"}, {"name": "Cancer", "parent": "Disease"},
                    {"name": "Aspirin", "parent": "Analgesic"},          # duplicates an entity name
                    {"name": "Weird", "parent": "DoesNotExist"},          # unknown parent
                    {"name": "LoopA", "parent": "LoopB"}, {"name": "LoopB", "parent": "LoopA"},
                    {"name": "Drug", "parent": "Thing"}],                 # redefining a base class
        "instances": [{"name": "Aspirin", "class": "Aspirin"}, {"name": "tumor", "class": "Cancer"},
                      {"name": "Chemotherapy", "class": "Cancer"},        # wrong branch for a DRUG
                      {"name": "ghost entity", "class": "Drug"}],         # not in NER list
        "disjoint": [["Analgesic", "Drug"], ["Analgesic", "Cancer"]],
    })
    ner = stub_ner([ent("Aspirin", "DRUG"), ent("stroke", "DISEASE"), ent("Chemotherapy", "DRUG"),
                    ent("tumor", "DISEASE"), ent("nausea", "SYMPTOM"), ent("Aspirin", "DRUG", 1),
                    ent("fever", "SYMPTOM")])
    fake_ollama.script[:] = [pairs_answer, tax_answer]
    logs = []
    monkeypatch.setenv("OMAKER_ENTITIES", "ner")   # entities from the NER model only
    tax, triples = he.HybridEngine.extrair(TEXT, "qwen3:8b", 0.1, logs.append, ner=ner,
                                           client=OllamaClient("qwen3:8b", fake_ollama.host))

    assert tax["classes"]["Analgesic"] == "Drug"
    assert "Aspirin" not in tax["classes"] and "Drug" not in tax["classes"]
    assert tax["classes"]["Weird"] == "BiomedicalEntity"
    assert tax["classes"]["LoopA"] == "BiomedicalEntity" or tax["classes"]["LoopB"] == "BiomedicalEntity"
    assert tax["instances"]["Aspirin"] == "Analgesic"        # redirected to the entity-named class's parent
    assert tax["instances"]["tumor"] == "Cancer"
    assert tax["instances"]["Chemotherapy"] == "Drug"        # Cancer branch rejected for a DRUG
    assert "ghost entity" not in tax["instances"]
    assert tax["disjoint"] == [["Analgesic", "Cancer"]]
    assert len(triples) == 3 and {t[2] for t in triples} == {"prevents", "treats", "causes"}
    assert any("SKIP" in line and "tumor" in line for line in logs)   # DISEASE "treats" rejected by the domain filter


def test_llm_entities_are_verified_in_text(fake_ollama, weak_ner):
    fake_ollama.script[:] = [LLM_ENTITIES]
    verified = extract_entities_llm(OllamaClient("qwen3:8b", fake_ollama.host), TEXT)
    words = sorted(v.text.lower() for v in verified)
    assert "cancer" not in words and "ever" not in words, words
    assert words.count("aspirin") == 2 and {"stroke", "tumor", "nausea", "fever", "chemotherapy"} <= set(words)

    merged = merge_entities(weak_ner.extract(TEXT), verified)
    assert not any(a.start < b.end and b.start < a.end
                   for i, a in enumerate(merged) for b in merged[i + 1:])  # no overlaps


def test_merge_both_sources(fake_ollama, weak_ner, monkeypatch):
    monkeypatch.setenv("OMAKER_ENTITIES", "both")
    fake_ollama.script[:] = [LLM_ENTITIES, json.dumps({"results": []}),
                             json.dumps({"classes": [], "instances": [], "disjoint": []})]
    logs2 = []
    tax2, _triples2 = he.HybridEngine.extrair(TEXT, "qwen3:8b", 0.1, logs2.append, ner=weak_ner,
                                              client=OllamaClient("qwen3:8b", fake_ollama.host))
    assert any("6 unique entities" in line for line in logs2), logs2
    assert any("ignored: 'tumor'" in line for line in logs2)
    assert set(tax2["instances"]) == {"Aspirin", "stroke", "Chemotherapy", "tumor", "nausea", "fever"}


def test_engine_entry_points_take_no_api_key():
    import inspect
    for fn in (he.HybridEngine.gerar_ontologia, he.HybridEngine.atualizar_ontologia):
        assert "api_key" not in inspect.signature(fn).parameters


EMPTY_TAX = {"classes": {}, "instances": {}, "disjoint": []}


def test_atualizar_forwards_model_and_temperature(monkeypatch, tmp_path):
    from omaker.ontology import builder as owl_builder
    seen = {}
    monkeypatch.setattr(he.HybridEngine, "extrair",
                        staticmethod(lambda texto, modelo, temp, log, **k: seen.update(m=modelo, t=temp) or (EMPTY_TAX, [])))
    monkeypatch.setattr(owl_builder, "load_world_ontology", lambda path: (object(), object()))
    monkeypatch.setattr(owl_builder, "populate", lambda onto, tax, triples, log=print: 0)
    monkeypatch.setattr(owl_builder, "run_reasoner", lambda world, log=print, java_exe="": owl_builder.ReasonerStatus.UNAVAILABLE)
    monkeypatch.setattr(owl_builder, "save", lambda onto, path: path)
    he.HybridEngine.atualizar_ontologia(str(tmp_path / "a.owl"), "txt", lambda m: None, modelo_llm="x:1b", temp_llm=0.3)
    assert seen == {"m": "x:1b", "t": 0.3}


@pytest.mark.parametrize("extra, truncated", [(0, False), (300, True)])
def test_taxonomy_text_truncation_is_logged(fake_ollama, stub_ner, monkeypatch, tmp_path, extra, truncated):
    text = TEXT + " Filler sentence about nothing." * extra
    ner = stub_ner([ent("Aspirin", "DRUG"), ent("stroke", "DISEASE")])
    fake_ollama.script[:] = [
        json.dumps({"results": [{"id": 0, "relation": "prevents"}]}),
        json.dumps({"classes": [], "instances": [], "disjoint": []}),
    ]
    monkeypatch.setenv("OMAKER_ENTITIES", "ner")
    monkeypatch.setattr(he, "default_checkpoint_path", lambda: tmp_path / "nao-existe.pt")
    logs = []
    he.HybridEngine.extrair(text, "qwen3:8b", 0.1, logs.append, ner=ner,
                            client=OllamaClient("qwen3:8b", fake_ollama.host))

    prompt = fake_ollama.calls[-1]["messages"][-1]["content"]
    warned = [line for line in logs if "[WARNING]" in line]
    if truncated:
        assert len(text) > TAXONOMY_TEXT_LIMIT
        assert len(warned) == 1 and str(len(text)) in warned[0] and str(TAXONOMY_TEXT_LIMIT) in warned[0]
        assert text[: TAXONOMY_TEXT_LIMIT] in prompt and text not in prompt
    else:
        assert warned == []
        assert text in prompt


LOOPING = {"content": '{"entities": [{"text": "Aspirin", "type": "DRUG"}, ', "done_reason": "length"}


def test_llm_entity_loop_falls_back_to_ner_entities(fake_ollama, weak_ner, monkeypatch):
    monkeypatch.setenv("OMAKER_ENTITIES", "both")
    fake_ollama.script[:] = [LOOPING, json.dumps({"results": []}),
                             json.dumps({"classes": [], "instances": [], "disjoint": []})]
    logs = []
    tax, _triples = he.HybridEngine.extrair(TEXT, "qwen3:8b", 0.1, logs.append, ner=weak_ner,
                                            client=OllamaClient("qwen3:8b", fake_ollama.host))
    assert any("[LLM-NER]" in line and "NER entities only" in line for line in logs), logs
    assert set(tax["instances"]) == {"Aspirin", "Chemotherapy"}


def test_llm_entity_loop_is_an_error_when_the_llm_is_the_only_source(fake_ollama, weak_ner, monkeypatch):
    from omaker.llm.client import LLMError
    monkeypatch.setenv("OMAKER_ENTITIES", "llm")
    fake_ollama.script[:] = [LOOPING]
    with pytest.raises(LLMError):
        he.HybridEngine.extrair(TEXT, "qwen3:8b", 0.1, lambda _m: None, ner=weak_ner,
                                client=OllamaClient("qwen3:8b", fake_ollama.host))


def test_pure_uses_the_calibrated_threshold(fake_ollama, stub_ner, monkeypatch, tmp_path):
    """Com calibração, o limite de confiança vem dela, e não do 0,70 fixo."""
    from types import SimpleNamespace

    from omaker.relations import model as pure_model
    ckpt = tmp_path / "model.pt"
    ckpt.write_bytes(b"x")
    monkeypatch.setattr(he, "default_checkpoint_path", lambda: ckpt)
    monkeypatch.setenv("OMAKER_ENTITIES", "ner")
    ner = stub_ner([ent("Aspirin", "DRUG"), ent("stroke", "DISEASE")])

    def run(threshold):
        fake = SimpleNamespace(threshold=threshold, predict=lambda pairs: [("prevents", 0.6)] * len(pairs))
        monkeypatch.setattr(pure_model.RelationExtractorPURE, "load", classmethod(lambda cls, path, device=None: fake))
        _tax, triples = he.HybridEngine.extrair(TEXT, "qwen3:8b", 0.1, lambda _m: None, ner=ner, with_taxonomy=False,
                                                client=OllamaClient("qwen3:8b", fake_ollama.host))
        return [(t[0], t[2], t[3]) for t in triples]

    assert run(None) == []                                   # sem calibração: 0,6 < 0,70
    assert run(0.5) == [("Aspirin", "prevents", "stroke")]   # calibrado: 0,6 >= 0,5


def test_missing_checkpoint_is_downloaded_before_falling_back_to_the_llm(fake_ollama, stub_ner, monkeypatch,
                                                                         tmp_path):
    from omaker.relations import download
    monkeypatch.setenv("OMAKER_ENTITIES", "ner")
    monkeypatch.setattr(he, "default_checkpoint_path", lambda: tmp_path / "omaker_pure.pt")
    asked = []
    monkeypatch.setattr(download, "ensure_pure_checkpoint", lambda dest, log: asked.append(dest) or False)
    fake_ollama.script[:] = [json.dumps({"results": [{"id": 0, "relation": "prevents"}]})]
    ner = stub_ner([ent("Aspirin", "DRUG"), ent("stroke", "DISEASE")])
    _tax, triples = he.HybridEngine.extrair(TEXT, "qwen3:8b", 0.1, lambda _m: None, ner=ner, with_taxonomy=False,
                                            client=OllamaClient("qwen3:8b", fake_ollama.host))
    assert asked == [tmp_path / "omaker_pure.pt"]                                          # tentou baixar
    assert [(t[0], t[2], t[3]) for t in triples] == [("Aspirin", "prevents", "stroke")]   # e caiu no LLM


def test_updater_keeps_a_backup_of_the_original_owl(monkeypatch, tmp_path):
    """O Atualizador sobrescreve o .owl; antes, guarda uma cópia do original ao lado dele."""
    from omaker.ontology import builder as owl_builder
    original = tmp_path / "a.owl"
    original.write_text("<rdf>original</rdf>", encoding="utf-8")
    monkeypatch.setattr(he.HybridEngine, "extrair", staticmethod(lambda texto, modelo, temp, log, **k: (EMPTY_TAX, [])))
    monkeypatch.setattr(owl_builder, "load_world_ontology", lambda path: (object(), object()))
    monkeypatch.setattr(owl_builder, "populate", lambda onto, tax, triples, log=print: 0)
    monkeypatch.setattr(owl_builder, "run_reasoner", lambda world, log=print, java_exe="": owl_builder.ReasonerStatus.UNAVAILABLE)
    monkeypatch.setattr(owl_builder, "save", lambda onto, path: open(path, "w", encoding="utf-8").write("<rdf>novo</rdf>"))
    logs = []
    he.HybridEngine.atualizar_ontologia(str(original), "txt", logs.append)
    (backup,) = tmp_path.glob("a.backup-*.owl")
    assert backup.read_text(encoding="utf-8") == "<rdf>original</rdf>"
    assert original.read_text(encoding="utf-8") == "<rdf>novo</rdf>"
    assert any(backup.name in line for line in logs), logs


def test_ollama_is_not_required_when_no_step_uses_the_llm(stub_ner, monkeypatch, tmp_path):
    """Modo ner, com o PURE e sem taxonomia (a avaliação do sistema pure): nada chama o LLM, então nada confere o Ollama."""
    from types import SimpleNamespace

    from omaker.relations import model as pure_model
    ckpt = tmp_path / "model.pt"
    ckpt.write_bytes(b"x")
    monkeypatch.setattr(he, "default_checkpoint_path", lambda: ckpt)
    monkeypatch.setenv("OMAKER_ENTITIES", "ner")
    fake = SimpleNamespace(threshold=None, predict=lambda pairs: [("prevents", 0.9)] * len(pairs))
    monkeypatch.setattr(pure_model.RelationExtractorPURE, "load", classmethod(lambda cls, path, device=None: fake))

    def no_ollama(*a, **k):
        raise AssertionError("o Ollama não deveria ser conferido")

    monkeypatch.setattr(he.HybridEngine, "_client", staticmethod(no_ollama))
    ner = stub_ner([ent("Aspirin", "DRUG"), ent("stroke", "DISEASE")])
    _tax, triples = he.HybridEngine.extrair(TEXT, "qwen3:8b", 0.1, lambda _m: None, ner=ner, with_taxonomy=False)
    assert [(t[0], t[2], t[3]) for t in triples] == [("Aspirin", "prevents", "stroke")]


def test_llm_client_is_created_once_when_needed(fake_ollama, stub_ner, monkeypatch, tmp_path):
    monkeypatch.setenv("OMAKER_ENTITIES", "ner")
    monkeypatch.setattr(he, "default_checkpoint_path", lambda: tmp_path / "nao-existe.pt")
    created = []

    def make(modelo, temp, log):
        created.append(modelo)
        return OllamaClient("qwen3:8b", fake_ollama.host)

    monkeypatch.setattr(he.HybridEngine, "_client", staticmethod(make))
    fake_ollama.script[:] = [json.dumps({"results": [{"id": 0, "relation": "prevents"}]}),
                             json.dumps({"classes": [], "instances": [], "disjoint": []})]
    ner = stub_ner([ent("Aspirin", "DRUG"), ent("stroke", "DISEASE")])
    he.HybridEngine.extrair(TEXT, "qwen3:8b", 0.1, lambda _m: None, ner=ner)   # relações e taxonomia pelo LLM
    assert created == ["qwen3:8b"]
