"""RNF-01: o texto do usuário só vai ao Ollama local; as outras conexões de rede são só downloads."""
import ast
import json
from pathlib import Path

from omaker.llm.client import OllamaClient

ROOT = Path(__file__).resolve().parents[1]
LOCAL_OLLAMA = "http://localhost:11434"
NETWORK_MODULES = {"requests", "urllib.request", "urllib3", "http.client", "httpx", "aiohttp", "socket"}
ALLOWED = {"omaker/llm/client.py", "omaker/relations/download.py", "omaker/relations/biored.py"}


def test_ollama_host_defaults_to_localhost(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    assert OllamaClient().host == LOCAL_OLLAMA


def test_only_the_ollama_client_and_the_downloaders_import_network_libraries():
    found = set()
    for path in (ROOT / "omaker").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            if any(n in NETWORK_MODULES or n.split(".")[0] in {"requests", "urllib3", "httpx", "aiohttp"}
                   for n in names):
                found.add(path.relative_to(ROOT).as_posix())
    assert found <= ALLOWED, sorted(found - ALLOWED)


class _Resp:
    status_code = 200

    def __init__(self, body):
        self._body, self.text = body, json.dumps(body)

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def test_generating_an_ontology_sends_the_text_only_to_the_local_ollama(monkeypatch, tmp_path):
    import requests

    from omaker.ontology import builder as owl_builder
    from omaker.pipeline import engine as he

    text = "Aspirin prevents stroke in older patients."
    urls, bodies = [], []

    def fake_get(url, **kwargs):
        urls.append(url)
        return _Resp({"models": [{"name": "qwen3:8b"}]})

    def fake_post(url, **kwargs):
        payload = kwargs["json"]
        urls.append(url)
        bodies.append(payload)
        props = payload["format"]["properties"]
        if "entities" in props:
            answer = {"entities": [{"text": "Aspirin", "type": "DRUG"}, {"text": "stroke", "type": "DISEASE"}]}
        elif "results" in props:
            answer = {"results": [{"id": 0, "relation": "prevents"}]}
        else:
            answer = {"classes": [], "instances": [], "disjoint": []}
        return _Resp({"message": {"content": json.dumps(answer)}, "done_reason": "stop"})

    def no_other_connection(*a, **k):
        raise AssertionError("conexão de rede fora do cliente do Ollama")

    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.setenv("OMAKER_ENTITIES", "llm")
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "request", no_other_connection)
    monkeypatch.setattr(requests, "Session", no_other_connection)
    monkeypatch.setattr(he, "default_checkpoint_path", lambda: tmp_path / "sem-checkpoint.pt")   # relações pelo LLM
    monkeypatch.setattr(owl_builder, "run_reasoner", lambda *a, **k: owl_builder.ReasonerStatus.UNAVAILABLE)

    result = he.HybridEngine.gerar_ontologia(text, "local", "qwen3:8b", 0.1, str(tmp_path), "", lambda _m: None)
    assert Path(result.path).is_file() and result.relations_added == 1
    assert urls and all(u.startswith(LOCAL_OLLAMA + "/") for u in urls), urls
    assert any(text in m["content"] for b in bodies for m in b["messages"])   # o texto foi, e só para lá
