import json

import pytest

from omaker.domain.labels import REL2ID
from omaker.relations.data import (
    RelationExample,
    load_examples,
    load_splits,
    save_splits,
    sha256_of,
    split_examples,
)
from omaker.relations.train import DATA_PATH


def _ex(text, rel):
    return RelationExample(text, "A", "DRUG", "B", "DISEASE", rel)


def test_load_current_dataset():
    examples = load_examples(DATA_PATH)
    assert len(examples) == 31
    assert all(e.relation in REL2ID for e in examples)


def test_unknown_relation_is_reported_with_index(tmp_path):
    rows = [
        {"text": "x", "sub_name": "a", "sub_type": "DRUG", "obj_name": "b", "obj_type": "DISEASE", "relation": "treats"},
        {"text": "y", "sub_name": "a", "sub_type": "DRUG", "obj_name": "b", "obj_type": "DISEASE", "relation": "cures"},
    ]
    path = tmp_path / "d.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ValueError, match="exemplo 1: relação desconhecida 'cures'"):
        load_examples(path)


def test_unknown_type_is_reported_with_index(tmp_path):
    rows = [{"text": "x", "sub_name": "a", "sub_type": "PLANET", "obj_name": "b", "obj_type": "DISEASE",
             "relation": "treats"}]
    path = tmp_path / "d.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ValueError, match="exemplo 0: tipo desconhecido 'PLANET'"):
        load_examples(path)


def test_split_is_deterministic_and_disjoint_by_text():
    examples = load_examples(DATA_PATH)
    a, b = split_examples(examples, seed=42), split_examples(examples, seed=42)
    assert (a.train, a.dev, a.test) == (b.train, b.dev, b.test)
    texts = [{e.text for e in part} for part in (a.train, a.dev, a.test)]
    assert not (texts[0] & texts[1]) and not (texts[0] & texts[2]) and not (texts[1] & texts[2])
    assert len(a.train) + len(a.dev) + len(a.test) == 31
    assert a.dev and a.test


def test_split_falls_back_when_class_too_small():
    examples = [_ex(f"t{i}", "treats" if i % 2 else "causes") for i in range(9)] + [_ex("raro", "prevents")]
    splits = split_examples(examples, seed=1)
    assert splits.manifest["stratified"] is False
    assert len(splits.train) + len(splits.dev) + len(splits.test) == 10


def test_save_and_load_roundtrip(tmp_path):
    examples = load_examples(DATA_PATH)
    splits = split_examples(examples, seed=7, source_sha256=sha256_of(DATA_PATH))
    save_splits(splits, tmp_path / "splits")
    loaded = load_splits(tmp_path / "splits")
    assert (loaded.train, loaded.dev, loaded.test) == (splits.train, splits.dev, splits.test)
    assert loaded.manifest == splits.manifest
    assert len(loaded.manifest["source_sha256"]) == 64
