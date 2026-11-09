"""End-to-end fine-tuning of the PURE relation extractor.

Run from the project root:  python -m core.train
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import torch
import torch.nn as nn
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader
from transformers import get_linear_schedule_with_warmup

from core.labels import ID2REL, MODEL_NAME, REL2ID
from core.paths import default_checkpoint_path
from core.relation_extractor import RelationExtractorPURE, find_span

DATA_PATH = Path(__file__).parent / "train_relations.json"


def to_sample(item: dict):
    """Dataset row -> (model sample, label id). Uses explicit spans when provided."""
    text = item["text"]
    s = tuple(item["sub_span"]) if "sub_span" in item else find_span(text, item["sub_name"])
    o = tuple(item["obj_span"]) if "obj_span" in item else (find_span(text, item["obj_name"], avoid=s) if s else None)
    if s is None or o is None:
        return None
    sample = dict(text=text, sub_span=s, sub_type=item["sub_type"], obj_span=o, obj_type=item["obj_type"])
    return sample, REL2ID[item["relation"]]


def evaluate(model, pairs, batch_size):
    model.eval()
    preds, golds = [], []
    with torch.no_grad():
        for i in range(0, len(pairs), batch_size):
            chunk = pairs[i : i + batch_size]
            logits, valid = model([p[0] for p in chunk])
            pred = logits.argmax(-1).tolist()
            for p, v, (_, gold) in zip(pred, valid.tolist(), chunk, strict=False):
                if v:
                    preds.append(p)
                    golds.append(gold)
    return golds, preds


def train_omaker_pure(
    data_path: Path = DATA_PATH,
    epochs: int = 15,
    lr_encoder: float = 2e-5,
    lr_classifier: float = 1e-3,
    weight_decay: float = 0.01,
    batch_size: int = 8,
    grad_accum: int = 1,
    val_fraction: float = 0.25,
    seed: int = 42,
    save_path: str | None = None,
):
    save_path = str(save_path or default_checkpoint_path())
    random.seed(seed)
    torch.manual_seed(seed)

    if not Path(data_path).exists():
        print(f"Dataset not found: {data_path}")
        return
    rows = json.loads(Path(data_path).read_text(encoding="utf-8"))
    converted = [c for c in (to_sample(r) for r in rows) if c is not None]
    print(f"Loaded {len(converted)}/{len(rows)} usable samples from {data_path}")

    labels = [c[1] for c in converted]
    train_set, val_set = train_test_split(
        converted, test_size=val_fraction, random_state=seed, stratify=labels
    )
    print(f"Train: {len(train_set)} | Validation: {len(val_set)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    model = RelationExtractorPURE(model_name=MODEL_NAME, num_relations=len(REL2ID)).to(device)

    optimizer = torch.optim.AdamW(
        [
            {"params": model.encoder.parameters(), "lr": lr_encoder, "weight_decay": weight_decay},
            {"params": model.classifier.parameters(), "lr": lr_classifier, "weight_decay": weight_decay},
        ]
    )
    loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, collate_fn=lambda b: b)
    total_steps = max(1, math.ceil(len(loader) / grad_accum) * epochs)
    scheduler = get_linear_schedule_with_warmup(optimizer, int(0.1 * total_steps), total_steps)
    criterion = nn.CrossEntropyLoss()

    best_f1 = -1.0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        optimizer.zero_grad()

        for step, batch in enumerate(loader, start=1):
            samples = [b[0] for b in batch]
            targets = torch.tensor([b[1] for b in batch], device=device)
            logits, valid = model(samples)
            if not valid.any():
                continue
            loss = criterion(logits[valid], targets[valid])
            (loss / grad_accum).backward()
            total_loss += loss.item()

            if step % grad_accum == 0 or step == len(loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

        golds, preds = evaluate(model, val_set, batch_size)
        val_f1 = f1_score(golds, preds, average="macro", zero_division=0) if golds else 0.0
        print(f"Epoch {epoch:02d}/{epochs} | train loss {total_loss / max(1, len(loader)):.4f} | val macro-F1 {val_f1 * 100:.2f}%")

        if val_f1 > best_f1:  # best model chosen on VALIDATION, not on training data
            best_f1 = val_f1
            model.save(save_path)
            best_report = (golds, preds)

    golds, preds = best_report
    print(f"\nBest val macro-F1: {best_f1 * 100:.2f}%  -> saved to '{save_path}'")
    names = [ID2REL[i] for i in sorted(ID2REL)]
    print(classification_report(golds, preds, labels=sorted(ID2REL), target_names=names, zero_division=0))


if __name__ == "__main__":
    train_omaker_pure()
