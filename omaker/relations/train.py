"""Treino do classificador de relações PURE, reproduzível por configuração.

    uv run python -m omaker.relations.train --config configs/pure_base.toml [--install]
    uv run python -m omaker.relations.train --resume runs/<pasta>   # continua um treino que caiu

Cada execução grava em runs/<data>-<nome>/: a configuração usada, a divisão train/dev/test (com
manifesto), as métricas (validação por época, teste uma única vez no fim, intervalo de 95%), um
relatório no formato de .conhecimento/06-experimentos/_template.md e o melhor checkpoint pela
validação. O checkpoint usado pela GUI só é substituído com --install.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import random
import shutil
import subprocess
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import get_linear_schedule_with_warmup

from omaker.domain.labels import ID2REL, REL2ID
from omaker.evaluation.metrics import bootstrap_ci, classification_prf
from omaker.paths import default_checkpoint_path, project_root
from omaker.relations.config import DEFAULT_DATA, TrainConfig, dump_config, load_config
from omaker.relations.data import (
    RelationExample,
    Splits,
    load_examples,
    load_splits,
    save_splits,
    sha256_of,
    split_examples,
)
from omaker.relations.model import find_span

DATA_PATH = Path(DEFAULT_DATA)


def set_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def to_sample(e: RelationExample):
    """Exemplo -> (amostra do modelo, id da relação). Usa os spans explícitos quando existem."""
    s = e.sub_span or find_span(e.text, e.sub_name)
    o = e.obj_span or (find_span(e.text, e.obj_name, avoid=s) if s else None)
    if s is None or o is None:
        return None
    return dict(text=e.text, sub_span=s, sub_type=e.sub_type, obj_span=o, obj_type=e.obj_type), REL2ID[e.relation]


def _samples(examples):
    return [c for c in (to_sample(e) for e in examples) if c is not None]


def predict_labels(model, pairs, batch_size):
    """(golds, preds) em nomes de relação; um par sem span válido conta como no_relation previsto."""
    model.eval()
    golds, preds = [], []
    with torch.no_grad():
        for i in range(0, len(pairs), batch_size):
            chunk = pairs[i:i + batch_size]
            logits, valid = model([p[0] for p in chunk])
            for p, v, (_, gold) in zip(logits.argmax(-1).tolist(), valid.tolist(), chunk, strict=True):
                golds.append(ID2REL[gold])
                preds.append(ID2REL[p] if v else "no_relation")
    return golds, preds


def _scores(golds, preds, seed):
    r = classification_prf(golds, preds)

    def micro_f1(g, p):
        return classification_prf(g, p)["micro"].f1

    return {
        "n": len(golds),
        "micro": asdict(r["micro"]),
        "macro_f1": r["macro_f1"],
        "per_class": {k: asdict(v) for k, v in r["per_class"].items()},
        "ci95": list(bootstrap_ci(golds, preds, micro_f1, n=1000, seed=seed)),
    }


def _from_root(path) -> Path:
    """Caminhos relativos da configuração são relativos à raiz do repositório, não à pasta corrente."""
    path = Path(path)
    return path if path.is_absolute() else project_root() / path


def _run_dir(config: TrainConfig) -> Path:
    base = _from_root(config.runs_dir)
    stem = f"{datetime.now():%Y%m%d-%H%M%S}-{config.name}"
    run, k = base / stem, 2
    while run.exists():
        run, k = base / f"{stem}-{k}", k + 1
    run.mkdir(parents=True)
    return run


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=project_root(), capture_output=True,
                              text=True, timeout=5).stdout.strip() or "desconhecido"
    except OSError:
        return "desconhecido"


def _report(config, metrics, manifest, device, command) -> str:
    t, d = metrics["test"], metrics["dev"]
    counts = {p: sum(c.values()) for p, c in manifest["counts"].items()}
    lines = [
        f"# {datetime.now():%Y-%m-%d}: {config.name}",
        "",
        "**Componente:** PURE  ",
        f"**Commit do clone:** `{_commit()}` · **Máquina:** {device}, {platform.processor() or platform.machine()}",
        "",
        "## Pergunta / hipótese",
        "",
        "(preencher)",
        "",
        "## Configuração",
        "",
        "| Parâmetro | Valor |",
        "|---|---|",
        f"| Modelo / encoder | {config.model_name} |",
        f"| Dados (treino / val / teste) | {counts['train']} / {counts['dev']} / {counts['test']} ({Path(config.data_path).name}, "
        f"sha256 {manifest['source_sha256'][:12]}, estratificada: {manifest['stratified']}) |",
        f"| Hiperparâmetros | épocas {config.epochs}, lr encoder {config.lr_encoder}, lr classificador "
        f"{config.lr_classifier}, weight decay {config.weight_decay}, batch {config.batch_size} |",
        f"| Seed | {config.seed} |",
        "",
        "Comando exato:",
        "",
        "```bash",
        command,
        "```",
        "",
        "## Resultados",
        "",
        "| Métrica | Valor |",
        "|---|---|",
        f"| Melhor época (validação) | {metrics['best_epoch']} |",
        f"| Validação: micro-F1 | {d['micro']['f1']:.3f} |",
        f"| Teste: micro-F1 (sem no_relation) | {t['micro']['f1']:.3f} (IC 95%: {t['ci95'][0]:.3f} a {t['ci95'][1]:.3f}) |",
        f"| Teste: precisão / revocação | {t['micro']['precision']:.3f} / {t['micro']['recall']:.3f} |",
        f"| Teste: macro-F1 | {t['macro_f1']:.3f} |",
        f"| Teste: exemplos | {t['n']} |",
        "",
        "Artefatos: esta pasta (`config.toml`, `splits/`, `metrics.json`, `model.pt`).",
        "",
        "## Conclusão",
        "",
        "(preencher)",
        "",
    ]
    return "\n".join(lines)


def _identity(batch):
    return batch


def _rng_state() -> dict:
    kind, keys, pos, has_gauss, cached = np.random.get_state()
    state = {"python": random.getstate(), "numpy": (kind, keys.tolist(), pos, has_gauss, cached),
             "torch": torch.get_rng_state()}
    if torch.cuda.is_available():
        state["cuda"] = torch.cuda.get_rng_state_all()
    return state


def _set_rng_state(state: dict) -> None:
    random.setstate(state["python"])
    kind, keys, pos, has_gauss, cached = state["numpy"]
    np.random.set_state((kind, np.array(keys, dtype=np.uint32), pos, has_gauss, cached))
    torch.set_rng_state(state["torch"])
    if "cuda" in state and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda"])


def _save_resume_point(run: Path, **state) -> None:
    """Grava last.pt de forma atômica: uma queda durante a gravação não estraga o ponto anterior."""
    tmp = run / "last.pt.part"
    torch.save({**state, "rng": _rng_state()}, tmp)
    tmp.replace(run / "last.pt")


def _load_splits_for(config: TrainConfig) -> Splits:
    if config.splits_dir:
        splits_dir = _from_root(config.splits_dir)
        if not splits_dir.exists():
            raise FileNotFoundError(f"splits_dir '{splits_dir}' não existe. Para o BioRED, gere com: "
                                    f"uv run python -m omaker.relations.biored --download")
        return load_splits(splits_dir)
    data_path = _from_root(config.data_path)
    return split_examples(load_examples(data_path), seed=config.seed, fractions=config.fractions,
                          source_sha256=sha256_of(data_path))


def run_training(config: TrainConfig, model_factory=None, device=None, install: bool = False,
                 command: str = "") -> Path:
    set_seeds(config.seed)
    splits = _load_splits_for(config)
    run = _run_dir(config)
    dump_config(config, run / "config.toml")
    save_splits(splits, run / "splits")
    command = command or f"uv run python -m omaker.relations.train  # config: {asdict(config)}"
    return _train(run, config, splits, model_factory, device, install, command, state=None)


def resume_training(run, model_factory=None, device=None, install: bool = False) -> Path:
    """Continua um treino interrompido a partir de runs/<pasta>/last.pt, com a mesma configuração e divisão."""
    run = Path(run)
    if (run / "metrics.json").exists():
        print(f"O treino em {run} já terminou; nada a retomar.")
        return run
    checkpoint = run / "last.pt"
    if not checkpoint.exists():
        raise FileNotFoundError(f"{checkpoint} não existe: o treino caiu antes do primeiro ponto de retomada. "
                                f"Rode o treino de novo.")
    config = load_config(run / "config.toml")
    splits = load_splits(run / "splits")
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    print(f"Retomando {run.name}: época {state['epoch']}, passo {state['step']}.")
    return _train(run, config, splits, model_factory, device, install, state["command"], state=state)


def _train(run: Path, config: TrainConfig, splits: Splits, model_factory, device, install: bool, command: str,
           state: dict | None) -> Path:
    train_set, dev_set, test_set = _samples(splits.train), _samples(splits.dev), _samples(splits.test)

    device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    if model_factory is None:
        from omaker.relations.model import RelationExtractorPURE as model_factory
    set_seeds(config.seed)
    model = model_factory(model_name=config.model_name, num_relations=len(REL2ID)).to(device)

    optimizer = torch.optim.AdamW([
        {"params": model.encoder.parameters(), "lr": config.lr_encoder, "weight_decay": config.weight_decay},
        {"params": model.classifier.parameters(), "lr": config.lr_classifier, "weight_decay": config.weight_decay},
    ])
    steps_per_epoch = math.ceil(len(train_set) / config.batch_size)
    total_steps = max(1, math.ceil(steps_per_epoch / config.grad_accum) * config.epochs)
    scheduler = get_linear_schedule_with_warmup(optimizer, int(0.1 * total_steps), total_steps)
    criterion = nn.CrossEntropyLoss()

    history, best_f1, best_epoch, best_dev = [], -1.0, 0, None
    start_epoch, skip, resumed_loss = 1, 0, 0.0
    if state is not None:
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        history, best_f1 = state["history"], state["best_f1"]
        best_epoch, best_dev = state["best_epoch"], state["best_dev"]
        start_epoch, skip, resumed_loss = state["epoch"], state["step"], state["total_loss"]
        _set_rng_state(state["rng"])

    def resume_point(epoch, step, total_loss):
        _save_resume_point(run, model=model.state_dict(), optimizer=optimizer.state_dict(),
                           scheduler=scheduler.state_dict(), epoch=epoch, step=step, total_loss=total_loss,
                           history=history, best_f1=best_f1, best_epoch=best_epoch, best_dev=best_dev,
                           command=command)

    for epoch in range(start_epoch, config.epochs + 1):
        # Ordem dos lotes fixa por época: ao retomar no meio da época, os mesmos lotes são refeitos e pulados.
        loader = DataLoader(train_set, batch_size=config.batch_size, shuffle=True, collate_fn=_identity,
                            generator=torch.Generator().manual_seed(config.seed * 1000 + epoch))
        model.train()
        first = epoch == start_epoch
        total_loss = resumed_loss if first else 0.0
        optimizer.zero_grad()
        for step, batch in enumerate(loader, start=1):
            if first and step <= skip:
                continue
            targets = torch.tensor([b[1] for b in batch], device=device)
            logits, valid = model([b[0] for b in batch])
            if not valid.any():
                continue
            loss = criterion(logits[valid], targets[valid])
            (loss / config.grad_accum).backward()
            total_loss += loss.item()
            if step % config.grad_accum == 0 or step == len(loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                if config.save_every_steps and step % config.save_every_steps == 0 and step < len(loader):
                    resume_point(epoch, step, total_loss)

        golds, preds = predict_labels(model, dev_set, config.batch_size)
        dev_f1 = classification_prf(golds, preds)["micro"].f1
        history.append({"epoch": epoch, "train_loss": total_loss / max(1, len(loader)), "dev_micro_f1": dev_f1})
        print(f"Epoch {epoch:02d}/{config.epochs} | loss {history[-1]['train_loss']:.4f} | dev micro-F1 {dev_f1:.3f}")
        if dev_f1 > best_f1:  # escolha pela VALIDAÇÃO; o teste não participa
            best_f1, best_epoch, best_dev = dev_f1, epoch, (golds, preds)
            model.save(str(run / "model.pt"), extra={"train_texts": sorted({e.text for e in splits.train})})
        resume_point(epoch + 1, 0, 0.0)

    # Teste: uma única vez, com o checkpoint da melhor época.
    model.load_state_dict(torch.load(run / "model.pt", map_location=device, weights_only=True)["state_dict"])
    test_golds, test_preds = predict_labels(model, test_set, config.batch_size)
    metrics = {
        "best_epoch": best_epoch,
        "dev": _scores(*best_dev, seed=config.seed),
        "test": _scores(test_golds, test_preds, seed=config.seed),
        "history": history,
        "split_manifest": splits.manifest,
    }
    (run / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    (run / "report.md").write_text(_report(config, metrics, splits.manifest, device.type, command), encoding="utf-8")

    if install:
        target = default_checkpoint_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(run / "model.pt", target)
        print(f"Checkpoint instalado para a GUI: {target}")
    (run / "last.pt").unlink(missing_ok=True)   # terminado: o ponto de retomada (grande) não serve mais
    t = metrics["test"]
    print(f"\nTeste: micro-F1 {t['micro']['f1']:.3f} (IC 95% {t['ci95'][0]:.3f} a {t['ci95'][1]:.3f}), "
          f"{t['n']} exemplos. Artefatos em {run}")
    return run


def main(argv=None) -> Path:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", help="arquivo TOML com a seção [train]")
    ap.add_argument("--install", action="store_true", help="copia o melhor checkpoint para o caminho usado pela GUI")
    ap.add_argument("--resume", metavar="PASTA_DO_RUN", help="continua um treino interrompido (runs/<pasta>)")
    args = ap.parse_args(argv)
    if args.resume:
        return resume_training(args.resume, install=args.install)
    config = load_config(args.config) if args.config else TrainConfig()
    command = "uv run python -m omaker.relations.train" + (f" --config {args.config}" if args.config else "") \
        + (" --install" if args.install else "")
    return run_training(config, install=args.install, command=command)


if __name__ == "__main__":
    main()
