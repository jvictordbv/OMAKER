"""HybridEngine.extrair: temperatura das entidades, texto sem entidades, texto sem pares e uma tripla por fato."""
import json
from types import SimpleNamespace

import pytest

from omaker.domain.entities import Entity
from omaker.llm.client import OllamaClient
from omaker.pipeline import engine as he

EMPTY_TAX_ANSWER = json.dumps({"classes": [], "instances": [], "disjoint": []})
NO_ENTITIES_MESSAGE = "No biomedical entities (drug / symptom / disease) were found in the text."


def ent(text, word, typ, nth=0, score=0.99):
    i = -1
    for _ in range(nth + 1):
        i = text.index(word, i + 1)
    return Entity(word, i, i + len(word), typ, score)


def _fake_pure(monkeypatch, tmp_path, predict, threshold=0.5):
    """Checkpoint "existente" e um PURE falso cujo predict(pairs) devolve [(rótulo, confiança)]."""
    from omaker.relations import model as pure_model

    ckpt = tmp_path / "model.pt"
    ckpt.write_bytes(b"x")
    monkeypatch.setattr(he, "default_checkpoint_path", lambda: ckpt)
    fake = SimpleNamespace(threshold=threshold, predict=predict)
    monkeypatch.setattr(pure_model.RelationExtractorPURE, "load", classmethod(lambda cls, path, device=None: fake))


# ---- ENT-10: temperatura das entidades pelo LLM
@pytest.mark.parametrize("configured, sent", [(0.8, 0.1), (0.1, 0.1), (0.05, 0.05), (0.0, 0.0)])
def test_entities_are_asked_with_the_configured_temperature_capped_at_0_1(fake_ollama, monkeypatch, configured, sent):
    monkeypatch.setenv("OMAKER_ENTITIES", "llm")
    fake_ollama.script[:] = [json.dumps({"entities": [{"text": "Aspirin", "type": "DRUG"}]})]
    he.HybridEngine.extrair("Aspirin was given.", "qwen3:8b", configured, lambda _m: None, with_taxonomy=False,
                            client=OllamaClient("qwen3:8b", fake_ollama.host))
    (call,) = fake_ollama.calls   # um único entity: nenhum par, então nenhum pedido de relações
    assert call["options"]["temperature"] == pytest.approx(sent)


# ---- ENT-13: texto sem entidades
@pytest.mark.parametrize("source", ["ner", "both"])
def test_generation_without_entities_fails_with_the_message_and_writes_no_owl(fake_ollama, monkeypatch, tmp_path,
                                                                             source):
    from omaker.nlp import ner as ner_mod

    monkeypatch.setenv("OMAKER_ENTITIES", source)
    monkeypatch.setattr(ner_mod, "BiomedicalNER", lambda *a, **k: SimpleNamespace(extract=lambda _t: [],
                                                                                   last_rejected=[]))
    monkeypatch.setattr(he.HybridEngine, "_client",
                        staticmethod(lambda modelo, temp, log: OllamaClient("qwen3:8b", fake_ollama.host)))
    fake_ollama.script[:] = [json.dumps({"entities": []})]   # o LLM (modo both) também não acha nada
    out = tmp_path / "saida"
    with pytest.raises(ValueError) as exc:
        he.HybridEngine.gerar_ontologia("The weather was sunny and the meeting ended early.", "vazio", "qwen3:8b",
                                        0.1, str(out), "", lambda _m: None)
    assert str(exc.value) == NO_ENTITIES_MESSAGE
    assert list(tmp_path.rglob("*.owl")) == []


# ---- REL-03: texto sem pares
def test_text_without_pairs_loads_downloads_and_calls_no_classifier(fake_ollama, stub_ner, monkeypatch, tmp_path):
    from omaker.relations import download
    from omaker.relations import model as pure_model

    def forbidden(name):
        def fn(*a, **k):
            raise AssertionError(f"{name} não deveria ser chamado sem pares")
        return fn

    monkeypatch.setenv("OMAKER_ENTITIES", "ner")
    monkeypatch.setattr(he, "default_checkpoint_path", forbidden("default_checkpoint_path"))
    monkeypatch.setattr(download, "ensure_pure_checkpoint", forbidden("o download do PURE"))
    monkeypatch.setattr(pure_model.RelationExtractorPURE, "load", classmethod(forbidden("RelationExtractorPURE.load")))
    monkeypatch.setattr(he, "classify_pairs", forbidden("classify_pairs (LLM)"))
    text = "Aspirin was given to the patient."
    fake_ollama.script[:] = [EMPTY_TAX_ANSWER]   # só a taxonomia chega ao LLM
    logs = []
    tax, triples = he.HybridEngine.extrair(text, "qwen3:8b", 0.1, logs.append, ner=stub_ner([ent(text, "Aspirin", "DRUG")]),
                                           client=OllamaClient("qwen3:8b", fake_ollama.host))
    assert triples == []
    assert "> [PAIRS] 0 candidate pairs." in logs and "> [RELATIONS] 0 triples kept." in logs
    assert len(fake_ollama.calls) == 1 and set(tax["instances"]) == {"Aspirin"}   # a geração seguiu para a taxonomia


# ---- REL-10: uma tripla por fato
TWO_SENTENCES = "Aspirin prevents stroke. Later, aspirin prevents Stroke again."


def _two_sentence_ner(stub_ner):
    t = TWO_SENTENCES
    return stub_ner([ent(t, "Aspirin", "DRUG"), ent(t, "stroke", "DISEASE"), ent(t, "aspirin", "DRUG"),
                     ent(t, "Stroke", "DISEASE")])


def test_the_same_fact_in_two_sentences_gives_one_triple_with_the_highest_confidence(stub_ner, monkeypatch,
                                                                                    tmp_path):
    monkeypatch.setenv("OMAKER_ENTITIES", "ner")
    _fake_pure(monkeypatch, tmp_path, lambda pairs: [("prevents", 0.8 if p["text"].startswith("Aspirin") else 0.9)
                                                     for p in pairs])
    _tax, triples = he.HybridEngine.extrair(TWO_SENTENCES, "qwen3:8b", 0.1, lambda _m: None,
                                            ner=_two_sentence_ner(stub_ner), with_taxonomy=False)
    assert len(triples) == 1
    (sub, _st, rel, obj, _ot, conf), = triples
    assert (sub.lower(), rel, obj.lower(), conf) == ("aspirin", "prevents", "stroke", pytest.approx(0.9))


def test_no_relation_predictions_are_never_kept_as_triples(stub_ner, monkeypatch, tmp_path):
    monkeypatch.setenv("OMAKER_ENTITIES", "ner")
    _fake_pure(monkeypatch, tmp_path, lambda pairs: [("no_relation", 0.99)] * len(pairs))
    _tax, triples = he.HybridEngine.extrair(TWO_SENTENCES, "qwen3:8b", 0.1, lambda _m: None,
                                            ner=_two_sentence_ner(stub_ner), with_taxonomy=False)
    assert triples == []
