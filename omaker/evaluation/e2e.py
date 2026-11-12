"""Avaliação de ponta a ponta: texto para triplas (sujeito, relação, objeto), contra um gabarito de documentos.

    uv run python -m omaker.evaluation.e2e --systems llm ner+llm pure

Casamento estrito (principal): sujeito e objeto iguais depois de normalizar (norm_term) e a mesma relação.
Casamento tolerante (só para comparação): um nome contido no outro ("diabetes" casa "type 2 diabetes").
As "armadilhas" do gabarito são pares que o texto menciona sem afirmar relação (negação, mera co-ocorrência).

Sistemas comparados (baselines):
- llm: entidades e relações pelo LLM;
- ner+llm: entidades pelo NER e pelo LLM, relações pelo LLM;
- pure: entidades pelo NER, relações pelo PURE treinado (exige checkpoint);
- both+pure: entidades pelo NER e pelo LLM, relações pelo PURE (compara o classificador com ner+llm
  usando as mesmas entidades).
A taxonomia não é pedida ao LLM aqui: ela não entra na métrica. O LLM roda com temperatura 0 e semente
fixa (OMAKER_LLM_SEED). Os totais saem para todos os documentos e, à parte, só para os held-out.
Para os sistemas com PURE, as frases do gabarito são comparadas com os textos de treino guardados no
checkpoint (contaminação).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from omaker.domain.text import split_sentences
from omaker.evaluation.metrics import PRF, _prf, set_prf
from omaker.ontology.alignment import norm_term
from omaker.paths import default_checkpoint_path, project_root

GOLD_SAMPLES = Path(__file__).parent / "gold" / "samples.json"
TRAIN_HINT = "uv run python -m omaker.relations.train --config configs/pure_base.toml --install"

SYSTEMS = {
    "llm": {"OMAKER_ENTITIES": "llm", "relations": "llm"},
    "ner+llm": {"OMAKER_ENTITIES": "both", "relations": "llm"},
    "pure": {"OMAKER_ENTITIES": "ner", "relations": "pure"},
    "both+pure": {"OMAKER_ENTITIES": "both", "relations": "pure"},
}
EVAL_SEED = 0
EVAL_TEMPERATURE = 0.0


@dataclass(frozen=True)
class GoldDoc:
    id: str
    text: str
    triples: frozenset
    traps: tuple   # ((sub, obj, motivo), ...)
    heldout: bool = False


def load_gold(path=GOLD_SAMPLES) -> list[GoldDoc]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [GoldDoc(d["id"], d["text"], frozenset(tuple(t) for t in d["triples"]),
                    tuple((t["sub"], t["obj"], t["why"]) for t in d.get("traps", [])), bool(d.get("heldout")))
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

    try:
        _tax, triples = HybridEngine.extrair(text, model, EVAL_TEMPERATURE, lambda _msg: None, with_taxonomy=False)
    except ValueError as err:
        if "No biomedical entities" in str(err):  # nenhuma entidade: o sistema não previu nada neste documento
            return []
        raise
    return [(t[0], t[2], t[3]) for t in triples]


def check_preconditions(systems) -> None:
    """Falha antes de rodar qualquer sistema (os do LLM são lentos) se faltar o checkpoint do PURE."""
    if any(SYSTEMS[name]["relations"] == "pure" for name in systems) and not default_checkpoint_path().exists():
        raise FileNotFoundError(f"Os sistemas com PURE precisam de um checkpoint treinado em "
                                f"{default_checkpoint_path()}. Treine com: {TRAIN_HINT}")


def _sha256(path) -> str | None:
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def contamination(docs) -> list[dict] | None:
    """Frases do gabarito que estão entre os textos de treino do checkpoint do PURE (None: não verificável)."""
    import torch

    try:
        ckpt = torch.load(default_checkpoint_path(), map_location="cpu", weights_only=True)
    except Exception:  # noqa: BLE001  arquivo que não é um checkpoint legível: contaminação não verificável
        return None
    texts = ckpt.get("train_texts") if isinstance(ckpt, dict) else None
    if texts is None:
        return None
    seen = {norm_term(t) for t in texts}
    hits = []
    for doc in docs:
        for start, end in split_sentences(doc.text):
            sentence = doc.text[start:end].strip()
            if norm_term(sentence) in seen:
                hits.append({"doc": doc.id, "sentence": sentence})
    return hits


def evaluate_system(name: str, docs, extract=None, model: str = "qwen3:8b", temperature: float = 0.0) -> dict:
    check_preconditions([name])
    extract = extract or default_extract
    per_doc, traps_hit = [], []
    tp = fp = fn = 0
    held = [0, 0, 0]
    lenient_preds, lenient_gold = [], []
    with system_environment(name):
        for doc in docs:
            preds = [tuple(p) for p in extract(doc.text, model)]
            strict = set_prf({strict_key(*g) for g in doc.triples}, {strict_key(*p) for p in preds})
            tp, fp, fn = tp + strict.tp, fp + strict.fp, fn + strict.fn
            if doc.heldout:
                held = [held[0] + strict.tp, held[1] + strict.fp, held[2] + strict.fn]
            lenient_preds += [(doc.id, p) for p in preds]
            lenient_gold += [(doc.id, g) for g in doc.triples]
            for p in preds:
                why = next((w for s, o, w in doc.traps if _same(p[0], s) and _same(p[2], o)), None)
                if why:
                    traps_hit.append({"doc": doc.id, "pred": list(p), "why": why})
            per_doc.append({"doc": doc.id, "strict": asdict(strict), "lenient": asdict(_lenient(doc.triples, preds)),
                            "predicted": [list(p) for p in preds]})
    total_strict = _prf(tp, fp, fn)
    by_doc_gold = {d.id: d.triples for d in docs}
    matched = sum(any(lenient_match(p, g) for g in by_doc_gold[d]) for d, p in lenient_preds)
    hit = sum(any(lenient_match(p, g) for dd, p in lenient_preds if dd == d) for d, g in lenient_gold)
    precision = matched / len(lenient_preds) if lenient_preds else 0.0
    recall = hit / len(lenient_gold) if lenient_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    total_lenient = PRF(precision, recall, f1, hit, len(lenient_preds) - matched, len(lenient_gold) - hit)
    result = {"system": name, "strict": asdict(total_strict), "heldout_strict": asdict(_prf(*held)),
              "lenient": asdict(total_lenient), "traps_hit": traps_hit, "per_doc": per_doc}
    if SYSTEMS[name]["relations"] == "pure":
        result["contamination"] = contamination(docs)
    return result


def _report(results: list[dict], gold_path, model) -> str:
    rows = ["| Sistema | P estrita | R estrita | F1 estrito | F1 estrito (held-out) | F1 tolerante | Armadilhas |",
            "|---|---|---|---|---|---|---|"]
    notes = []
    for r in results:
        s, le, h = r["strict"], r["lenient"], r.get("heldout_strict", {"f1": 0.0})
        rows.append(f"| {r['system']} | {s['precision']:.2f} | {s['recall']:.2f} | {s['f1']:.2f} | {h['f1']:.2f} "
                    f"| {le['f1']:.2f} | {len(r['traps_hit'])} |")
        if "contamination" in r:
            c = r["contamination"]
            notes.append(f"- {r['system']}: contaminação não verificável (checkpoint sem textos de treino)." if c is None
                         else f"- {r['system']}: {len(c)} frase(s) do gabarito estão no treino do PURE"
                              + (": " + "; ".join(x["sentence"] for x in c) if c else "."))
    return "\n".join([f"# {datetime.now():%Y-%m-%d}: avaliação de ponta a ponta", "",
                      f"Gabarito: `{gold_path}`. Modelo do LLM: `{model}`.", "", *rows, "", *notes, ""])


# Retomar só faz sentido se o que define o resultado não mudou.
RESUME_MUST_MATCH = ("gold_sha256", "model", "temperature", "llm_seed", "checkpoint_sha256")


def main(argv=None) -> Path:
    ap = argparse.ArgumentParser(description="Avaliação de ponta a ponta com casamento estrito.")
    ap.add_argument("--systems", nargs="+", default=list(SYSTEMS), choices=list(SYSTEMS))
    ap.add_argument("--gold", default=str(GOLD_SAMPLES))
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--runs-dir", default=str(project_root() / "runs"))
    ap.add_argument("--seed", type=int, default=EVAL_SEED, help="semente enviada ao Ollama")
    ap.add_argument("--resume", metavar="PASTA_DO_RUN", help="continua uma avaliação interrompida (runs/<pasta>)")
    args = ap.parse_args(argv)
    check_preconditions(args.systems)
    docs = load_gold(args.gold)
    metadata = {
        "commit": _commit(), "gold": str(args.gold), "gold_sha256": _sha256(args.gold), "model": args.model,
        "temperature": EVAL_TEMPERATURE, "llm_seed": args.seed, "systems": args.systems,
        "checkpoint": str(default_checkpoint_path()), "checkpoint_sha256": _sha256(default_checkpoint_path()),
    }
    results = []
    if args.resume:
        run = Path(args.resume)
        saved = json.loads((run / "results.json").read_text(encoding="utf-8"))
        for key in RESUME_MUST_MATCH:
            if saved["metadata"].get(key) != metadata[key]:
                raise ValueError(f"não dá para retomar {run}: '{key}' mudou "
                                 f"({saved['metadata'].get(key)!r} para {metadata[key]!r})")
        results = saved["results"]
        metadata = {**saved["metadata"], "systems": list(dict.fromkeys(saved["metadata"]["systems"] + args.systems))}
    else:
        stem = Path(args.runs_dir) / f"{datetime.now():%Y%m%d-%H%M%S}-e2e"
        run, k = stem, 2
        while run.exists():
            run, k = Path(f"{stem}-{k}"), k + 1
        run.mkdir(parents=True)
    done = {r["system"] for r in results}
    previous_seed = os.environ.get("OMAKER_LLM_SEED")
    os.environ["OMAKER_LLM_SEED"] = str(args.seed)
    try:
        for name in args.systems:  # grava depois de cada sistema: uma falha não perde os anteriores
            if name in done:
                print(f"{name}: já avaliado em {run.name}, pulando.")
                continue
            results.append(evaluate_system(name, docs, model=args.model, temperature=EVAL_TEMPERATURE))
            (run / "results.json").write_text(json.dumps({"metadata": metadata, "results": results},
                                                         ensure_ascii=False, indent=1), encoding="utf-8")
            (run / "report.md").write_text(_report(results, args.gold, args.model), encoding="utf-8")
    finally:
        if previous_seed is None:
            os.environ.pop("OMAKER_LLM_SEED", None)
        else:
            os.environ["OMAKER_LLM_SEED"] = previous_seed
    print((run / "report.md").read_text(encoding="utf-8"))
    print(f"Resultados em {run}")
    return run


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=project_root(), capture_output=True,
                              text=True, timeout=5).stdout.strip() or "desconhecido"
    except OSError:
        return "desconhecido"


if __name__ == "__main__":
    main()
