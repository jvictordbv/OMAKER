"""Builds / extends an OWL ontology with owlready2 from a validated taxonomy and relation triples.

`populate` is idempotent (it reuses entities that already exist), so the same code
serves both "generate new ontology" and "update existing ontology".
"""
from __future__ import annotations

import enum
import os
import shutil
import types
from dataclasses import dataclass

import owlready2
from owlready2 import AllDisjoint, ObjectProperty, Thing, World, sync_reasoner_hermit
from owlready2.base import OwlReadyInconsistentOntologyError

from omaker.domain.labels import BASE_CLASSES, RELATION_DOMAIN, ROOT_CLASS
from omaker.domain.text import to_identifier
from omaker.ontology.alignment import (
    OMAKER_NAMESPACE,
    aligned_class,
    build_label_index,
    camel_to_words,
    is_external,
    norm_term,
)


class ReasonerStatus(enum.Enum):
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"
    UNAVAILABLE = "unavailable"


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
    # Ontologia externa (ex.: symp.owl): reaproveita classes-base que já existem nela, pelo rótulo, e cria o
    # resto no namespace do OMAKER, para não inventar termos dentro do namespace alheio [#9].
    external = is_external(onto)
    index = build_label_index(onto) if external else {}
    ns = onto.get_namespace(OMAKER_NAMESPACE) if external else onto
    reused = set()

    def lookup(name):
        return onto.world[OMAKER_NAMESPACE + name] if external else onto[name]

    with onto:
        def get_or_make_class(name, parent):
            existing = lookup(name)
            if existing is not None:
                return existing
            with ns:
                return types.new_class(name, (parent,))

        def base_of(cls):
            ancestors = cls.ancestors()
            return next((classes[b] for b in BASE_CLASSES.values() if classes[b] in ancestors), None)

        root = get_or_make_class(ROOT_CLASS, Thing)
        classes = {ROOT_CLASS: root}
        for base in BASE_CLASSES.values():
            match = index.get(norm_term(base))
            if match is not None:
                classes[base] = match
                reused.add(match)
                log(f"  [ALIGN] {base} = {match.iri}")
            else:
                classes[base] = get_or_make_class(base, root)

        pending = dict(taxonomy["classes"])
        while pending:  # parents first
            ready = [n for n, p in pending.items() if p in classes]
            if not ready:  # defensive: unresolved parents hang under the root
                ready = list(pending)
                for n in ready:
                    pending[n] = ROOT_CLASS
            for n in ready:
                parent = classes[pending.pop(n)]
                match = None
                if external:  # subclasse proposta pelo LLM que a ontologia já tem ("Pain" é o "pain" da SYMP)
                    base = base_of(parent)
                    match = aligned_class(index, camel_to_words(n), base) if base is not None else None
                if match is not None:
                    classes[n] = match
                    reused.add(match)
                    log(f"  [ALIGN] {n} = {match.iri}")
                else:
                    classes[n] = get_or_make_class(n, parent)

        props = {}
        for rel, domain in RELATION_DOMAIN.items():
            prop = lookup(rel)
            if prop is None:
                with ns:
                    prop = types.new_class(rel, (ObjectProperty,))
            if domain and classes[domain] not in prop.domain:
                prop.domain.append(classes[domain])
            props[rel] = prop

        individuals = {}
        for name, cls_name in taxonomy["instances"].items():
            ident = to_identifier(name)
            if ident in classes:  # an individual must not share an IRI with a class
                ident += "_ind"
            ind = lookup(ident)
            if ind is None:
                target = classes[cls_name]
                if external:  # a classe que a ontologia já tem para essa entidade, se houver, é mais específica
                    base = base_of(target)
                    match = aligned_class(index, name, base) if base is not None else None
                    if match is not None:
                        target = match
                        log(f"  [ALIGN] {name} -> {match.iri}")
                ind = target(ident, namespace=ns)
                ind.label.append(name)
            individuals[name.lower()] = ind

        added = 0
        for sub, _sub_type, rel, obj, _obj_type, conf in triples:
            s, o = individuals.get(sub.lower()), individuals.get(obj.lower())
            if s is None or o is None:
                continue
            values = getattr(s, rel)
            if o not in values:
                values.append(o)
                added += 1
                tag = "LLM" if conf is None else f"{conf:.0%}"
                log(f"  [AXIOM] {sub} --[{rel}]--> {obj} ({tag})")

        # Disjunções só entre classes do OMAKER: não se impõe axioma a classes de uma ontologia alheia.
        existing = [set(d.entities) for d in onto.disjoint_classes()]

        def add_disjoint(members):  # não repete o mesmo axioma a cada atualização
            if len(members) > 1 and set(members) not in existing:
                AllDisjoint(members)
                existing.append(set(members))

        for group in taxonomy.get("disjoint", []):
            add_disjoint([classes[c] for c in group if c in classes and classes[c] not in reused])
        # base types never overlap
        add_disjoint([classes[b] for b in BASE_CLASSES.values() if classes[b] not in reused])

    log(f"> [OWL] {len(classes) - 1} classes, {len(individuals)} individuals, {added} new relations.")
    return added


