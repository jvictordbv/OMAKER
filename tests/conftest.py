import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import pytest

from core.ner import Entity


class _FakeOllama:
    def __init__(self):
        self.script: list[str] = []   # contents returned by /api/chat, in order
        self.calls: list[dict] = []   # request bodies received by /api/chat
        self.models: list[str] = ["qwen3:8b"]   # served by /api/tags
        self.host = ""


@pytest.fixture
def fake_ollama():
    state = _FakeOllama()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, obj):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            self._send(200, {"models": [{"name": m} for m in state.models]})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.calls.append(body)
            self._send(200, {"message": {"content": state.script.pop(0)}})

    srv = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    state.host = f"http://127.0.0.1:{srv.server_port}"
    try:
        yield state
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


@pytest.fixture
def stub_ner():
    """Factory: stub_ner(entities) -> object with extract(text) and last_rejected, no torch needed."""
    def make(entities: list[Entity]):
        return SimpleNamespace(extract=lambda _text: list(entities), last_rejected=[])
    return make


@pytest.fixture
def sample_extraction():
    """(taxonomy, triples) of scenario 1 of test_hybrid_engine: the validated output of
    HybridEngine.extrair, kept as literal data so tests of the OWL stage need no LLM or NER."""
    tax = {
        "classes": {"Analgesic": "Drug", "Cancer": "Disease", "Weird": "BiomedicalEntity",
                    "LoopA": "BiomedicalEntity", "LoopB": "LoopA"},
        "instances": {"Aspirin": "Analgesic", "stroke": "Disease", "Chemotherapy": "Drug",
                      "tumor": "Cancer", "nausea": "Symptom", "fever": "Symptom"},
        "disjoint": [["Analgesic", "Cancer"]],
    }
    triples = [
        ("Aspirin", "DRUG", "prevents", "stroke", "DISEASE", None),
        ("Chemotherapy", "DRUG", "treats", "tumor", "DISEASE", None),
        ("Chemotherapy", "DRUG", "causes", "nausea", "SYMPTOM", None),
    ]
    return tax, triples
