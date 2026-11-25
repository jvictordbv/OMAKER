"""Entidades propostas pelo LLM: esquema, tipos aceitos e envio do texto em blocos de frases."""
from omaker.domain.text import split_sentences
from omaker.llm.entities import ENTITY_SCHEMA, extract_entities_llm

PREFIX = "Text:\n"


class RecordingClient:
    """Cliente LLM falso: guarda cada pedido e responde com answer(bloco) -> lista de propostas."""

    model = "falso"

    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def chat_json(self, system, user, schema, temperature=0.1, retries=2):
        self.calls.append({"user": user, "schema": schema, "temperature": temperature})
        assert user.startswith(PREFIX)
        return {"entities": self.answer(user[len(PREFIX):])}


# ---- ENT-08: tipos aceitos do LLM
def test_llm_is_asked_for_the_entity_schema_with_the_three_types():
    client = RecordingClient(lambda _chunk: [])
    extract_entities_llm(client, "Aspirin prevents stroke.")
    (call,) = client.calls
    assert call["schema"] is ENTITY_SCHEMA
    item = ENTITY_SCHEMA["properties"]["entities"]["items"]
    assert item["properties"]["type"]["enum"] == ["DRUG", "SYMPTOM", "DISEASE"]
    assert set(item["required"]) == {"text", "type"}


def test_llm_proposals_with_an_unknown_type_or_an_empty_name_are_discarded():
    text = "BRCA1 was mutated. Aspirin prevents stroke."
    client = RecordingClient(lambda _chunk: [
        {"text": "BRCA1", "type": "GENE"}, {"text": "", "type": "DRUG"}, {"text": "   ", "type": "DISEASE"},
        {"text": "stroke", "type": "EVENT"}, {"text": "Aspirin", "type": "DRUG"},
    ])
    entities = extract_entities_llm(client, text)
    assert [(e.text, e.type) for e in entities] == [("Aspirin", "DRUG")]


# ---- ENT-09: texto em blocos de frases
def _long_text(n_chars):
    sentences, i = [], 0
    while sum(len(s) + 1 for s in sentences) < n_chars:
        sentences.append(f"Patient {i} received aspirin and reported a mild headache after the dose.")
        i += 1
    return " ".join(sentences)


def test_long_text_is_sent_in_blocks_of_whole_sentences_of_at_most_3000_chars():
    text = _long_text(7000)
    assert len(text) >= 7000
    client = RecordingClient(lambda _chunk: [])
    extract_entities_llm(client, text)
    chunks = [c["user"][len(PREFIX):] for c in client.calls]
    assert len(chunks) >= 3
    assert all(len(c) <= 3000 for c in chunks)
    sentences = [text[s:e] for s, e in split_sentences(text)]
    # cada bloco é uma sequência de frases inteiras, e juntos eles cobrem todas as frases, na ordem
    assert [s for c in chunks for s in (c[a:b] for a, b in split_sentences(c))] == sentences


def test_a_single_sentence_longer_than_the_limit_is_sent_alone():
    big = "Aspirin " + "and more aspirin " * 200 + "was given."
    assert len(big) > 3000
    text = f"Fever started. {big} Nausea followed."
    client = RecordingClient(lambda _chunk: [])
    extract_entities_llm(client, text)
    chunks = [c["user"][len(PREFIX):] for c in client.calls]
    assert chunks == ["Fever started.", big, "Nausea followed."]


def test_the_first_proposal_of_a_name_wins_regardless_of_case():
    text = _long_text(7000)
    answers = iter([[{"text": "aspirin", "type": "DRUG"}], [{"text": "ASPIRIN", "type": "SYMPTOM"}]])
    client = RecordingClient(lambda _chunk: next(answers, [{"text": "Aspirin", "type": "DISEASE"}]))
    entities = extract_entities_llm(client, text)
    assert len(client.calls) >= 3
    assert entities and {e.type for e in entities} == {"DRUG"}
    assert len(entities) == text.lower().count("aspirin")   # uma proposta só, achada em todas as ocorrências
