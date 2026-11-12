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
