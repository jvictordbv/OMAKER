import pytest

from core.llm_client import LLMError, OllamaClient


def test_parses_think_block_and_fenced_json(fake_ollama):
    c = OllamaClient("qwen3:8b", fake_ollama.host)
    c.check()
    fake_ollama.script[:] = ['<think>hmm</think>```json\n{"a": 1}\n```']
    assert c.chat_json("s", "u", {"type": "object"}) == {"a": 1}
    call = fake_ollama.calls[-1]
    assert call["think"] is False and call["options"]["num_ctx"] == 8192 and "format" in call


def test_retries_with_parse_error_feedback(fake_ollama):
    c = OllamaClient("qwen3:8b", fake_ollama.host)
    fake_ollama.script[:] = ["not json at all", '{"ok": true}']
    assert c.chat_json("s", "u", {"type": "object"}) == {"ok": True}
    assert "not valid JSON" in fake_ollama.calls[-1]["messages"][-1]["content"]


def test_raises_after_retries(fake_ollama):
    c = OllamaClient("qwen3:8b", fake_ollama.host)
    fake_ollama.script[:] = ["x", "y", "z"]
    with pytest.raises(LLMError):
        c.chat_json("s", "u", {})


def test_check_missing_model_suggests_pull(fake_ollama):
    with pytest.raises(LLMError) as exc:
        OllamaClient("llama3", fake_ollama.host).check()
    assert "ollama pull" in str(exc.value)
