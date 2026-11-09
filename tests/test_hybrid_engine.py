import json

import pytest

from core import hybrid_engine as he
from core.llm_client import OllamaClient
from core.llm_ner import extract_entities_llm, merge_entities
from core.ner import Entity

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
    monkeypatch.setattr(he.HybridEngine, "ENTITY_SOURCE", "ner")   # entities from the NER model only
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
    assert any("SKIP" in l and "tumor" in l for l in logs)   # DISEASE "treats" rejected by the domain filter


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
    monkeypatch.setattr(he.HybridEngine, "ENTITY_SOURCE", "both")
    fake_ollama.script[:] = [LLM_ENTITIES, json.dumps({"results": []}),
                             json.dumps({"classes": [], "instances": [], "disjoint": []})]
    logs2 = []
    tax2, _triples2 = he.HybridEngine.extrair(TEXT, "qwen3:8b", 0.1, logs2.append, ner=weak_ner,
                                              client=OllamaClient("qwen3:8b", fake_ollama.host))
    assert any("6 unique entities" in l for l in logs2), logs2
    assert any("ignored: 'tumor'" in l for l in logs2)
    assert set(tax2["instances"]) == {"Aspirin", "stroke", "Chemotherapy", "tumor", "nausea", "fever"}
