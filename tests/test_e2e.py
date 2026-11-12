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


def test_heldout_doc_reported_separately(docs):
    r = evaluate_system("ner+llm", docs, extract=_fake_extract)
    assert [d.id for d in docs if d.heldout] == ["amostra-2"]
    h = r["heldout_strict"]
    assert (h["tp"], h["fp"], h["fn"]) == (1, 0, 4)


def test_both_pure_system_uses_all_entities(docs, monkeypatch, tmp_path):
    ckpt = tmp_path / "treinado.pt"
    ckpt.write_bytes(b"x")
    monkeypatch.setenv("OMAKER_CHECKPOINT", str(ckpt))
    seen = []
    evaluate_system("both+pure", docs, extract=lambda t, m: seen.append(os.environ["OMAKER_ENTITIES"]) or [])
    assert set(seen) == {"both"}


def test_contamination_with_pure_training_texts(docs, monkeypatch, tmp_path):
    import torch

    salbutamol = next(s for s in docs[1].text.split(". ") if "Salbutamol" in s)
    ckpt = tmp_path / "treinado.pt"
    torch.save({"state_dict": {}, "train_texts": [salbutamol.rstrip(".") + "."]}, ckpt)
    monkeypatch.setenv("OMAKER_CHECKPOINT", str(ckpt))
    r = evaluate_system("pure", docs, extract=lambda t, m: [])
    assert r["contamination"] and r["contamination"][0]["doc"] == "amostra-2"
    assert "Salbutamol" in r["contamination"][0]["sentence"]


def test_no_entities_counts_as_no_prediction(monkeypatch):
    from omaker.evaluation import e2e

    def boom(*a, **k):
        raise ValueError("No biomedical entities (drug / symptom / disease) were found in the text.")

    monkeypatch.setattr(he.HybridEngine, "extrair", staticmethod(boom))
    assert e2e.default_extract("texto sem entidades", "qwen3:8b") == []


def test_preconditions_checked_before_running_any_system(monkeypatch, tmp_path):
    from omaker.evaluation import e2e

    monkeypatch.setenv("OMAKER_CHECKPOINT", str(tmp_path / "nao-existe.pt"))
    ran = []
    monkeypatch.setattr(e2e, "evaluate_system", lambda name, *a, **k: ran.append(name) or {})
    with pytest.raises(FileNotFoundError):
        e2e.main(["--systems", "llm", "pure", "--runs-dir", str(tmp_path / "runs")])
    assert ran == []


def test_results_written_after_each_system_with_metadata(monkeypatch, tmp_path):
    from omaker.evaluation import e2e

    def fake_eval(name, docs, extract=None, model="m", temperature=0.0):
        if name == "ner+llm":
            raise RuntimeError("Ollama caiu")
        return {"system": name, "strict": {"precision": 0, "recall": 0, "f1": 0, "tp": 0, "fp": 0, "fn": 0},
                "lenient": {"f1": 0}, "traps_hit": []}

    monkeypatch.setattr(e2e, "evaluate_system", fake_eval)
    with pytest.raises(RuntimeError):
        e2e.main(["--systems", "llm", "ner+llm", "--runs-dir", str(tmp_path / "runs")])
    (run,) = (tmp_path / "runs").iterdir()
    saved = json.loads((run / "results.json").read_text(encoding="utf-8"))
    assert [r["system"] for r in saved["results"]] == ["llm"]
    meta = saved["metadata"]
    assert {"commit", "gold_sha256", "model", "temperature", "llm_seed", "checkpoint", "checkpoint_sha256"} <= set(meta)


def test_llm_seed_sent_to_ollama(fake_ollama, monkeypatch):
    monkeypatch.setenv("OMAKER_LLM_SEED", "7")
    fake_ollama.script[:] = [json.dumps({"ok": True})]
    OllamaClient("qwen3:8b", fake_ollama.host).chat_json("s", "u", {"type": "object"})
    assert fake_ollama.calls[-1]["options"]["seed"] == 7


def _fake_result(name):
    return {"system": name, "strict": {"precision": 0, "recall": 0, "f1": 0, "tp": 0, "fp": 0, "fn": 0},
            "lenient": {"f1": 0}, "traps_hit": []}


def test_resume_skips_systems_already_evaluated(monkeypatch, tmp_path):
    from omaker.evaluation import e2e

    ran, fail = [], {"ner+llm"}

    def fake_eval(name, docs, extract=None, model="m", temperature=0.0):
        ran.append(name)
        if name in fail:
            raise RuntimeError("Ollama caiu")
        return _fake_result(name)

    monkeypatch.setattr(e2e, "evaluate_system", fake_eval)
    args = ["--systems", "llm", "ner+llm", "--runs-dir", str(tmp_path / "runs")]
    with pytest.raises(RuntimeError):
        e2e.main(args)
    (run,) = (tmp_path / "runs").iterdir()
    fail.clear()
    ran.clear()
    assert e2e.main(args + ["--resume", str(run)]) == run
    assert ran == ["ner+llm"]   # o llm já estava gravado
    saved = json.loads((run / "results.json").read_text(encoding="utf-8"))
    assert [r["system"] for r in saved["results"]] == ["llm", "ner+llm"]


def test_resume_refuses_a_different_model(monkeypatch, tmp_path):
    from omaker.evaluation import e2e

    monkeypatch.setattr(e2e, "evaluate_system", lambda name, *a, **k: _fake_result(name))
    run = e2e.main(["--systems", "llm", "--runs-dir", str(tmp_path / "runs")])
    with pytest.raises(ValueError, match="model"):
        e2e.main(["--systems", "llm", "--model", "outro:1b", "--resume", str(run)])
