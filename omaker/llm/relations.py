"""Relation classification by the LLM, used when there is no trained PURE checkpoint."""
from __future__ import annotations

import json
from pathlib import Path

from omaker.config import llm_prompt
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

# The task, without the output format: omaker.llm.optimize starts from this instruction (DSPy sets the format).
RELATION_INSTRUCTION = """You classify the relation between a subject and an object entity inside one sentence.
Labels: treats (subject treats/relieves object), causes (subject causes/induces object),
prevents (subject prevents/reduces risk of object), no_relation.
Answer no_relation unless the sentence explicitly states the relation between THESE two entities
(co-occurrence in the same sentence or record is not a relation)."""

RELATION_SYSTEM = RELATION_INSTRUCTION + " Return JSON only."

# Written by `python -m omaker.llm.optimize --install`; used only with OMAKER_LLM_PROMPT=optimized.
OPTIMIZED_PROMPT = Path(__file__).parent / "prompts" / "relations_optimized.json"


def _pair_line(sentence, subject, subject_type, obj, object_type) -> str:
    return f'sentence: "{sentence.strip()}" | subject: "{subject}" ({subject_type}) | object: "{obj}" ({object_type})'


def optimized_system(prompt: dict) -> str:
    """System prompt from the exported prompt: instruction, worked examples, then the JSON request."""
    parts = [prompt["instruction"].strip()]
    examples = prompt.get("examples") or []
    if examples:
        lines = [_pair_line(e["sentence"], e["subject"], e["subject_type"], e["object"], e["object_type"])
                 + f" -> {e['relation']}" for e in examples]
        parts.append("Examples:\n" + "\n".join(lines))
    parts.append("Return JSON only.")
    return "\n\n".join(parts)


def relation_system(log) -> str:
    """The handwritten prompt, or the optimized one when OMAKER_LLM_PROMPT=optimized and the file exists."""
    if llm_prompt() != "optimized":
        return RELATION_SYSTEM
    if not OPTIMIZED_PROMPT.is_file():
        log(f"> [LLM] OMAKER_LLM_PROMPT=optimized, but {OPTIMIZED_PROMPT} does not exist: using the default prompt.")
        return RELATION_SYSTEM
    log(f"> [LLM] Using the optimized relation prompt ({OPTIMIZED_PROMPT.name}).")
    return optimized_system(json.loads(OPTIMIZED_PROMPT.read_text(encoding="utf-8")))


def classify_pairs(client: LLMClient, pairs: list[dict], temperature: float, log,
                   system: str | None = None) -> list[tuple[str, None]]:
    """Classifies candidate pairs with the LLM when there is no trained PURE checkpoint (no confidence).

    `system` replaces the prompt chosen by OMAKER_LLM_PROMPT (omaker.evaluation.llm_batch compares both).
    """
    log("> [LLM] No trained PURE checkpoint found: classifying pairs with the LLM (no confidence scores).")
    system = system or relation_system(log)
    out = [(NO_RELATION, None)] * len(pairs)
    for start in range(0, len(pairs), PAIR_BATCH):
        chunk = pairs[start:start + PAIR_BATCH]
        lines = [f"{start + i}. " + _pair_line(p["text"], p["sub_name"], p["sub_type"], p["obj_name"], p["obj_type"])
                 for i, p in enumerate(chunk)]
        data = client.chat_json(system, "\n".join(lines), RELATION_SCHEMA, temperature=temperature)
        for r in data.get("results", []):
            idx = r.get("id")
            if isinstance(idx, int) and 0 <= idx < len(pairs) and r.get("relation") in RELATIONS:
                out[idx] = (r["relation"], None)
    return out
