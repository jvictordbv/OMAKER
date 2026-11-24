import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import pytest

from omaker.domain.entities import Entity


@pytest.fixture(autouse=True)
def no_model_download(monkeypatch):
    """Nenhum teste baixa o checkpoint do PURE da internet (os de download usam sessões falsas)."""
    monkeypatch.setenv("OMAKER_NO_DOWNLOAD", "1")


@pytest.fixture(autouse=True)
def isolated_qsettings(tmp_path, monkeypatch):
    """Nenhum teste lê ou grava as configurações reais do usuário (registro MeuMestrado/OntoGenApp)."""
    from PySide6.QtCore import QSettings

    from omaker.ui.pages import settings

    monkeypatch.setattr(settings, "default_settings",
                        lambda: QSettings(str(tmp_path / "qsettings_teste.ini"), QSettings.IniFormat))


class _FakeOllama:
    def __init__(self):
        self.script: list = []   # contents returned by /api/chat, in order (str, or dict with done_reason)
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
            item = state.script.pop(0)
            item = item if isinstance(item, dict) else {"content": item, "done_reason": "stop"}
            self._send(200, {"message": {"content": item["content"]}, "done_reason": item["done_reason"]})

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


TINY_MODEL_TEXT = "aspirin prevents stroke ."   # SAMPLE_TEXT de test_relation_extractor


@pytest.fixture
def tiny_fp16_model(tmp_path):
    """Tiny BERT saved in float16 (like the SpanBERT checkpoint) plus its tokenizer; offline."""
    from transformers import BertConfig, BertModel, BertTokenizerFast

    path = tmp_path / "tiny_bert"
    path.mkdir()
    vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"] + TINY_MODEL_TEXT.split()
    (path / "vocab.txt").write_text("\n".join(vocab) + "\n", encoding="utf-8")
    BertTokenizerFast(vocab_file=str(path / "vocab.txt")).save_pretrained(path)
    config = BertConfig(
        vocab_size=64, hidden_size=32, num_hidden_layers=1, num_attention_heads=2, intermediate_size=64
    )
    BertModel(config).half().save_pretrained(path)
    return str(path)
