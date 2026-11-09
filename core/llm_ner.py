"""LLM-assisted entity extraction with verification, plus merging with the NER model's output.

The LLM only proposes surface strings. Every proposal is located in the text with a
whole-word search; strings that do not occur are discarded, so it cannot hallucinate entities.
"""
from __future__ import annotations

import re
from typing import List

from core.ner import Entity
from core.text_utils import split_sentences

LLM_ENTITY_SCORE = 0.75  # constant: the LLM gives no calibrated score
ENTITY_TYPES_LLM = ["DRUG", "SYMPTOM", "DISEASE"]

ENTITY_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "type": {"type": "string", "enum": ENTITY_TYPES_LLM}},
                "required": ["text", "type"],
            },
        }
    },
    "required": ["entities"],
}

ENTITY_SYSTEM = """You extract biomedical entities from text. Types:
- DRUG: medications, vaccines, therapies (e.g. chemotherapy), and harmful agents such as alcohol or tobacco.
- SYMPTOM: signs and symptoms (e.g. fever, nausea, headache, dizziness).
- DISEASE: diseases, disorders, infections, tumors, conditions (e.g. stroke, pneumonia, tumor).
Rules:
- Copy each entity EXACTLY as written in the text (same spelling, no translation, no normalisation).
- List ONLY things that are clearly a drug/therapy, a symptom/sign, or a disease/condition. Do NOT list habits or
  exposures (e.g. diet, exercise), lab values or analytes (e.g. blood glucose), anatomical structures, procedures,
  people, doses or dates. If unsure whether something fits, leave it out.
- Use the shortest span that names the entity. Drop generic modifiers (chronic, acute, long-term, severe, excessive)
  and nouns such as use, intake or consumption attached to a substance name; keep words that belong to the
  name itself (e.g. "type 1 diabetes", "breast cancer").
- Never add entities that are not in the text; list each distinct entity once. Return only JSON."""


def _chunks(text: str, max_chars: int):
    """Groups whole sentences into chunks of at most max_chars."""
    chunk, size = [], 0
    for s, e in split_sentences(text):
        sentence = text[s:e]
        if chunk and size + len(sentence) > max_chars:
            yield " ".join(chunk)
            chunk, size = [], 0
        chunk.append(sentence)
        size += len(sentence) + 1
    if chunk:
        yield " ".join(chunk)


def extract_entities_llm(client, text: str, temperature: float = 0.0, max_chars: int = 3000) -> List[Entity]:
    proposals = {}
    for chunk in _chunks(text, max_chars):
        data = client.chat_json(ENTITY_SYSTEM, f"Text:\n{chunk}", ENTITY_SCHEMA, temperature=temperature)
        for item in data.get("entities", []):
            name, etype = str(item.get("text", "")).strip(), str(item.get("type", "")).upper()
            if name and etype in ENTITY_TYPES_LLM:
                proposals.setdefault(name.lower(), (name, etype))

    entities: List[Entity] = []
    for name, etype in proposals.values():
        pattern = re.compile(r"(?<!\w)" + re.escape(name) + r"(?!\w)", re.IGNORECASE)
        for m in pattern.finditer(text):  # every mention, so each one can form pairs
            entities.append(Entity(text[m.start():m.end()], m.start(), m.end(), etype, LLM_ENTITY_SCORE))
    return entities


def merge_entities(*groups) -> List[Entity]:
    """Union of several entity lists. On overlap the longer span wins, then the higher score."""
    pool = sorted((e for g in groups for e in g), key=lambda e: (-(e.end - e.start), -e.score))
    kept: List[Entity] = []
    for e in pool:
        if all(e.end <= k.start or e.start >= k.end for k in kept):
            kept.append(e)
    return sorted(kept, key=lambda e: e.start)