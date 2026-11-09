"""Builds / extends an OWL ontology with owlready2 from a validated taxonomy and relation triples.

`populate` is idempotent (it reuses entities that already exist), so the same code
serves both "generate new ontology" and "update existing ontology".
"""
from __future__ import annotations

import os
import shutil
import types

import owlready2
from owlready2 import AllDisjoint, ObjectProperty, Thing, World, sync_reasoner_hermit
from owlready2.base import OwlReadyInconsistentOntologyError

from core.labels import BASE_CLASSES, RELATION_DOMAIN, ROOT_CLASS
from core.text_utils import to_identifier

def new_world_ontology(uri: str):
    world = World()
    return world, world.get_ontology(uri)


def load_world_ontology(path: str):
    world = World()
    onto = world.get_ontology(f"file://{os.path.abspath(path)}".replace("\\", "/")).load()
    return world, onto


def populate(onto, taxonomy: dict, triples: list, log=print):
    """taxonomy: {"classes": {name: parent}, "instances": {name: class}, "disjoint": [[...]]}
    triples: (subject, subject_type, relation, object, object_type, confidence|None)
    """
    with onto:
        def get_or_make_class(name, parent):
            existing = onto[name]
            return existing if existing is not None else types.new_class(name, (parent,))

        root = get_or_make_class(ROOT_CLASS, Thing)
        classes = {ROOT_CLASS: root}
        for base in BASE_CLASSES.values():
            classes[base] = get_or_make_class(base, root)

        pending = dict(taxonomy["classes"])
        while pending:  # parents first
            ready = [n for n, p in pending.items() if p in classes]
            if not ready:  # defensive: unresolved parents hang under the root
                ready = list(pending)
                for n in ready:
                    pending[n] = ROOT_CLASS
            for n in ready:
                classes[n] = get_or_make_class(n, classes[pending.pop(n)])

        props = {}
        for rel, domain in RELATION_DOMAIN.items():
            prop = onto[rel] if onto[rel] is not None else types.new_class(rel, (ObjectProperty,))
            if domain and classes[domain] not in prop.domain:
                prop.domain.append(classes[domain])
            props[rel] = prop

        individuals = {}
        for name, cls_name in taxonomy["instances"].items():
            ident = to_identifier(name)
            if ident in classes:  # an individual must not share an IRI with a class
                ident += "_ind"
            ind = onto[ident]
            if ind is None:
                ind = classes[cls_name](ident)
                ind.label.append(name)
            individuals[name.lower()] = ind

        added = 0
        for sub, sub_type, rel, obj, obj_type, conf in triples:
            s, o = individuals.get(sub.lower()), individuals.get(obj.lower())
            if s is None or o is None:
                continue
            values = getattr(s, rel)
            if o not in values:
                values.append(o)
                added += 1
                tag = "LLM" if conf is None else f"{conf:.0%}"
                log(f"  [AXIOM] {sub} --[{rel}]--> {obj} ({tag})")

        for group in taxonomy.get("disjoint", []):
            members = [classes[c] for c in group if c in classes]
            if len(members) > 1:
                AllDisjoint(members)
        # base types never overlap
        AllDisjoint([classes[b] for b in BASE_CLASSES.values()])

    log(f"> [OWL] {len(classes) - 1} classes, {len(individuals)} individuals, {added} new relations.")
    return added


def run_reasoner(world, log=print, java_exe: str = ""):
    if java_exe and not os.path.exists(java_exe):
        log(f"> [HERMIT] OMAKER_JAVA points to a file that does not exist ({java_exe}); trying 'java' from PATH.")
        java_exe = ""
    owlready2.JAVA_EXE = java_exe or shutil.which("java") or "java"
    log("> [HERMIT] Running the reasoner for logical validation...")
    try:
        sync_reasoner_hermit(world, infer_property_values=True)
        log("> [HERMIT] Consistent graph, inferences materialized.")
        return True
    except OwlReadyInconsistentOntologyError as err:
        log(f"> [HERMIT] LOGICAL INCONSISTENCY detected: {err}")
        log("> [HERMIT] The file will be saved, but it needs review.")
    except Exception as e:
        log(f"> [HERMIT] Could not run (check Java / OMAKER_JAVA): {e}")
    return False


def save(onto, path: str):
    onto.save(file=path, format="rdfxml")
    return path