import json
import os

import pytest

from omaker.evaluation.e2e import GOLD_SAMPLES, evaluate_system, lenient_match, load_gold, strict_key
from omaker.llm.client import OllamaClient
from omaker.pipeline import engine as he


@pytest.fixture
def docs():
    return load_gold(GOLD_SAMPLES)


def test_gold_samples_load(docs):
    assert [d.id for d in docs] == ["amostra-1", "amostra-2"]
    assert len(docs[0].triples) == 7 and len(docs[1].triples) == 5


def test_strict_vs_lenient():
    pred, gold = ("Metformin", "treats", "diabetes"), ("metformin", "treats", "type 2 diabetes")
    assert lenient_match(pred, gold)
    assert strict_key(*pred) != strict_key(*gold)
    assert strict_key("Liver_Cirrhosis ", "causes", "x") == strict_key("liver cirrhosis", "causes", "X")


def _fake_extract(text, model):
    if "metformin" in text.lower():
        return [("aspirin", "prevents", "myocardial infarction"),       # exata
                ("Alcohol", "causes", "liver cirrhosis"),                # exata (maiúscula)
                ("metformin", "treats", "diabetes"),                     # só tolerante
                ("ibuprofen", "treats", "headache")]                     # armadilha
    return [("warfarin", "prevents", "stroke")]


def test_evaluate_with_fake_extractor(docs):
    r = evaluate_system("ner+llm", docs, extract=_fake_extract)
    s, le = r["strict"], r["lenient"]
    assert (s["tp"], s["fp"], s["fn"]) == (3, 2, 9)
    assert s["precision"] == pytest.approx(3 / 5) and s["recall"] == pytest.approx(3 / 12)
    assert le["precision"] == pytest.approx(4 / 5) and le["recall"] == pytest.approx(4 / 12)
    assert len(r["traps_hit"]) == 1 and r["traps_hit"][0]["pred"][0] == "ibuprofen"


def test_pure_requires_checkpoint(docs, monkeypatch, tmp_path):
    monkeypatch.setenv("OMAKER_CHECKPOINT", str(tmp_path / "nao-existe.pt"))
    with pytest.raises(FileNotFoundError, match="omaker.relations.train"):
        evaluate_system("pure", docs, extract=_fake_extract)


def test_system_environment_is_applied_and_restored(docs, monkeypatch, tmp_path):
    monkeypatch.setenv("OMAKER_ENTITIES", "both")
    ckpt = tmp_path / "treinado.pt"
    ckpt.write_bytes(b"x")
    monkeypatch.setenv("OMAKER_CHECKPOINT", str(ckpt))
    seen = []

    def spy(text, model):
        seen.append((os.environ["OMAKER_ENTITIES"], os.path.exists(os.environ["OMAKER_CHECKPOINT"])))
        return []

    evaluate_system("llm", docs, extract=spy)
    assert set(seen) == {("llm", False)}          # relações pelo LLM mesmo havendo checkpoint
    seen.clear()
    evaluate_system("pure", docs, extract=spy)
    assert set(seen) == {("ner", True)}
    assert os.environ["OMAKER_ENTITIES"] == "both" and os.environ["OMAKER_CHECKPOINT"] == str(ckpt)


def test_extrair_without_taxonomy_skips_llm_call(fake_ollama, stub_ner, monkeypatch, tmp_path):
    from omaker.domain.entities import Entity

    monkeypatch.setenv("OMAKER_ENTITIES", "ner")
    monkeypatch.setenv("OMAKER_CHECKPOINT", str(tmp_path / "nao-existe.pt"))
    text = "Aspirin prevents stroke."
    ner = stub_ner([Entity("Aspirin", 0, 7, "DRUG", 0.99), Entity("stroke", 17, 23, "DISEASE", 0.99)])
    fake_ollama.script[:] = [json.dumps({"results": [{"id": 0, "relation": "prevents"}]})]
    tax, triples = he.HybridEngine.extrair(text, "qwen3:8b", 0.1, lambda _: None, ner=ner,
                                           client=OllamaClient("qwen3:8b", fake_ollama.host), with_taxonomy=False)
    assert len(fake_ollama.calls) == 1
    assert [(t[0], t[2], t[3]) for t in triples] == [("Aspirin", "prevents", "stroke")]
    assert tax["instances"] == {"Aspirin": "Drug", "stroke": "Disease"}
