import pytest

from omaker.llm.client import LLMError, OllamaClient


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


def test_check_lists_installed_models(fake_ollama):
    fake_ollama.models[:] = ["org-bench/qwen3:8b-q4_K_M"]
    with pytest.raises(LLMError) as e:
        OllamaClient("qwen3:8b", fake_ollama.host).check()
    assert "org-bench/qwen3:8b-q4_K_M" in str(e.value)
    assert OllamaClient("qwen3:8b", fake_ollama.host).installed_models() == ["org-bench/qwen3:8b-q4_K_M"]


@pytest.mark.parametrize("wanted, installed, ok", [
    ("qwen3:8b-q4_K_M", ["qwen3:8b-q4_K_M"], True),
    ("qwen3", ["qwen3:latest"], True),                 # sem tag, o Ollama usa :latest
    ("qwen3:8b", ["qwen3:8b-q4_K_M"], False),          # outra tag: o Ollama responde 404
    ("qwen3", ["qwen3:4b"], False),                     # sem tag não vira "qualquer tag"
])
def test_check_requires_the_exact_name_ollama_will_use(fake_ollama, wanted, installed, ok):
    fake_ollama.models[:] = installed
    client = OllamaClient(wanted, fake_ollama.host)
    if ok:
        client.check()
    else:
        with pytest.raises(LLMError, match=installed[0]):
            client.check()


def test_output_limit_stops_a_looping_model_without_retrying(fake_ollama):
    """O modelo em laço (repete a mesma lista) para no limite de tokens, e não em 10 min de espera."""
    c = OllamaClient("qwen3:8b", fake_ollama.host)
    fake_ollama.script[:] = [{"content": '{"entities": [{"text": "biopsy"}, {"text": "biopsy"}, ', "done_reason": "length"}]
    with pytest.raises(LLMError, match="limit"):
        c.chat_json("s", "u", {})
    assert len(fake_ollama.calls) == 1   # repetir a mesma pergunta daria o mesmo laço
    assert fake_ollama.calls[0]["options"]["num_predict"] == c.max_tokens > 0
