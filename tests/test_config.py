from pathlib import Path

import pytest

from omaker.config import Settings, load_settings
from omaker.llm.client import OllamaClient


def test_defaults():
    assert load_settings({}) == Settings("http://localhost:11434", "both", None)


def test_host_without_scheme_gets_http():
    assert load_settings({"OLLAMA_HOST": "127.0.0.1:11434"}).ollama_host == "http://127.0.0.1:11434"


def test_entity_source_is_normalized():
    assert load_settings({"OMAKER_ENTITIES": " NER "}).entity_source == "ner"


def test_invalid_entity_source_raises():
    with pytest.raises(ValueError, match="OMAKER_ENTITIES.*ner, llm ou both"):
        load_settings({"OMAKER_ENTITIES": "bothh"})


def test_checkpoint_from_env(tmp_path):
    assert load_settings({"OMAKER_CHECKPOINT": str(tmp_path / "x.pt")}).checkpoint == Path(tmp_path / "x.pt")


def test_env_change_after_import_is_seen(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://outra-maquina:11434")
    assert OllamaClient("qwen3:8b").host == "http://outra-maquina:11434"


def test_bad_entity_source_does_not_break_checkpoint_or_client(monkeypatch):
    from omaker import paths

    monkeypatch.setenv("OMAKER_ENTITIES", "nerr")
    monkeypatch.delenv("OMAKER_CHECKPOINT", raising=False)
    assert paths.default_checkpoint_path() == paths.project_root() / "omaker_pure.pt"
    assert OllamaClient("qwen3:8b", None).host.startswith("http")


def test_bad_entity_source_reported_when_generating(monkeypatch, stub_ner):
    from omaker.pipeline.engine import HybridEngine

    class NoLLM:
        model = "fake"

        def chat_json(self, *a, **k):
            raise AssertionError("LLM must not be called")

    monkeypatch.setenv("OMAKER_ENTITIES", "nerr")
    with pytest.raises(ValueError, match="OMAKER_ENTITIES"):
        HybridEngine.extrair("Aspirin prevents stroke.", "fake", 0.1, lambda _: None, ner=stub_ner([]), client=NoLLM())