def run_reasoner(world, log=print, java_exe: str = "") -> ReasonerStatus:
    if java_exe and not os.path.exists(java_exe):
        log(f"> [HERMIT] O Java informado não existe ({java_exe}); tentando o 'java' do PATH.")
        java_exe = ""
    java_exe = java_exe or shutil.which("java") or ""
    if not java_exe:
        log("> [HERMIT] Java não encontrado. Instale o Java 11+ ou informe o caminho do Protégé "
            "nas Configurações (o OMAKER usa o Java que vem com ele).")
        return ReasonerStatus.UNAVAILABLE
    owlready2.JAVA_EXE = java_exe
    log("> [HERMIT] Running the reasoner for logical validation...")
    try:
        sync_reasoner_hermit(world, infer_property_values=True)
        log("> [HERMIT] Consistent graph, inferences materialized.")
        return ReasonerStatus.CONSISTENT
    except OwlReadyInconsistentOntologyError as err:
        log(f"> [HERMIT] LOGICAL INCONSISTENCY detected: {err}")
        log("> [HERMIT] The file will be saved, but it needs review.")
        return ReasonerStatus.INCONSISTENT
    except Exception as e:  # noqa: BLE001  HermiT/Java pode falhar de muitas formas; vira status UNAVAILABLE
        log(f"> [HERMIT] Could not run (verifique o Java): {e}")
        return ReasonerStatus.UNAVAILABLE


def save(onto, path: str):
    onto.save(file=path, format="rdfxml")
    return path


# ----------------------------------------------------------------------------- synonyms
@dataclass(frozen=True)
class EquivalenceReport:
    added: int                      # pares owl:equivalentClass gravados
    groups_written: list            # grupos (termos achados) que geraram equivalências
    not_found: list                 # termos sem classe correspondente na ontologia
    path: str                       # arquivo gravado


_norm_term = norm_term


def add_equivalences(src_path: str, groups: dict, dest_path: str, log=print) -> EquivalenceReport:
    """Grava owl:equivalentClass entre as classes de cada grupo de sinônimos, numa cópia (dest_path).

    Cada termo casa com a classe cujo rdfs:label ou nome é igual a ele, sem diferenciar maiúsculas
    (espaços e "_" contam como iguais). Grupos com menos de duas classes achadas são ignorados.
    src_path nunca é alterado.
    """
    _world, onto = load_world_ontology(src_path)
    index = {}
    for cls in onto.classes():
        for key in [cls.name, *cls.label]:
            index.setdefault(_norm_term(key), cls)

    added, written, not_found = 0, [], []
    for terms in groups.values():
        found = []
        for term in terms:
            cls = index.get(_norm_term(term))
            if cls is None:
                not_found.append(term)
            elif all(cls is not c for _, c in found):
                found.append((term, cls))
        if len(found) < 2:
            log(f"  [SKIP] {', '.join(terms)}: menos de duas classes encontradas na ontologia.")
            continue
        first = found[0][1]
        for _, other in found[1:]:
            if other not in first.equivalent_to:
                first.equivalent_to.append(other)
                added += 1
        written.append([term for term, _ in found])

    if added == 0:
        log("> [SYNONYMS] Nenhuma equivalência nova; nenhum arquivo foi criado.")
        return EquivalenceReport(0, written, not_found, "")
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    save(onto, dest_path)
    log(f"> [SYNONYMS] {added} owl:equivalentClass gravados em {dest_path}")
    return EquivalenceReport(added, written, not_found, dest_path)
