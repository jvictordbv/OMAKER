"""Métricas de extração de relações.

A métrica principal é o micro-F1 sobre as relações positivas (no_relation fora), o padrão da área.
Com conjuntos pequenos, o valor pontual engana: bootstrap_ci dá o intervalo de confiança.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from omaker.domain.labels import NO_RELATION


@dataclass(frozen=True)
class PRF:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


def _prf(tp: int, fp: int, fn: int) -> PRF:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return PRF(p, r, f, tp, fp, fn)


def classification_prf(golds: list[str], preds: list[str], negative: str = NO_RELATION) -> dict:
    """micro (PRF nas relações positivas), macro_f1 (média nas relações positivas do gabarito) e per_class."""
    labels = sorted({g for g in golds if g != negative} | {p for p in preds if p != negative})
    per_class = {}
    for lab in labels:
        tp = sum(g == lab and p == lab for g, p in zip(golds, preds, strict=True))
        fp = sum(g != lab and p == lab for g, p in zip(golds, preds, strict=True))
        fn = sum(g == lab and p != lab for g, p in zip(golds, preds, strict=True))
        per_class[lab] = _prf(tp, fp, fn)
    micro = _prf(sum(c.tp for c in per_class.values()), sum(c.fp for c in per_class.values()),
                 sum(c.fn for c in per_class.values()))
    in_gold = [lab for lab in labels if lab in set(golds)]
    macro = sum(per_class[lab].f1 for lab in in_gold) / len(in_gold) if in_gold else 0.0
    return {"micro": micro, "macro_f1": macro, "per_class": per_class}


def set_prf(gold: set, predicted: set) -> PRF:
    tp = len(gold & predicted)
    return _prf(tp, len(predicted - gold), len(gold - predicted))


def bootstrap_ci(golds, preds, metric, n: int = 1000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    """Intervalo percentil de metric(golds, preds), reamostrando os índices com reposição."""
    rng = random.Random(seed)
    size = len(golds)
    if size == 0:
        return (0.0, 0.0)
    values = []
    for _ in range(n):
        idx = [rng.randrange(size) for _ in range(size)]
        values.append(metric([golds[i] for i in idx], [preds[i] for i in idx]))
    values.sort()
    lo = values[int((alpha / 2) * (n - 1))]
    hi = values[int((1 - alpha / 2) * (n - 1))]
    return (lo, hi)
