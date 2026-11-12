"""Avaliação de ponta a ponta: texto para triplas (sujeito, relação, objeto), contra um gabarito de documentos.

    uv run python -m omaker.evaluation.e2e --systems llm ner+llm pure

Casamento estrito (principal): sujeito e objeto iguais depois de normalizar (norm_term) e a mesma relação.
Casamento tolerante (só para comparação): um nome contido no outro ("diabetes" casa "type 2 diabetes").
As "armadilhas" do gabarito são pares que o texto menciona sem afirmar relação (negação, mera co-ocorrência).

Sistemas comparados (baselines):
- llm: entidades e relações pelo LLM;
- ner+llm: entidades pelo NER e pelo LLM, relações pelo LLM;
- pure: entidades pelo NER, relações pelo PURE treinado (exige checkpoint).
A taxonomia não é pedida ao LLM aqui: ela não entra na métrica.
"""
from __future__ import annotations

import argparse
import json
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from omaker.evaluation.metrics import PRF, set_prf
from omaker.ontology.alignment import norm_term
from omaker.paths import default_checkpoint_path, project_root

GOLD_SAMPLES = Path(__file__).parent / "gold" / "samples.json"
TRAIN_HINT = "uv run python -m omaker.relations.train --config configs/pure_base.toml --install"

SYSTEMS = {
    "llm": {"OMAKER_ENTITIES": "llm", "relations": "llm"},
    "ner+llm": {"OMAKER_ENTITIES": "both", "relations": "llm"},
    "pure": {"OMAKER_ENTITIES": "ner", "relations": "pure"},
}


@dataclass(frozen=True)
class GoldDoc:
    id: str
    text: str
    triples: frozenset
    traps: tuple   # ((sub, obj, motivo), ...)


def load_gold(path=GOLD_SAMPLES) -> list[GoldDoc]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [GoldDoc(d["id"], d["text"], frozenset(tuple(t) for t in d["triples"]),
                    tuple((t["sub"], t["obj"], t["why"]) for t in d.get("traps", [])))
            for d in data["docs"]]


def strict_key(sub, rel, obj) -> tuple:
    return (norm_term(sub), rel, norm_term(obj))


def _same(a: str, b: str) -> bool:
    a, b = norm_term(a), norm_term(b)
    return a == b or a in b or b in a


def lenient_match(pred, gold) -> bool:
    return _same(pred[0], gold[0]) and pred[1] == gold[1] and _same(pred[2], gold[2])


def _lenient(gold, preds) -> PRF:
    matched = sum(any(lenient_match(p, g) for g in gold) for p in preds)
    hit = sum(any(lenient_match(p, g) for p in preds) for g in gold)
    precision = matched / len(preds) if preds else 0.0
    recall = hit / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return PRF(precision, recall, f1, hit, len(preds) - matched, len(gold) - hit)


@contextmanager
def system_environment(name: str):
    """Aplica o ambiente do sistema durante a avaliação e restaura o anterior depois."""
    spec = SYSTEMS[name]
    changes = {"OMAKER_ENTITIES": spec["OMAKER_ENTITIES"]}
    if spec["relations"] == "llm":  # força as relações pelo LLM mesmo que exista um checkpoint treinado
        changes["OMAKER_CHECKPOINT"] = str(project_root() / "runs" / "_sem-checkpoint-para-baseline-llm.pt")
    saved = {k: os.environ.get(k) for k in changes}
    os.environ.update(changes)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def default_extract(text: str, model: str) -> list[tuple[str, str, str]]:
    from omaker.pipeline.engine import HybridEngine

    _tax, triples = HybridEngine.extrair(text, model, 0.1, lambda _msg: None, with_taxonomy=False)
    return [(t[0], t[2], t[3]) for t in triples]


def evaluate_system(name: str, docs, extract=None, model: str = "qwen3:8b") -> dict:
    if SYSTEMS[name]["relations"] == "pure" and not default_checkpoint_path().exists():
        raise FileNotFoundError(f"O sistema 'pure' precisa de um checkpoint treinado em {default_checkpoint_path()}. "
                                f"Treine com: {TRAIN_HINT}")
    extract = extract or default_extract
    per_doc, traps_hit = [], []
    tp = fp = fn = 0
    lenient_preds, lenient_gold = [], []
    with system_environment(name):
        for doc in docs:
            preds = [tuple(p) for p in extract(doc.text, model)]
            strict = set_prf({strict_key(*g) for g in doc.triples}, {strict_key(*p) for p in preds})
            tp, fp, fn = tp + strict.tp, fp + strict.fp, fn + strict.fn
            lenient_preds += [(doc.id, p) for p in preds]
            lenient_gold += [(doc.id, g) for g in doc.triples]
            for p in preds:
                why = next((w for s, o, w in doc.traps if _same(p[0], s) and _same(p[2], o)), None)
                if why:
                    traps_hit.append({"doc": doc.id, "pred": list(p), "why": why})
            per_doc.append({"doc": doc.id, "strict": asdict(strict), "lenient": asdict(_lenient(doc.triples, preds)),
                            "predicted": [list(p) for p in preds]})
    total_strict = set_prf(set(range(tp + fn)), set(range(fn, fn + tp + fp)))  # só as contagens importam
    by_doc_gold = {d.id: d.triples for d in docs}
    matched = sum(any(lenient_match(p, g) for g in by_doc_gold[d]) for d, p in lenient_preds)
    hit = sum(any(lenient_match(p, g) for dd, p in lenient_preds if dd == d) for d, g in lenient_gold)
    precision = matched / len(lenient_preds) if lenient_preds else 0.0
    recall = hit / len(lenient_gold) if lenient_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    total_lenient = PRF(precision, recall, f1, hit, len(lenient_preds) - matched, len(lenient_gold) - hit)
    return {"system": name, "strict": asdict(total_strict), "lenient": asdict(total_lenient),
            "traps_hit": traps_hit, "per_doc": per_doc}


def _report(results: list[dict], gold_path, model) -> str:
    rows = ["| Sistema | P estrita | R estrita | F1 estrito | F1 tolerante | Armadilhas |", "|---|---|---|---|---|---|"]
    for r in results:
        s, le = r["strict"], r["lenient"]
        rows.append(f"| {r['system']} | {s['precision']:.2f} | {s['recall']:.2f} | {s['f1']:.2f} | {le['f1']:.2f} "
                    f"| {len(r['traps_hit'])} |")
    return "\n".join([f"# {datetime.now():%Y-%m-%d}: avaliação de ponta a ponta", "",
                      f"Gabarito: `{gold_path}`. Modelo do LLM: `{model}`.", "", *rows, ""])


def main(argv=None) -> Path:
    ap = argparse.ArgumentParser(description="Avaliação de ponta a ponta com casamento estrito.")
    ap.add_argument("--systems", nargs="+", default=list(SYSTEMS), choices=list(SYSTEMS))
    ap.add_argument("--gold", default=str(GOLD_SAMPLES))
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--runs-dir", default=str(project_root() / "runs"))
    args = ap.parse_args(argv)
    docs = load_gold(args.gold)
    results = [evaluate_system(name, docs, model=args.model) for name in args.systems]
    run = Path(args.runs_dir) / f"{datetime.now():%Y%m%d-%H%M%S}-e2e"
    run.mkdir(parents=True, exist_ok=True)
    (run / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    report = _report(results, args.gold, args.model)
    (run / "report.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"Resultados em {run}")
    return run


if __name__ == "__main__":
    main()
