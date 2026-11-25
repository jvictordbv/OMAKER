"""Prompt de relações do LLM: o escrito à mão (padrão) ou o otimizado (OMAKER_LLM_PROMPT=optimized)."""
import json

import pytest

from omaker.llm import relations
from omaker.llm.client import OllamaClient

PAIR = {"text": "Aspirin prevents stroke.", "sub_name": "Aspirin", "sub_type": "DRUG",
        "obj_name": "stroke", "obj_type": "DISEASE"}
OPTIMIZED = {
    "format": 1,
    "instruction": "Decide carefully whether the sentence asserts the relation (optimized instruction).",
    "examples": [
        {"sentence": "Metformin lowers glucose in type 2 diabetes.", "subject": "Metformin", "subject_type": "DRUG",
         "object": "type 2 diabetes", "object_type": "DISEASE", "relation": "treats"},
        {"sentence": "Patients on lithium and with gout were enrolled.", "subject": "lithium", "subject_type": "DRUG",
         "object": "gout", "object_type": "DISEASE", "relation": "no_relation"},
    ],
}


@pytest.fixture
def optimized_file(tmp_path, monkeypatch):
    path = tmp_path / "relations_optimized.json"
    path.write_text(json.dumps(OPTIMIZED), encoding="utf-8")
    monkeypatch.setattr(relations, "OPTIMIZED_PROMPT", path)
    return path


def _classify(fake_ollama, logs=None):
    fake_ollama.script[:] = ['{"results": [{"id": 0, "relation": "prevents"}]}']
    out = relations.classify_pairs(OllamaClient("qwen3:8b", fake_ollama.host), [PAIR], 0.0,
                                   (logs if logs is not None else []).append)
    return out, fake_ollama.calls[-1]["messages"][0]["content"]


def test_default_prompt_is_the_handwritten_one(fake_ollama, optimized_file, monkeypatch):
    monkeypatch.delenv("OMAKER_LLM_PROMPT", raising=False)
    out, system = _classify(fake_ollama)
    assert out == [("prevents", None)]
    assert system == relations.RELATION_SYSTEM


def test_handwritten_prompt_is_instruction_plus_json_request():
    assert relations.RELATION_SYSTEM == relations.RELATION_INSTRUCTION + " Return JSON only."


def test_optimized_prompt_sends_instruction_and_examples(fake_ollama, optimized_file, monkeypatch):
    monkeypatch.setenv("OMAKER_LLM_PROMPT", "optimized")
    logs = []
    out, system = _classify(fake_ollama, logs)
    assert out == [("prevents", None)]
    assert OPTIMIZED["instruction"] in system
    for ex in OPTIMIZED["examples"]:
        assert (f'sentence: "{ex["sentence"]}" | subject: "{ex["subject"]}" ({ex["subject_type"]}) '
                f'| object: "{ex["object"]}" ({ex["object_type"]}) -> {ex["relation"]}') in system
    assert "Return JSON only." in system
    assert any("optimized" in m for m in logs)


def test_optimized_requested_without_file_falls_back_to_default(fake_ollama, tmp_path, monkeypatch):
    monkeypatch.setattr(relations, "OPTIMIZED_PROMPT", tmp_path / "missing.json")
    monkeypatch.setenv("OMAKER_LLM_PROMPT", "optimized")
    logs = []
    _out, system = _classify(fake_ollama, logs)
    assert system == relations.RELATION_SYSTEM
    assert any("missing.json" in m for m in logs)


def test_env_is_read_at_call_time(fake_ollama, optimized_file, monkeypatch):
    monkeypatch.setenv("OMAKER_LLM_PROMPT", "optimized")
    assert OPTIMIZED["instruction"] in _classify(fake_ollama)[1]
    monkeypatch.setenv("OMAKER_LLM_PROMPT", "default")
    assert _classify(fake_ollama)[1] == relations.RELATION_SYSTEM
