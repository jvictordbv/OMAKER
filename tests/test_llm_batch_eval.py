"""Medida do prompt de relações em lotes, pelo caminho do pipeline (omaker.evaluation.llm_batch, AVA-24)."""
import json

import pytest

from omaker.evaluation import llm_batch
from omaker.llm.client import LLMError
from omaker.llm.relations import PAIR_BATCH, RELATION_SYSTEM

OPTIMIZED = {"format": 1, "instruction": "OPTIMIZED INSTRUCTION", "examples": [
    {"sentence": "Aspirin relieves headache.", "subject": "Aspirin", "subject_type": "DRUG",
     "object": "headache", "object_type": "SYMPTOM", "relation": "treats"}]}


def _row(i, relation):
    return {"text": f"Drug{i} and disease{i} appear in sentence {i}.", "sub_name": f"Drug{i}", "sub_type": "DRUG",
            "obj_name": f"disease{i}", "obj_type": "DISEASE", "relation": relation}


@pytest.fixture
def splits(tmp_path):
    d = tmp_path / "splits"
    d.mkdir()
    rows = {"train": [_row(0, "causes")],
            "dev": [_row(i, "causes" if i % 2 else "no_relation") for i in range(20)],
            "test": [_row(i, "treats" if i % 3 == 0 else "no_relation") for i in range(100, 117)]}
    for part, r in rows.items():
        (d / f"{part}.json").write_text(json.dumps(r), encoding="utf-8")
    (d / "manifest.json").write_text("{}", encoding="utf-8")
    return d


@pytest.fixture
def prompt_file(tmp_path, monkeypatch):
    path = tmp_path / "relations_optimized.json"
    path.write_text(json.dumps(OPTIMIZED), encoding="utf-8")
    monkeypatch.setattr(llm_batch, "OPTIMIZED_PROMPT", path)
    return path


class FakeClient:
    """Responde cada lote: o prompt otimizado acerta o gabarito, o escrito à mão diz no_relation para tudo."""

    model = "fake"

    def __init__(self, gold, fail_on=(), stop_after=None):
        self.gold, self.fail_on, self.stop_after = gold, set(fail_on), stop_after
        self.calls = []

    def chat_json(self, system, user, schema, temperature=0.1, retries=2):
        if self.stop_after is not None and len(self.calls) >= self.stop_after:
            raise KeyboardInterrupt   # queda no meio (fora do LLMError, que vira lote com falha)
        self.calls.append({"system": system, "user": user, "temperature": temperature})
        if len(self.calls) in self.fail_on:
            raise LLMError("The model did not return valid JSON")
        lines = user.splitlines()
        results = []
        for line in lines:
            idx, rest = line.split(". ", 1)
            subject = rest.split('subject: "', 1)[1].split('"', 1)[0]
            rel = self.gold[subject] if "OPTIMIZED INSTRUCTION" in system else "no_relation"
            results.append({"id": int(idx), "relation": rel})
        return {"results": results}


def _gold(splits):
    return {r["sub_name"]: r["relation"] for p in ("dev", "test")
            for r in json.loads((splits / f"{p}.json").read_text(encoding="utf-8"))}


def _argv(splits, tmp_path, *extra):
    return ["--splits", str(splits), "--runs-dir", str(tmp_path / "runs"), *extra]


def test_batches_have_at_most_15_consecutive_pairs_in_pipeline_format(splits):
    from omaker.relations.data import load_examples

    out = llm_batch.batches(load_examples(splits / "dev.json"))
    assert [len(b) for b in out] == [PAIR_BATCH, 5]
    assert out[0][0] == {"text": "Drug0 and disease0 appear in sentence 0.", "sub_name": "Drug0", "sub_type": "DRUG",
                         "obj_name": "disease0", "obj_type": "DISEASE"}
    assert out[1][0]["sub_name"] == "Drug15"


def test_systems_are_the_handwritten_and_the_optimized_pipeline_prompts(prompt_file):
    s = llm_batch.systems()
    assert s["default"] == RELATION_SYSTEM
    assert s["optimized"].startswith("OPTIMIZED INSTRUCTION")
    assert 'subject: "Aspirin" (DRUG)' in s["optimized"] and s["optimized"].endswith("Return JSON only.")


def test_systems_require_the_installed_optimized_prompt(tmp_path):
    with pytest.raises(FileNotFoundError, match="--install"):
        llm_batch.systems(tmp_path / "missing.json")


def test_full_run_scores_both_prompts_on_dev_and_test_in_batches(splits, prompt_file, tmp_path, monkeypatch):
    monkeypatch.delenv("OMAKER_LLM_SEED", raising=False)
    client = FakeClient(_gold(splits))
    run = llm_batch.main(_argv(splits, tmp_path), client=client)
    assert len(client.calls) == 2 * 2 + 2 * 2   # dev: 2 lotes, teste: 2 lotes, para cada prompt
    assert {c["temperature"] for c in client.calls} == {0.0}
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["optimized"]["dev"]["micro"]["f1"] == 1.0
    assert metrics["optimized"]["test"]["micro"]["f1"] == 1.0
    assert metrics["default"]["dev"]["micro"]["f1"] == 0.0
    assert metrics["metadata"]["n_dev"] == 20 and metrics["metadata"]["n_test"] == 17
    report = (run / "report.md").read_text(encoding="utf-8")
    assert "| Otimizado | 1.000 |" in report and "lotes de 15 pares" in report
    assert "OMAKER_LLM_SEED" not in __import__("os").environ   # restaurada no fim


def test_failed_batch_counts_as_no_relation_and_is_reported(splits, prompt_file, tmp_path):
    client = FakeClient(_gold(splits), fail_on={3})   # 3.º pedido: primeiro lote do otimizado em dev
    run = llm_batch.main(_argv(splits, tmp_path), client=client)
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["optimized"]["dev"]["failed_batches"] == 1
    assert metrics["optimized"]["dev"]["micro"]["tp"] == 3   # só o 2.º lote conta: Drug15, 17 e 19 são causes
    state = json.loads((run / "state.json").read_text(encoding="utf-8"))
    assert "valid JSON" in state["results"]["optimized/dev"][0]["error"]


def test_resume_continues_from_the_next_batch(splits, prompt_file, tmp_path):
    with pytest.raises(KeyboardInterrupt):
        llm_batch.main(_argv(splits, tmp_path), client=FakeClient(_gold(splits), stop_after=3))
    run = next((tmp_path / "runs").iterdir())
    client = FakeClient(_gold(splits))
    llm_batch.main(["--resume", str(run)], client=client)
    assert len(client.calls) == 8 - 3
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["optimized"]["test"]["micro"]["f1"] == 1.0


def test_resume_refuses_changed_settings_or_prompt(splits, prompt_file, tmp_path):
    run = llm_batch.main(_argv(splits, tmp_path, "--limit", "5"), client=FakeClient(_gold(splits)))
    with pytest.raises(ValueError, match="'limit' mudou"):
        llm_batch.main(["--resume", str(run), "--limit", "6"], client=FakeClient(_gold(splits)))
    prompt_file.write_text(json.dumps({**OPTIMIZED, "instruction": "OTHER"}), encoding="utf-8")
    with pytest.raises(ValueError, match="prompts mudou"):
        llm_batch.main(["--resume", str(run)], client=FakeClient(_gold(splits)))
