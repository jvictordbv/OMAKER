from core.ner import normalize_label


def test_label_prefix_only_stripped_at_start():
    assert normalize_label("b-sub-b-type") == "sub-b-type"


def test_label_prefix_variants():
    assert normalize_label("B-Disease") == "disease"
    assert normalize_label("I-chemical") == "chemical"
    assert normalize_label("disease") == "disease"
