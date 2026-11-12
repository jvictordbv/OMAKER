"""Taxonomy prompt for the LLM and validation of its answer (classes, instance typing, disjointness)."""
from __future__ import annotations

import re

from omaker.domain.labels import BASE_CLASSES, ROOT_CLASS
from omaker.domain.text import to_identifier
from omaker.llm.client import LLMClient

# Characters of the source text sent with the taxonomy prompt (keeps the request inside the model context).
TAXONOMY_TEXT_LIMIT = 6000

TAXONOMY_SCHEMA = {
    "type": "object",
    "properties": {
        "classes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "parent": {"type": "string"}},
                "required": ["name", "parent"],
            },
        },
        "instances": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "class": {"type": "string"}},
                "required": ["name", "class"],
            },
        },
        "disjoint": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
    },
    "required": ["classes", "instances", "disjoint"],
}

TAXONOMY_SYSTEM = f"""You are a senior knowledge engineer specialised in biomedical ontologies (OWL / Description Logic).
You receive a text and the biomedical entities already detected in it. Organise them into a class hierarchy.

Rules:
1. Base classes already exist: {', '.join(BASE_CLASSES.values())}. Never redefine them.
2. "classes": propose subclasses ONLY when the text or well-established medical knowledge supports them
   (e.g. Analgesic under Drug, Infection under Disease). Every parent must be a base class or another class you define.
   Use singular CamelCase names. Do NOT create a class for an individual entity.
3. "instances": assign EVERY entity to its most specific class. Copy entity names EXACTLY as given. Never add new entities.
   Apply the is-a test: every member of a subclass must truly be an instance of it. Do not group things by body
   system or purpose unless that is genuinely what they are; if unsure, use the base class. Prefer few, well-justified
   classes over many.
4. "disjoint": groups of sibling classes that cannot share members. Leave empty if unsure.
5. Do not output relations. Output only JSON matching the schema."""


def validate_taxonomy(raw: dict, entities) -> dict:
    """Turns the LLM answer into a safe taxonomy. Anything inconsistent falls back to the NER type."""
    base_names = set(BASE_CLASSES.values())
    base_of_type = dict(BASE_CLASSES)
    def norm(s):
        return re.sub(r"[\W_]+", "", s.lower())

    entity_keys = {norm(e.text) for e in entities}

    parents = {}
    redirect = {}  # class name -> parent, for classes that duplicate an entity name
    for c in raw.get("classes", []):
        name = to_identifier(str(c.get("name", "")), capitalize=True)
        parent = to_identifier(str(c.get("parent", "")), capitalize=True) if c.get("parent") else ROOT_CLASS
        if name in base_names or name == ROOT_CLASS or name in parents:
            continue
        if norm(name) in entity_keys:  # a class must not duplicate an entity ("CardiovascularDisease" vs "cardiovascular disease")
            redirect[name] = parent
            continue
        parents[name] = parent

    valid_parents = base_names | {ROOT_CLASS}
    for name in list(parents):  # unknown parent -> root
        p = redirect.get(parents[name], parents[name])
        parents[name] = p if (p in parents or p in valid_parents) else ROOT_CLASS

    def ancestors(name):
        chain, seen = [], set()
        while name in parents and name not in seen:
            seen.add(name)
            name = parents[name]
            chain.append(name)
        return chain

    for name in list(parents):  # break cycles
        if name in ancestors(name):
            parents[name] = ROOT_CLASS

    def root_base(cls):
        return ([cls] + ancestors(cls))[-1]  # top of the chain: a base class or the root

    instances = {}
    raw_inst = {str(i.get("name", "")).lower(): to_identifier(str(i.get("class", "")), capitalize=True)
                for i in raw.get("instances", [])}
    for e in entities:
        base = base_of_type[e.type]
        cls = raw_inst.get(e.text.lower())
        cls = redirect.get(cls, cls)
        # accept the LLM class only if it exists and descends from the entity's own base type
        instances[e.text] = cls if (cls in parents and root_base(cls) == base) else base

    disjoint = []
    for group in raw.get("disjoint", []):
        members = [to_identifier(str(g), capitalize=True) for g in group]
        members = [m for m in members if m in parents]
        related = any(a in ancestors(b) or b in ancestors(a) for a in members for b in members if a != b)
        if len(set(members)) > 1 and not related:
            disjoint.append(sorted(set(members)))
    return {"classes": parents, "instances": instances, "disjoint": disjoint}


def ask_taxonomy(client: LLMClient, entities, text: str, temperature: float, log) -> dict:
    """Asks the LLM to organise the entities into classes, then validates the answer."""
    log(f"> [LLM] Asking {client.model} for taxonomy (subclasses, instance typing)...")
    listing = "\n".join(f"- {e.text} ({e.type})" for e in entities)
    if len(text) > TAXONOMY_TEXT_LIMIT:
        log(f"> [WARNING] Text has {len(text)} characters; the taxonomy prompt uses only the first "
            f"{TAXONOMY_TEXT_LIMIT}. Entities and relations still come from the whole text.")
    user = f"Entities:\n{listing}\n\nText:\n{text[:TAXONOMY_TEXT_LIMIT]}"
    raw = client.chat_json(TAXONOMY_SYSTEM, user, TAXONOMY_SCHEMA, temperature=temperature)
    taxonomy = validate_taxonomy(raw, entities)
    log(f"> [LLM] {len(taxonomy['classes'])} extra classes, {len(taxonomy['disjoint'])} disjoint groups.")
    return taxonomy
