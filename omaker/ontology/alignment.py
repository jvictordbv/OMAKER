"""Alinhamento com ontologias externas (por exemplo a Symptom Ontology).

Ao atualizar uma ontologia que não foi gerada pelo OMAKER, as classes-base do OMAKER (Drug, Disease,
Symptom) que já existem nela, pelo rótulo, são reaproveitadas; o que falta é criado num namespace
próprio, em vez de dentro do namespace da ontologia alheia.
"""
from __future__ import annotations

import re

from omaker.domain.labels import ROOT_CLASS

OMAKER_NAMESPACE = "http://www.mestrado.edu/ontologias/omaker#"
EXACT_SYNONYM = "http://www.geneontology.org/formats/oboInOwl#hasExactSynonym"


def norm_term(text) -> str:
    """Minúsculas, com espaços e "_" tratados como iguais."""
    return re.sub(r"[\s_]+", " ", str(text)).strip().casefold()


def camel_to_words(name: str) -> str:
    """Nome de classe CamelCase em palavras ("BackPain" vira "Back Pain"), para casar com rótulos."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)


def _deprecated(cls) -> bool:
    return any(str(v).strip().lower() == "true" for v in getattr(cls, "deprecated", []))


def build_label_index(onto) -> dict:
    """Termo normalizado para classe: rótulos primeiro, depois sinônimos exatos, depois nomes.
    Ficam de fora as classes criadas pelo OMAKER (OMAKER_NAMESPACE) e as obsoletas (owl:deprecated),
    que na SYMP compartilham sinônimos com as classes em uso ("mammitis", "apoplexy")."""
    classes = [c for c in onto.classes() if not c.iri.startswith(OMAKER_NAMESPACE) and not _deprecated(c)]
    synonym = onto.world[EXACT_SYNONYM]
    index: dict = {}
    for keys_of in (lambda c: c.label,
                    lambda c: synonym[c] if synonym is not None else [],
                    lambda c: [c.name]):
        for cls in classes:
            for key in keys_of(cls):
                index.setdefault(norm_term(key), cls)
    return index


def is_external(onto) -> bool:
    """Tem classes e não foi gerada pelo OMAKER (não tem a classe raiz no próprio namespace)."""
    return onto[ROOT_CLASS] is None and next(iter(onto.classes()), None) is not None


def aligned_class(index: dict, entity_text: str, base_cls):
    """Classe existente para a entidade (rótulo, sinônimo exato ou nome), desde que esteja no ramo do tipo
    dela (base_cls ou uma descendente). Fora do ramo, None: um DRUG não vira instância de um sintoma."""
    cls = index.get(norm_term(entity_text))
    if cls is None:
        return None
    return cls if (cls is base_cls or base_cls in cls.ancestors()) else None
