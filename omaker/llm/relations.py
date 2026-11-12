"""Relation classification by the LLM, used when there is no trained PURE checkpoint."""
from __future__ import annotations

from omaker.domain.labels import NO_RELATION, REL2ID
from omaker.llm.client import LLMClient

RELATIONS = [r for r in REL2ID if r != NO_RELATION]

# Pairs sent to the LLM per request.
PAIR_BATCH = 15

RELATION_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "relation": {"type": "string", "enum": RELATIONS + [NO_RELATION]}},
                "required": ["id", "relation"],
            },
        }
    },
    "required": ["results"],
}

RELATION_SYSTEM = """You classify the relation between a subject and an object entity inside one sentence.
Labels: treats (subject treats/relieves object), causes (subject causes/induces object),
prevents (subject prevents/reduces risk of object), no_relation.
Answer no_relation unless the sentence explicitly states the relation between THESE two entities
(co-occurrence in the same sentence or record is not a relation). Return JSON only."""


def classify_pairs(client: LLMClient, pairs: list[dict], temperature: float, log) -> list[tuple[str, None]]:
    """Classifies candidate pairs with the LLM when there is no trained PURE checkpoint (no confidence)."""
    log("> [LLM] No trained PURE checkpoint found: classifying pairs with the LLM (no confidence scores).")
    out = [(NO_RELATION, None)] * len(pairs)
    for start in range(0, len(pairs), PAIR_BATCH):
        chunk = pairs[start:start + PAIR_BATCH]
        lines = [f'{start + i}. sentence: "{p["text"].strip()}" | subject: "{p["sub_name"]}" ({p["sub_type"]}) '
                 f'| object: "{p["obj_name"]}" ({p["obj_type"]})' for i, p in enumerate(chunk)]
        data = client.chat_json(RELATION_SYSTEM, "\n".join(lines), RELATION_SCHEMA, temperature=temperature)
        for r in data.get("results", []):
            idx = r.get("id")
            if isinstance(idx, int) and 0 <= idx < len(pairs) and r.get("relation") in RELATIONS:
                out[idx] = (r["relation"], None)
    return out
