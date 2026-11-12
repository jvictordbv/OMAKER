"""Hybrid OMAKER engine.

  text --> NER (entities) --> candidate pairs --> PURE (relations, with confidence)
                          \\-> Qwen3 via Ollama (taxonomy: subclasses, instance typing, disjointness)
                          --> owlready2 --> HermiT --> .owl

Qwen never invents entities or relations: it only organizes the entities the NER found.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from core.iri import DEFAULT_URI_BASE, normalize_base, ontology_iri
from core.labels import BASE_CLASSES, DEFAULT_CONFIDENCE_THRESHOLD, NO_RELATION, REL2ID, RELATION_DOMAIN, ROOT_CLASS
from core.llm_client import DEFAULT_MODEL, LLMError, OllamaClient
from core.llm_ner import extract_entities_llm, merge_entities
from core.owl_builder import ReasonerStatus
from core.paths import default_checkpoint_path
from core.text_utils import to_identifier


@dataclass(frozen=True)
class OntologyResult:
    path: str
    reasoner: ReasonerStatus
    relations_added: int

RELATIONS = [r for r in REL2ID if r != NO_RELATION]

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


# ----------------------------------------------------------------------------- helpers
def unique_entities(entities):
    """One entry per lower-cased surface form; on conflicting types keep the best score."""
    best = {}
    for e in entities:
        key = e.text.lower()
        if key not in best or e.score > best[key].score:
            best[key] = e
    return list(best.values())


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


def filter_by_domain(triples, log):
    """Drops triples that violate relation domains (e.g. a symptom 'treating' something)."""
    kept = []
    for t in triples:
        sub, sub_type, rel = t[0], t[1], t[2]
        need = RELATION_DOMAIN.get(rel)
        if need and BASE_CLASSES.get(sub_type.upper()) != need:
            log(f"  [SKIP] {sub} --[{rel}]--> {t[3]}: subject is a {sub_type}, '{rel}' requires a {need}.")
            continue
        kept.append(t)
    return kept


# ----------------------------------------------------------------------------- engine
class HybridEngine:
    # Where entities come from: "ner" (model only), "llm" (Qwen only) or "both" (merged).
    ENTITY_SOURCE = os.environ.get("OMAKER_ENTITIES", "both").lower()

    @staticmethod
    def _client(modelo_llm, temp_llm, log):
        model = modelo_llm or DEFAULT_MODEL
        if model.lower().startswith("gemini"):
            raise LLMError(f"'{model}' não é um modelo do Ollama; escolha um modelo local (ex.: {DEFAULT_MODEL}).")
        client = OllamaClient(model=model)
        client.check()
        return client

    @staticmethod
    def _relations_pure(pairs, log, checkpoint):
        from core.relation_extractor import RelationExtractorPURE

        log(f"> [PURE] Loading '{checkpoint}'...")
        model = RelationExtractorPURE.load(str(checkpoint))
        return model.predict(pairs)

    @staticmethod
    def _relations_llm(client, pairs, temp, log):
        log("> [LLM] No trained PURE checkpoint found: classifying pairs with the LLM (no confidence scores).")
        out = [(NO_RELATION, None)] * len(pairs)
        for start in range(0, len(pairs), 15):
            chunk = pairs[start:start + 15]
            lines = [f'{start + i}. sentence: "{p["text"].strip()}" | subject: "{p["sub_name"]}" ({p["sub_type"]}) '
                     f'| object: "{p["obj_name"]}" ({p["obj_type"]})' for i, p in enumerate(chunk)]
            data = client.chat_json(RELATION_SYSTEM, "\n".join(lines), RELATION_SCHEMA, temperature=temp)
            for r in data.get("results", []):
                idx = r.get("id")
                if isinstance(idx, int) and 0 <= idx < len(pairs) and r.get("relation") in RELATIONS:
                    out[idx] = (r["relation"], None)
        return out

    @staticmethod
    def extrair(texto, modelo_llm, temp_llm, log, ner=None, client=None):
        """text -> (taxonomy, triples). Separate from OWL building so it can be tested/reused."""
        from core.ner import BiomedicalNER
        from core.pair_generator import generate_pairs

        client = client or HybridEngine._client(modelo_llm, temp_llm, log)

        entities = []
        if HybridEngine.ENTITY_SOURCE in ("ner", "both"):
            log("> [NER] Detecting biomedical entities...")
            ner_model = ner or BiomedicalNER()
            entities = ner_model.extract(texto)
            log(f"> [NER] model found {len(entities)} mentions.")
            for word, label, score in getattr(ner_model, "last_rejected", [])[:10]:
                log(f"  [NER] ignored: '{word}' labelled {label} ({score:.2f})")
        if HybridEngine.ENTITY_SOURCE in ("llm", "both"):
            log(f"> [LLM-NER] Asking {client.model} for entities (each one is verified in the text)...")
            llm_entities = extract_entities_llm(client, texto, temperature=min(temp_llm, 0.1))
            log(f"> [LLM-NER] {len(llm_entities)} verified mentions.")
            entities = merge_entities(entities, llm_entities)
        uniq = unique_entities(entities)
        if not uniq:
            raise ValueError("No biomedical entities (drug / symptom / disease) were found in the text.")
        log(f"> [NER] {len(uniq)} unique entities: " + ", ".join(f"{e.text} ({e.type})" for e in uniq))

        pairs = generate_pairs(texto, entities)
        log(f"> [PAIRS] {len(pairs)} candidate pairs.")

        triples = []
        if pairs:
            checkpoint = default_checkpoint_path()
            if checkpoint.exists():
                preds = HybridEngine._relations_pure(pairs, log, checkpoint)
                threshold = DEFAULT_CONFIDENCE_THRESHOLD
            else:
                preds, threshold = HybridEngine._relations_llm(client, pairs, temp_llm, log), 0.0
            best = {}
            for p, (rel, conf) in zip(pairs, preds, strict=False):
                if rel == NO_RELATION or (conf is not None and conf < threshold):
                    continue
                key = (p["sub_name"].lower(), rel, p["obj_name"].lower())
                if key not in best or (conf or 0) > (best[key][5] or 0):
                    best[key] = (p["sub_name"], p["sub_type"], rel, p["obj_name"], p["obj_type"], conf)
            triples = filter_by_domain(list(best.values()), log)
        log(f"> [RELATIONS] {len(triples)} triples kept.")

        log(f"> [LLM] Asking {client.model} for taxonomy (subclasses, instance typing)...")
        listing = "\n".join(f"- {e.text} ({e.type})" for e in uniq)
        if len(texto) > TAXONOMY_TEXT_LIMIT:
            log(f"> [WARNING] Text has {len(texto)} characters; the taxonomy prompt uses only the first "
                f"{TAXONOMY_TEXT_LIMIT}. Entities and relations still come from the whole text.")
        user = f"Entities:\n{listing}\n\nText:\n{texto[:TAXONOMY_TEXT_LIMIT]}"
        raw = client.chat_json(TAXONOMY_SYSTEM, user, TAXONOMY_SCHEMA, temperature=temp_llm)
        taxonomy = validate_taxonomy(raw, uniq)
        log(f"> [LLM] {len(taxonomy['classes'])} extra classes, {len(taxonomy['disjoint'])} disjoint groups.")
        return taxonomy, triples

    # ---- public API used by the GUI -----------------------------------------------------
    @staticmethod
    def construir(taxonomy, triples, nome_arquivo, pasta_destino, uri_base, log_callback, protege_exe=""):
        """taxonomy + triples -> .owl file, plus what the reasoner said about it."""
        from core import owl_builder
        from core.java_locator import find_java

        if normalize_base(uri_base)[1]:
            log_callback(f"> [IRI] URI base vazia ou inválida; usando {DEFAULT_URI_BASE}")
        world, onto = owl_builder.new_world_ontology(ontology_iri(uri_base, nome_arquivo))
        added = owl_builder.populate(onto, taxonomy, triples, log_callback)
        status = owl_builder.run_reasoner(world, log_callback, find_java(protege_exe) or "")

        os.makedirs(pasta_destino or ".", exist_ok=True)
        caminho = owl_builder.save(onto, os.path.join(pasta_destino or ".", f"{nome_arquivo}.owl"))
        log_callback(f"\n> [SUCCESS] OWL knowledge graph saved to:\n{caminho}")
        return OntologyResult(caminho, status, added)

    @staticmethod
    def gerar_ontologia(texto, nome_arquivo, api_key, modelo_llm, temp_llm, pasta_destino, uri_base, log_callback,
                        protege_exe=""):
        taxonomy, triples = HybridEngine.extrair(texto, modelo_llm, temp_llm, log_callback)
        return HybridEngine.construir(taxonomy, triples, nome_arquivo, pasta_destino, uri_base, log_callback,
                                      protege_exe=protege_exe)

    @staticmethod
    def atualizar_ontologia(caminho_owl, texto, api_key, log_callback, modelo_llm=DEFAULT_MODEL, temp_llm=0.1,
                            protege_exe=""):
        from core import owl_builder
        from core.java_locator import find_java

        taxonomy, triples = HybridEngine.extrair(texto, modelo_llm, temp_llm, log_callback)
        world, onto = owl_builder.load_world_ontology(caminho_owl)
        added = owl_builder.populate(onto, taxonomy, triples, log_callback)
        status = owl_builder.run_reasoner(world, log_callback, find_java(protege_exe) or "")
        owl_builder.save(onto, caminho_owl)
        log_callback("\n> [SUCCESS] Merge finished.")
        return OntologyResult(caminho_owl, status, added)
