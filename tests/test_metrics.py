import pytest

from omaker.evaluation.metrics import bootstrap_ci, classification_prf, set_prf


def test_micro_excludes_no_relation():
    golds = ["treats", "no_relation", "causes", "treats"]
    preds = ["treats", "treats", "no_relation", "causes"]
    m = classification_prf(golds, preds)["micro"]
    assert (m.tp, m.fp, m.fn) == (1, 2, 2)
    assert m.precision == pytest.approx(1 / 3) and m.recall == pytest.approx(1 / 3)


def test_per_class_and_macro():
    golds = ["treats", "treats", "causes"]
    preds = ["treats", "causes", "causes"]
    r = classification_prf(golds, preds)
    assert r["per_class"]["treats"].f1 == pytest.approx(2 / 3)     # P=1, R=1/2
    assert r["per_class"]["causes"].f1 == pytest.approx(2 / 3)     # P=1/2, R=1
    assert r["macro_f1"] == pytest.approx(2 / 3)


def test_set_prf():
    m = set_prf({"a", "b", "c"}, {"a", "d"})
    assert (m.tp, m.fp, m.fn) == (1, 1, 2)
    assert m.f1 == pytest.approx(0.4)


def test_empty_predictions():
    m = set_prf({"a"}, set())
    assert (m.precision, m.recall, m.f1) == (0.0, 0.0, 0.0)
    m = set_prf(set(), set())
    assert (m.precision, m.recall, m.f1) == (0.0, 0.0, 0.0)


def test_bootstrap_ci_contains_point_and_is_reproducible():
    golds = ["treats", "causes", "no_relation", "prevents"] * 5
    preds = ["treats", "no_relation", "no_relation", "prevents"] * 5

    def micro_f1(g, p):
        return classification_prf(g, p)["micro"].f1

    point = micro_f1(golds, preds)
    lo, hi = bootstrap_ci(golds, preds, micro_f1, n=300, seed=3)
    assert lo <= point <= hi
    assert (lo, hi) == bootstrap_ci(golds, preds, micro_f1, n=300, seed=3)
