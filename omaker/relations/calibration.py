"""Calibração da confiança do PURE: ECE, temperature scaling e limite de confiança escolhido pela validação.

    uv run python -m omaker.relations.calibration --run runs/<pasta> [--device cpu]

A temperatura e o limite são ajustados só na validação; o teste é usado uma vez, para o relatório.
O resultado vai para runs/<pasta>/calibration.json e calibration.md, e para model.calibration.json
ao lado do checkpoint, que RelationExtractorPURE.load lê sozinho (o model.pt não é alterado).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from omaker.domain.labels import ID2REL, NO_RELATION
from omaker.evaluation.metrics import classification_prf

N_BINS = 10
THRESHOLD_GRID = [round(0.30 + 0.05 * i, 2) for i in range(14)]   # 0,30 a 0,95
CURRENT_THRESHOLD = 0.70   # o limite fixo usado antes da calibração (domain/labels.py)


# ------------------------------------------------------------------ medidas
def confidences(logits: torch.Tensor, temperature: float = 1.0):
    """(confiança, classe prevista) com softmax(logits / T). A temperatura não muda a classe prevista."""
    probs = torch.softmax(logits / temperature, dim=-1)
    return probs.max(dim=-1)


def ece(conf: torch.Tensor, correct: torch.Tensor, n_bins: int = N_BINS):
    """Expected Calibration Error e as faixas do diagrama de confiabilidade."""
    conf, correct = conf.float(), correct.float()
    edges = torch.linspace(0, 1, n_bins + 1)
    total, bins = 0.0, []
    for i in range(n_bins):
        lo, hi = float(edges[i]), float(edges[i + 1])
        mask = (conf > lo) & (conf <= hi) if i else (conf >= lo) & (conf <= hi)
        n = int(mask.sum())
        if n:
            c, a = float(conf[mask].mean()), float(correct[mask].mean())
            total += n / len(conf) * abs(c - a)
            bins.append({"lo": lo, "hi": hi, "n": n, "confidence": c, "accuracy": a})
    return total, bins


def fit_temperature(logits: torch.Tensor, labels: torch.Tensor, steps: int = 200) -> float:
    """Temperatura que minimiza a log-verossimilhança negativa (Guo et al., 2017)."""
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=steps)
    loss_fn = torch.nn.CrossEntropyLoss()
    logits, labels = logits.detach().float(), labels.long()

    def closure():
        opt.zero_grad()
        loss = loss_fn(logits / log_t.exp(), labels)
        loss.backward()
        return loss

    opt.step(closure)
    return float(log_t.detach().exp())


def apply_threshold(preds: list[str], confs: list[float], threshold: float) -> list[str]:
    """Relação com confiança abaixo do limite vira no_relation (como o pipeline faz)."""
    return [p if p == NO_RELATION or c >= threshold else NO_RELATION for p, c in zip(preds, confs, strict=True)]


def best_threshold(golds: list[str], preds: list[str], confs: list[float], grid=THRESHOLD_GRID):
    """(limite, micro-F1) com o maior micro-F1; no empate, o menor limite."""
    scored = [(classification_prf(golds, apply_threshold(preds, confs, t))["micro"].f1, -t) for t in grid]
    f1, neg_t = max(scored)
    return -neg_t, f1


# ------------------------------------------------------------- arquivo extra
def sidecar_path(checkpoint) -> Path:
    checkpoint = Path(checkpoint)
    return checkpoint.with_name(checkpoint.stem + ".calibration.json")


def read_calibration(checkpoint) -> dict | None:
    path = sidecar_path(checkpoint)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


# ---------------------------------------------------------------- execução
@torch.no_grad()
def collect_logits(model, pairs, batch_size: int = 32):
    """(logits [N, C], rótulos [N], válidos [N]) para pares (amostra, id do rótulo)."""
    model.eval()
    logits, labels, valid = [], [], []
    for i in range(0, len(pairs), batch_size):
        chunk = pairs[i:i + batch_size]
        out, ok = model([p[0] for p in chunk])
        logits.append(out.float().cpu())
        valid.append(ok.cpu())
        labels += [p[1] for p in chunk]
    return torch.cat(logits), torch.tensor(labels), torch.cat(valid)


def _summary(logits, labels, valid, temperature: float, threshold: float) -> dict:
    conf, pred = confidences(logits, temperature)
    conf = torch.where(valid, conf, torch.zeros_like(conf))
    pred_names = [ID2REL[p] if ok else NO_RELATION for p, ok in zip(pred.tolist(), valid.tolist(), strict=True)]
    golds = [ID2REL[g] for g in labels.tolist()]
    correct = torch.tensor([p == g for p, g in zip(pred_names, golds, strict=True)])
    value, bins = ece(conf, correct)
    prf = classification_prf(golds, apply_threshold(pred_names, conf.tolist(), threshold))
    return {"ece": value, "bins": bins, "threshold": threshold, "micro_f1": prf["micro"].f1,
            "precision": prf["micro"].precision, "recall": prf["micro"].recall}


def calibrate(run, device: str | None = None) -> dict:
    from omaker.relations.data import load_splits
    from omaker.relations.model import RelationExtractorPURE
    from omaker.relations.train import _samples

    run = Path(run)
    checkpoint = run / "model.pt"
    model = RelationExtractorPURE.load(str(checkpoint), device=device or "cpu")
    model.temperature = 1.0   # medir sempre a partir das confianças cruas
    splits = load_splits(run / "splits")
    dev = collect_logits(model, _samples(splits.dev))
    test = collect_logits(model, _samples(splits.test))

    d_logits, d_labels, d_valid = dev
    temperature = fit_temperature(d_logits[d_valid], d_labels[d_valid])
    d_conf, d_pred = confidences(d_logits, temperature)
    d_conf = torch.where(d_valid, d_conf, torch.zeros_like(d_conf))
    d_names = [ID2REL[p] if ok else NO_RELATION for p, ok in zip(d_pred.tolist(), d_valid.tolist(), strict=True)]
    threshold, dev_f1 = best_threshold([ID2REL[g] for g in d_labels.tolist()], d_names, d_conf.tolist())

    result = {
        "checkpoint": str(checkpoint), "temperature": temperature, "threshold": threshold,
        "dev": {"n": len(d_labels), "micro_f1_at_threshold": dev_f1,
                "before": _summary(*dev, 1.0, CURRENT_THRESHOLD),
                "after": _summary(*dev, temperature, threshold)},
        "test": {"n": len(test[1]),
                 "before": _summary(*test, 1.0, CURRENT_THRESHOLD),
                 "after": _summary(*test, temperature, threshold),
                 "no_threshold": _summary(*test, 1.0, 0.0)},
    }
    (run / "calibration.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    (run / "calibration.md").write_text(report(result), encoding="utf-8")
    sidecar_path(checkpoint).write_text(json.dumps({"temperature": temperature, "threshold": threshold}, indent=1),
                                        encoding="utf-8")
    return result


def report(r: dict) -> str:
    t = r["test"]
    rows = [f"| Sem limite | {t['no_threshold']['ece']:.3f} | 0.00 | {t['no_threshold']['precision']:.3f} "
            f"| {t['no_threshold']['recall']:.3f} | {t['no_threshold']['micro_f1']:.3f} |"]
    for label, key in (("Antes (T = 1, limite fixo)", "before"), ("Depois (calibrado)", "after")):
        s = t[key]
        rows.append(f"| {label} | {s['ece']:.3f} | {s['threshold']:.2f} | {s['precision']:.3f} | {s['recall']:.3f} "
                    f"| {s['micro_f1']:.3f} |")
    bins = ["| Faixa | Exemplos | Confiança média | Acerto |", "|---|---|---|---|"]
    for key, name in (("before", "antes"), ("after", "depois")):
        bins += [f"| {b['lo']:.1f} a {b['hi']:.1f} ({name}) | {b['n']} | {b['confidence']:.3f} | {b['accuracy']:.3f} |"
                 for b in t[key]["bins"]]
    return "\n".join([
        "# Calibração do PURE", "",
        f"Checkpoint: `{r['checkpoint']}`. Temperatura e limite ajustados na validação ({r['dev']['n']} exemplos); "
        f"teste com {t['n']} exemplos.", "",
        f"- Temperatura: **{r['temperature']:.3f}** (acima de 1: o modelo estava confiante demais).",
        f"- Limite de confiança escolhido pela validação: **{r['threshold']:.2f}** "
        f"(micro-F1 na validação {r['dev']['micro_f1_at_threshold']:.3f}).", "",
        "## Teste", "",
        "| Configuração | ECE | Limite | Precisão | Revocação | Micro-F1 |", "|---|---|---|---|---|---|", *rows, "",
        "## Diagrama de confiabilidade (teste)", "", *bins, "",
    ])


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="pasta do treino (runs/<pasta>) com model.pt e splits/")
    ap.add_argument("--device", default=None, help="cpu ou cuda (padrão: cpu)")
    args = ap.parse_args(argv)
    r = calibrate(args.run, args.device)
    print(report(r))
    return r


if __name__ == "__main__":
    main()
