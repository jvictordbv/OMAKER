"""Gabarito de ponta a ponta a partir do teste oficial do BioRED (100 resumos que nunca entram no treino).

O BioRED anota relações entre conceitos (ids), e um conceito aparece no texto com vários nomes. Protocolo:

- cada nome previsto é ligado aos conceitos do resumo que têm esse nome (comparação com norm_term);
- acerto: sujeito químico, objeto doença e a relação aceita para o par
  (Positive_Correlation aceita causes; Negative_Correlation aceita treats e prevents);
- cada par do gabarito conta um acerto só, mesmo previsto com vários nomes (as repetições são ignoradas);
- falso positivo: relação errada, par químico e doença sem relação anotada, direção invertida
  (doença como sujeito de um químico) ou entidade que o BioRED não anotou ("symptom", "patients");
- ignorado: pares com relação de outro tipo (Association e afins, rótulo incerto) e pares que o BioRED
  não anota para o OMAKER (doença e doença, químico e químico).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from omaker.ontology.alignment import norm_term
from omaker.relations.biored import OFFICIAL_FILES, Document, parse_pubtator

CHEMICAL, DISEASE = "ChemicalEntity", "DiseaseOrPhenotypicFeature"
ACCEPTED = {"Positive_Correlation": {"causes"}, "Negative_Correlation": {"treats", "prevents"}}


@dataclass(frozen=True)
class BioredGoldDoc:
    id: str
    text: str
    surfaces: dict = field(hash=False)   # nome normalizado -> ids de conceito
    types: dict = field(hash=False)      # id -> tipo do BioRED
    gold: dict = field(hash=False)       # (id químico, id doença) -> relações aceitas
    ignored: frozenset = frozenset()     # pares com relação de rótulo incerto
    heldout: bool = True
    triples: frozenset = frozenset()     # compatibilidade com GoldDoc (não usado na contagem)
    traps: tuple = ()


@dataclass(frozen=True)
class Score:
    tp: int
    fp: int
    fn: int
    ignored: int


def _gold_doc(doc: Document) -> BioredGoldDoc:
    surfaces: dict[str, set] = defaultdict(set)
    types: dict[str, str] = {}
    for m in doc.mentions:
        for i in m.ids:
            surfaces[norm_term(m.text)].add(i)
            types[i] = m.type
    gold: dict[tuple, set] = defaultdict(set)
    uncertain = set()
    for rtype, a, b in doc.relations:
        if {types.get(a), types.get(b)} != {CHEMICAL, DISEASE}:
            continue
        pair = (a, b) if types[a] == CHEMICAL else (b, a)
        if rtype in ACCEPTED:
            gold[pair] |= ACCEPTED[rtype]
        else:
            uncertain.add(pair)
    return BioredGoldDoc(f"biored-{doc.pmid}", doc.text, {k: frozenset(v) for k, v in surfaces.items()}, types,
                         dict(gold), frozenset(uncertain - set(gold)))


def gold_docs(documents) -> list[BioredGoldDoc]:
    return [_gold_doc(d) for d in documents]


def load_biored_gold(directory, limit: int | None = None) -> list[BioredGoldDoc]:
    path = Path(directory) / OFFICIAL_FILES["test"]
    if not path.exists():
        raise FileNotFoundError(f"{path} não existe. Baixe com: uv run python -m omaker.relations.biored --download")
    docs = gold_docs(parse_pubtator(path.read_text(encoding="utf-8")))
    return docs[:limit] if limit else docs


def score_doc(doc: BioredGoldDoc, preds) -> Score:
    tp = fp = ignored = 0
    hit: set[tuple] = set()
    for sub, rel, obj in preds:
        s_ids, o_ids = doc.surfaces.get(norm_term(sub), ()), doc.surfaces.get(norm_term(obj), ())
        if not s_ids or not o_ids:
            fp += 1   # entidade que o BioRED não anotou
            continue
        pairs = [(s, o) for s in s_ids for o in o_ids if doc.types[s] == CHEMICAL and doc.types[o] == DISEASE]
        if not pairs:
            reversed_pair = any(doc.types[s] == DISEASE for s in s_ids) and any(doc.types[o] == CHEMICAL
                                                                               for o in o_ids)
            if reversed_pair:
                fp += 1
            else:
                ignored += 1
            continue
        correct = [p for p in pairs if rel in doc.gold.get(p, ())]
        if correct:
            new = [p for p in correct if p not in hit]
            if new:
                tp += 1
                hit.add(new[0])
            else:
                ignored += 1   # o mesmo fato com outro nome
        elif any(p in doc.ignored for p in pairs):
            ignored += 1
        else:
            fp += 1
    return Score(tp, fp, len(doc.gold) - len(hit), ignored)
