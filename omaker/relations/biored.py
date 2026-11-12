"""Leitor do BioRED (Luo et al., 2022) para o esquema do OMAKER (decisão D5).

O BioRED anota relações por documento, entre conceitos (ids), sem direção. O PURE classifica pares dentro
de uma frase. A conversão:

- tipos: ChemicalEntity vira DRUG, DiseaseOrPhenotypicFeature vira DISEASE; os demais ficam de fora;
- rótulos: Positive_Correlation vira causes, Negative_Correlation vira treats; o sujeito é sempre o químico;
- cada par (id químico, id doença) presente na mesma frase gera um exemplo, com a primeira menção de cada id;
- par com relação de outro tipo (Association e afins) é descartado; par sem relação vira no_relation.

Limitação: o rótulo vem do documento, então uma frase pode citar os dois sem afirmar a relação.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from omaker.domain.labels import NO_RELATION
from omaker.domain.text import split_sentences
from omaker.relations.data import PARTS, RelationExample, Splits

BIORED_URL = "https://ftp.ncbi.nlm.nih.gov/pub/lu/BioRED/BIORED.zip"
OFFICIAL_FILES = {"train": "Train.PubTator", "dev": "Dev.PubTator", "test": "Test.PubTator"}
TYPE_MAP = {"ChemicalEntity": "DRUG", "DiseaseOrPhenotypicFeature": "DISEASE"}
LABEL_MAP = {"Positive_Correlation": "causes", "Negative_Correlation": "treats"}


@dataclass(frozen=True)
class Mention:
    start: int
    end: int
    text: str
    type: str
    ids: tuple[str, ...]


@dataclass(frozen=True)
class Document:
    pmid: str
    text: str
    mentions: tuple[Mention, ...]
    relations: tuple[tuple[str, str, str], ...]   # (tipo, id1, id2)


def parse_pubtator(content: str) -> list[Document]:
    docs: dict[str, dict] = {}
    for line in content.splitlines():
        if not line.strip():
            continue
        head = line[:30]
        if "|t|" in head or "|a|" in head:
            pmid, kind, body = line.split("|", 2)
            docs.setdefault(pmid, {"t": "", "a": "", "m": [], "r": []})[kind] = body
            continue
        fields = line.split("\t")
        doc = docs.setdefault(fields[0], {"t": "", "a": "", "m": [], "r": []})
        if len(fields) == 6:
            doc["m"].append(fields)
        elif len(fields) == 5:
            doc["r"].append((fields[1], fields[2], fields[3]))
        else:
            raise ValueError(f"PMID {fields[0]}: linha com {len(fields)} campos: {line[:80]!r}")

    out = []
    for pmid, d in docs.items():
        text = d["t"] + " " + d["a"]
        mentions = []
        for _, s, e, mtext, mtype, ids in d["m"]:
            start, end = int(s), int(e)
            if text[start:end] != mtext:
                raise ValueError(f"PMID {pmid}: offsets {start}-{end} não batem com '{mtext}'")
            mentions.append(Mention(start, end, mtext, mtype, tuple(i.strip() for i in ids.split(","))))
        out.append(Document(pmid, text, tuple(mentions), tuple(d["r"])))
    return out


def _pair_labels(doc: Document) -> dict[frozenset, str | None]:
    """Rótulo do OMAKER por par de ids; None quando a relação existe mas não é mapeada."""
    labels: dict[frozenset, str | None] = {}
    for rtype, a, b in doc.relations:
        key = frozenset((a, b))
        mapped = LABEL_MAP.get(rtype)
        if key in labels and labels[key] != mapped:
            labels[key] = None   # tipos conflitantes para o mesmo par: descarta
        else:
            labels[key] = mapped
    return labels


def document_examples(doc: Document) -> list[RelationExample]:
    labels = _pair_labels(doc)
    examples = []
    for s0, s1 in split_sentences(doc.text):
        first: dict[str, dict[str, Mention]] = {"DRUG": {}, "DISEASE": {}}
        for m in sorted(doc.mentions, key=lambda m: m.start):
            etype = TYPE_MAP.get(m.type)
            if etype is None or m.start < s0 or m.end > s1:
                continue
            for i in m.ids:
                first[etype].setdefault(i, m)
        sentence = doc.text[s0:s1]
        for chem_id, chem in first["DRUG"].items():
            for dis_id, dis in first["DISEASE"].items():
                if chem is dis or (chem.start < dis.end and dis.start < chem.end):
                    continue
                key = frozenset((chem_id, dis_id))
                if key in labels and labels[key] is None:
                    continue
                relation = labels.get(key) or NO_RELATION
                examples.append(RelationExample(
                    sentence, chem.text, "DRUG", dis.text, "DISEASE", relation,
                    sub_span=(chem.start - s0, chem.end - s0), obj_span=(dis.start - s0, dis.end - s0)))
    return _dedupe(examples)


def _dedupe(examples: list[RelationExample]) -> list[RelationExample]:
    """Uma menção com vários ids pode repetir o mesmo par de spans; fica o primeiro rótulo positivo."""
    best: dict[tuple, RelationExample] = {}
    for e in examples:
        key = (e.text, e.sub_span, e.obj_span)
        if key not in best or (best[key].relation == NO_RELATION and e.relation != NO_RELATION):
            best[key] = e
    return list(best.values())


def load_biored(directory) -> Splits:
    directory = Path(directory)
    digest = hashlib.sha256()
    parts = {}
    for part in PARTS:
        path = directory / OFFICIAL_FILES[part]
        if not path.exists():
            raise FileNotFoundError(f"{path} não existe. Baixe com: uv run python -m omaker.relations.biored "
                                    f"--download")
        content = path.read_bytes()
        digest.update(content)
        parts[part] = [e for doc in parse_pubtator(content.decode("utf-8")) for e in document_examples(doc)]
    manifest = {
        "seed": None,
        "fractions": None,
        "source_sha256": digest.hexdigest(),
        "stratified": False,
        "official_split": True,
        "source": "BioRED",
        "mapping": dict(LABEL_MAP),
        "types": dict(TYPE_MAP),
        "counts": {p: dict(sorted(Counter(e.relation for e in parts[p]).items())) for p in PARTS},
    }
    return Splits(parts["train"], parts["dev"], parts["test"], manifest)
