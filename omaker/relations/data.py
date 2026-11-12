"""Exemplos de extração de relações e divisão fixa train/dev/test.

A divisão é agrupada por texto (a mesma frase nunca cai em dois conjuntos) e, quando cada relação tem
ao menos três grupos, estratificada pela relação. O manifesto guarda a semente, as proporções, o hash
do arquivo de origem e as contagens, para que a mesma divisão seja relida em vez de sorteada de novo.

Para outro dataset (decisão D5), basta um leitor que devolva list[RelationExample].
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from omaker.domain.labels import BASE_CLASSES, REL2ID

PARTS = ("train", "dev", "test")


@dataclass(frozen=True)
class RelationExample:
    text: str
    sub_name: str
    sub_type: str
    obj_name: str
    obj_type: str
    relation: str
    sub_span: tuple[int, int] | None = None
    obj_span: tuple[int, int] | None = None


@dataclass(frozen=True)
class Splits:
    train: list[RelationExample]
    dev: list[RelationExample]
    test: list[RelationExample]
    manifest: dict


def _example(i: int, row: dict) -> RelationExample:
    if row["relation"] not in REL2ID:
        raise ValueError(f"exemplo {i}: relação desconhecida '{row['relation']}'")
    for key in ("sub_type", "obj_type"):
        if row[key] not in BASE_CLASSES:
            raise ValueError(f"exemplo {i}: tipo desconhecido '{row[key]}'")
    spans = {k: tuple(row[k]) for k in ("sub_span", "obj_span") if row.get(k) is not None}
    return RelationExample(row["text"], row["sub_name"], row["sub_type"], row["obj_name"], row["obj_type"],
                           row["relation"], **spans)


def load_examples(path) -> list[RelationExample]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [_example(i, row) for i, row in enumerate(rows)]


def sha256_of(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _allocate(groups: list, fractions, rng: random.Random) -> dict:
    """Embaralha os grupos e reparte: dev e test com ao menos um grupo cada; o resto vai para o treino."""
    groups = sorted(groups)
    rng.shuffle(groups)
    n = len(groups)
    n_dev = max(1, round(n * fractions[1]))
    n_test = max(1, round(n * fractions[2]))
    return {"dev": groups[:n_dev], "test": groups[n_dev:n_dev + n_test], "train": groups[n_dev + n_test:]}


def split_examples(examples, seed: int = 42, fractions=(0.7, 0.15, 0.15), source_sha256: str = "") -> Splits:
    by_text: dict[str, list[RelationExample]] = defaultdict(list)
    for e in examples:
        by_text[e.text].append(e)
    group_label = {text: items[0].relation for text, items in by_text.items()}
    per_relation: dict[str, list[str]] = defaultdict(list)
    for text, rel in group_label.items():
        per_relation[rel].append(text)

    rng = random.Random(seed)
    stratified = all(len(texts) >= 3 for texts in per_relation.values())
    assigned: dict[str, list[str]] = {p: [] for p in PARTS}
    if stratified:
        for rel in sorted(per_relation):
            for part, texts in _allocate(per_relation[rel], fractions, rng).items():
                assigned[part].extend(texts)
    else:
        assigned = _allocate(list(by_text), fractions, rng)

    parts = {p: [e for text in sorted(assigned[p]) for e in by_text[text]] for p in PARTS}
    manifest = {
        "seed": seed,
        "fractions": list(fractions),
        "source_sha256": source_sha256,
        "stratified": stratified,
        "counts": {p: dict(sorted(Counter(e.relation for e in parts[p]).items())) for p in PARTS},
    }
    return Splits(parts["train"], parts["dev"], parts["test"], manifest)


def _to_row(e: RelationExample) -> dict:
    return {k: v for k, v in asdict(e).items() if v is not None}


def save_splits(splits: Splits, directory) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for part in PARTS:
        rows = [_to_row(e) for e in getattr(splits, part)]
        (directory / f"{part}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (directory / "manifest.json").write_text(json.dumps(splits.manifest, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    return directory


def load_splits(directory) -> Splits:
    directory = Path(directory)
    parts = {p: load_examples(directory / f"{p}.json") for p in PARTS}
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    return Splits(parts["train"], parts["dev"], parts["test"], manifest)
