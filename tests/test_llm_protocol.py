import json

from omaker.domain.entities import Entity
from omaker.llm.client import LLMClient, OllamaClient
from omaker.pipeline.engine import HybridEngine

TEXT = "Aspirin prevents stroke."


class FakeLLM:
    """Cliente sem HTTP: prova que o motor depende só do protocolo."""

    model = "fake"

    def __init__(self, answers):
        self.answers = list(answers)

    def chat_json(self, system, user, schema, temperature=0.1, retries=2):
        return json.loads(self.answers.pop(0))


def test_clients_follow_protocol():
    assert isinstance(OllamaClient("qwen3:8b", "http://h:1"), LLMClient)
    assert isinstance(FakeLLM([]), LLMClient)


def test_engine_runs_with_any_llm_client(stub_ner, monkeypatch, tmp_path):
    monkeypatch.setenv("OMAKER_ENTITIES", "ner")
    monkeypatch.setenv("OMAKER_CHECKPOINT", str(tmp_path / "nao-existe.pt"))
    ner = stub_ner([Entity("Aspirin", 0, 7, "DRUG", 0.99), Entity("stroke", 17, 23, "DISEASE", 0.99)])
    llm = FakeLLM([
        json.dumps({"results": [{"id": 0, "relation": "prevents"}]}),
        json.dumps({"classes": [], "instances": [], "disjoint": []}),
    ])
    tax, triples = HybridEngine.extrair(TEXT, "fake", 0.1, lambda _: None, ner=ner, client=llm)
    assert [(t[0], t[2], t[3]) for t in triples] == [("Aspirin", "prevents", "stroke")]
    assert llm.answers == []
