"""PURE-style relation extractor with typed entity markers.

One code path (`_encode`) is used for training, evaluation and inference, so the
three can no longer diverge.
"""
from __future__ import annotations

from typing import Optional, Sequence

import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer

from core.labels import (
    ENTITY_TYPES,
    ID2REL,
    MODEL_NAME,
    NO_RELATION,
    REL2ID,
    marker_tokens,
)

MAX_LENGTH = 256


def find_span(text: str, name: str, avoid: Optional[tuple] = None) -> Optional[tuple]:
    """Case-insensitive search for `name` in `text`.

    Returns the first occurrence that does not overlap `avoid`, or None.
    Prefer spans coming from the NER over this function whenever possible.
    """
    hay, needle = text.lower(), name.lower()
    start = hay.find(needle)
    while start != -1:
        span = (start, start + len(name))
        if avoid is None or span[1] <= avoid[0] or span[0] >= avoid[1]:
            return span
        start = hay.find(needle, start + 1)
    return None


class RelationExtractorPURE(nn.Module):
    """Relation classifier: encoder + [h_subj_marker ; h_obj_marker] -> MLP."""

    def __init__(self, model_name: str = MODEL_NAME, num_relations: int = len(REL2ID), dropout: float = 0.1):
        super().__init__()
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.encoder = AutoModel.from_pretrained(model_name)

        self.tokenizer.add_special_tokens({"additional_special_tokens": marker_tokens()})
        self.encoder.resize_token_embeddings(len(self.tokenizer))

        hidden = self.encoder.config.hidden_size
        self.classifier = nn.Sequential(
            nn.Linear(hidden * 2, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, num_relations),
        )

    # ------------------------------------------------------------------ input
    def mark_text(self, text: str, sub_span: tuple, sub_type: str, obj_span: tuple, obj_type: str) -> str:
        """Insert typed markers around subject and object.

        "<S:DRUG> Paracetamol </S:DRUG> treats <O:SYMPTOM> fever </O:SYMPTOM>."
        """
        sub_type, obj_type = sub_type.upper(), obj_type.upper()
        for t in (sub_type, obj_type):
            if t not in ENTITY_TYPES:
                raise ValueError(f"Unknown entity type '{t}'. Valid: {ENTITY_TYPES}")
        (s0, s1), (o0, o1) = sub_span, obj_span
        if not (s1 <= o0 or o1 <= s0):
            raise ValueError("Subject and object spans overlap.")

        # (position, order, token): closing markers sort before opening ones at the same position.
        events = [
            (s0, 1, f"<S:{sub_type}> "), (s1, 0, f" </S:{sub_type}>"),
            (o0, 1, f"<O:{obj_type}> "), (o1, 0, f" </O:{obj_type}>"),
        ]
        events.sort(key=lambda e: (e[0], e[1]))
        out, cursor = [], 0
        for pos, _, token in events:
            out.append(text[cursor:pos])
            out.append(token)
            cursor = pos
        out.append(text[cursor:])
        return "".join(out)

    # --------------------------------------------------------------- encoding
    def _encode(self, samples: Sequence[dict]):
        """samples: dicts with text, sub_span, sub_type, obj_span, obj_type.

        Returns (logits [B, C], valid [B] bool). A sample is invalid when a marker
        was truncated away (sentence too long); its logits must be ignored.
        """
        device = next(self.parameters()).device
        marked = [
            self.mark_text(s["text"], s["sub_span"], s["sub_type"], s["obj_span"], s["obj_type"])
            for s in samples
        ]
        enc = self.tokenizer(
            marked, return_tensors="pt", padding=True, truncation=True, max_length=MAX_LENGTH
        ).to(device)
        hidden = self.encoder(**enc).last_hidden_state  # [B, T, H]

        s_ids = [self.tokenizer.convert_tokens_to_ids(f"<S:{s['sub_type'].upper()}>") for s in samples]
        o_ids = [self.tokenizer.convert_tokens_to_ids(f"<O:{s['obj_type'].upper()}>") for s in samples]

        rows = torch.arange(len(samples), device=device)
        s_idx, o_idx, valid = [], [], []
        for i in range(len(samples)):
            ids = enc["input_ids"][i]
            s_pos = (ids == s_ids[i]).nonzero(as_tuple=True)[0]
            o_pos = (ids == o_ids[i]).nonzero(as_tuple=True)[0]
            ok = len(s_pos) > 0 and len(o_pos) > 0
            valid.append(ok)
            s_idx.append(int(s_pos[0]) if ok else 0)
            o_idx.append(int(o_pos[0]) if ok else 0)

        s_idx = torch.tensor(s_idx, device=device)
        o_idx = torch.tensor(o_idx, device=device)
        pair = torch.cat([hidden[rows, s_idx], hidden[rows, o_idx]], dim=-1)
        logits = self.classifier(pair)
        return logits, torch.tensor(valid, device=device)

    def forward(self, samples: Sequence[dict]):
        return self._encode(samples)

    # -------------------------------------------------------------- inference
    @torch.no_grad()
    def predict(self, samples: Sequence[dict], batch_size: int = 16):
        """Returns a list of (relation_name, confidence), one per sample.

        Always runs in eval mode (dropout off) and restores the previous mode.
        """
        was_training = self.training
        self.eval()
        results = []
        try:
            for i in range(0, len(samples), batch_size):
                chunk = samples[i : i + batch_size]
                logits, valid = self._encode(chunk)
                probs = torch.softmax(logits, dim=-1)
                conf, pred = probs.max(dim=-1)
                for c, p, ok in zip(conf.tolist(), pred.tolist(), valid.tolist()):
                    results.append((ID2REL[p], c) if ok else (NO_RELATION, 0.0))
        finally:
            self.train(was_training)
        return results

    def extract_relation_triple(self, text, sub_name, sub_type, obj_name, obj_type):
        """Convenience wrapper for one pair given by names. Returns (triple, confidence)."""
        s = find_span(text, sub_name)
        o = find_span(text, obj_name, avoid=s) if s else None
        if s is None or o is None:
            print(f"Warning: '{sub_name}' or '{obj_name}' not found in text.")
            return None, 0.0
        sample = dict(text=text, sub_span=s, sub_type=sub_type, obj_span=o, obj_type=obj_type)
        (relation, conf), = self.predict([sample])
        return (sub_name, relation, obj_name), conf

    # ------------------------------------------------------------ persistence
    def save(self, path: str, extra: Optional[dict] = None):
        torch.save(
            {
                "state_dict": self.state_dict(),
                "model_name": self.model_name,
                "rel2id": REL2ID,
                "entity_types": ENTITY_TYPES,
                **(extra or {}),
            },
            path,
        )

    @classmethod
    def load(cls, path: str, device: Optional[str] = None) -> "RelationExtractorPURE":
        """Loads a checkpoint written by `save`. Raises if the file is missing or incompatible."""
        ckpt = torch.load(path, map_location=device or "cpu")
        if ckpt.get("rel2id") != REL2ID or tuple(ckpt.get("entity_types", ())) != tuple(ENTITY_TYPES):
            raise ValueError("Checkpoint labels/markers differ from core/labels.py. Retrain the model.")
        model = cls(model_name=ckpt["model_name"], num_relations=len(REL2ID))
        model.load_state_dict(ckpt["state_dict"])
        model.to(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        model.eval()
        return model


if __name__ == "__main__":
    # Smoke test with an untrained head: only checks that the plumbing runs.
    model = RelationExtractorPURE()
    triple, conf = model.extract_relation_triple(
        "Paracetamol treats fever quickly in adult patients.", "Paracetamol", "DRUG", "fever", "SYMPTOM"
    )
    print(triple, f"{conf:.3f}")