"""Biomedical NER: raw text -> typed entities with character offsets."""
from __future__ import annotations

import re

from omaker.domain.entities import Entity
from omaker.domain.labels import NER_MODEL_NAME
from omaker.domain.text import split_sentences

# Maps the NER model's labels (lower-cased) to OMAKER entity types.
# Labels not listed here are ignored. Check them against your NER model's config.
NER_LABEL_MAP = {
    "medication": "DRUG",
    "sign_symptom": "SYMPTOM",
    "disease_disorder": "DISEASE",
}


def normalize_label(label: str) -> str:
    """Lower-cases a model label and strips only a leading B-/I- prefix."""
    return re.sub(r"^[bi]-", "", label.lower())


class BiomedicalNER:
    def __init__(self, model_name: str = NER_MODEL_NAME, min_score: float = 0.5, device: int | None = None):
        import torch
        from transformers import pipeline

        if device is None:
            device = 0 if torch.cuda.is_available() else -1
        self.min_score = min_score
        self.last_rejected = []  # (text, label, score) of detections that were ignored
        self.pipe = pipeline(
            "token-classification",
            model=model_name,
            aggregation_strategy="simple",
            device=device,
        )

    @staticmethod
    def _snap_to_word(text: str, start: int, end: int):
        """Expand a span to whole-word boundaries (NER sometimes cuts word pieces)."""
        while start > 0 and text[start - 1].isalnum():
            start -= 1
        while end < len(text) and text[end].isalnum():
            end += 1
        return start, end

    def extract(self, text: str) -> list[Entity]:
        """Runs the NER sentence by sentence (the model has a 512-token limit)
        and maps offsets back to the full text."""
        sentences = split_sentences(text)
        results = self.pipe([text[s:e] for s, e in sentences], batch_size=8)

        entities: list[Entity] = []
        self.last_rejected = []
        for (s_start, s_end), items in zip(sentences, results, strict=False):
            sentence = text[s_start:s_end]
            for item in items:
                label = normalize_label(item["entity_group"])
                etype = NER_LABEL_MAP.get(label)
                if etype is None or item["score"] < self.min_score:
                    self.last_rejected.append((sentence[item["start"]:item["end"]], item["entity_group"], float(item["score"])))
                    continue
                start, end = self._snap_to_word(sentence, item["start"], item["end"])
                entities.append(
                    Entity(sentence[start:end], s_start + start, s_start + end, etype, float(item["score"]))
                )

        # Remove overlaps, keeping the highest-scoring entity.
        entities.sort(key=lambda e: -e.score)
        kept: list[Entity] = []
        for e in entities:
            if all(e.end <= k.start or e.start >= k.end for k in kept):
                kept.append(e)
        return sorted(kept, key=lambda e: e.start)
