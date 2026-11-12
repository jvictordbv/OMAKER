"""Hybrid OMAKER engine.

  text --> NER (entities) --> candidate pairs --> PURE (relations, with confidence)
                          \\-> Qwen3 via Ollama (taxonomy: subclasses, instance typing, disjointness)
                          --> owlready2 --> HermiT --> .owl

Qwen never invents entities or relations: it only organizes the entities the NER found.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from omaker.config import entity_source
from omaker.domain.labels import BASE_CLASSES, DEFAULT_CONFIDENCE_THRESHOLD, NO_RELATION, RELATION_DOMAIN
from omaker.llm.client import DEFAULT_MODEL, LLMClient, LLMError, OllamaClient
from omaker.llm.entities import extract_entities_llm, merge_entities
from omaker.llm.relations import classify_pairs
from omaker.llm.taxonomy import ask_taxonomy, validate_taxonomy
from omaker.ontology.builder import ReasonerStatus
from omaker.ontology.iri import DEFAULT_URI_BASE, normalize_base, ontology_iri
from omaker.paths import default_checkpoint_path


@dataclass(frozen=True)
class OntologyResult:
    path: str
    reasoner: ReasonerStatus
    relations_added: int


# ----------------------------------------------------------------------------- helpers
def unique_entities(entities):
    """One entry per lower-cased surface form; on conflicting types keep the best score."""
    best = {}
    for e in entities:
        key = e.text.lower()
        if key not in best or e.score > best[key].score:
            best[key] = e
    return list(best.values())


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
    @staticmethod
    def _client(modelo_llm, temp_llm, log):
        model = modelo_llm or DEFAULT_MODEL
        client = OllamaClient(model=model)
        client.check()
        return client

    @staticmethod
    def _relations_pure(pairs, log, checkpoint):
        from omaker.relations.model import RelationExtractorPURE

        log(f"> [PURE] Loading '{checkpoint}'...")
        model = RelationExtractorPURE.load(str(checkpoint))
        return model.predict(pairs)

    @staticmethod
    def extrair(texto, modelo_llm, temp_llm, log, ner=None, client: LLMClient | None = None, with_taxonomy=True):
        """text -> (taxonomy, triples). Separate from OWL building so it can be tested/reused."""
        from omaker.nlp.ner import BiomedicalNER
        from omaker.nlp.pairs import generate_pairs

        # Where entities come from: "ner" (model only), "llm" (Qwen only) or "both" (merged); OMAKER_ENTITIES.
        source = entity_source()
        client = client or HybridEngine._client(modelo_llm, temp_llm, log)

        entities = []
        if source in ("ner", "both"):
            log("> [NER] Detecting biomedical entities...")
            ner_model = ner or BiomedicalNER()
            entities = ner_model.extract(texto)
            log(f"> [NER] model found {len(entities)} mentions.")
            for word, label, score in getattr(ner_model, "last_rejected", [])[:10]:
                log(f"  [NER] ignored: '{word}' labelled {label} ({score:.2f})")
        if source in ("llm", "both"):
            log(f"> [LLM-NER] Asking {client.model} for entities (each one is verified in the text)...")
            try:
                llm_entities = extract_entities_llm(client, texto, temperature=min(temp_llm, 0.1))
            except LLMError as err:
                if source == "llm":
                    raise
                log(f"> [LLM-NER] skipped ({err}). Using the NER entities only.")
                llm_entities = []
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
                preds, threshold = classify_pairs(client, pairs, temp_llm, log), 0.0
            best = {}
            for p, (rel, conf) in zip(pairs, preds, strict=False):
                if rel == NO_RELATION or (conf is not None and conf < threshold):
                    continue
                key = (p["sub_name"].lower(), rel, p["obj_name"].lower())
                if key not in best or (conf or 0) > (best[key][5] or 0):
                    best[key] = (p["sub_name"], p["sub_type"], rel, p["obj_name"], p["obj_type"], conf)
            triples = filter_by_domain(list(best.values()), log)
        log(f"> [RELATIONS] {len(triples)} triples kept.")

        # with_taxonomy=False (avaliação de triplas): cada entidade fica na sua classe-base, sem chamar o LLM.
        taxonomy = ask_taxonomy(client, uniq, texto, temp_llm, log) if with_taxonomy else validate_taxonomy({}, uniq)
        return taxonomy, triples

    # ---- public API used by the GUI -----------------------------------------------------
    @staticmethod
    def construir(taxonomy, triples, nome_arquivo, pasta_destino, uri_base, log_callback, protege_exe=""):
        """taxonomy + triples -> .owl file, plus what the reasoner said about it."""
        from omaker.ontology import builder as owl_builder
        from omaker.ontology.java import find_java

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
    def gerar_ontologia(texto, nome_arquivo, modelo_llm, temp_llm, pasta_destino, uri_base, log_callback,
                        protege_exe=""):
        taxonomy, triples = HybridEngine.extrair(texto, modelo_llm, temp_llm, log_callback)
        return HybridEngine.construir(taxonomy, triples, nome_arquivo, pasta_destino, uri_base, log_callback,
                                      protege_exe=protege_exe)

    @staticmethod
    def atualizar_ontologia(caminho_owl, texto, log_callback, modelo_llm=DEFAULT_MODEL, temp_llm=0.1,
                            protege_exe=""):
        from omaker.ontology import builder as owl_builder
        from omaker.ontology.java import find_java

        taxonomy, triples = HybridEngine.extrair(texto, modelo_llm, temp_llm, log_callback)
        world, onto = owl_builder.load_world_ontology(caminho_owl)
        added = owl_builder.populate(onto, taxonomy, triples, log_callback)
        status = owl_builder.run_reasoner(world, log_callback, find_java(protege_exe) or "")
        owl_builder.save(onto, caminho_owl)
        log_callback("\n> [SUCCESS] Merge finished.")
        return OntologyResult(caminho_owl, status, added)
