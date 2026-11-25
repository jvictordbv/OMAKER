"""Biomedical NER: raw text -> typed entities with character offsets."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from omaker.config import ner_model
from omaker.domain.entities import Entity
from omaker.domain.labels import (
    BC5CDR_NER_MODEL_NAME,
    BC5CDR_NER_MODEL_REVISION,
    NER_MODEL_NAME,
    NER_MODEL_REVISION,
)
from omaker.domain.text import split_sentences
from omaker.ontology.alignment import build_label_index, norm_term

# Maps the NER model's labels (lower-cased) to OMAKER entity types.
# Labels not listed here are ignored. Check them against your NER model's config.
NER_LABEL_MAP = {
    "medication": "DRUG",
    "sign_symptom": "SYMPTOM",
    "disease_disorder": "DISEASE",
}
# id2label of judithrosell/BC5CDR_PubMedBERT_NER: B-/I-Chemical, B-/I-Disease, O.
BC5CDR_LABEL_MAP = {
    "chemical": "DRUG",
    "disease": "DISEASE",
}


@dataclass(frozen=True)
class NerSpec:
    name: str
    revision: str | None
    label_map: dict
    # BC5CDR does not tell symptoms from diseases: a disease named in the Symptom Ontology becomes SYMPTOM.
    symptoms_from_symp: bool = False


# Keys are the values of OMAKER_NER_MODEL (omaker.config.NER_MODELS).
NER_SPECS = {
    "d4data": NerSpec(NER_MODEL_NAME, NER_MODEL_REVISION, NER_LABEL_MAP),
    "bc5cdr": NerSpec(BC5CDR_NER_MODEL_NAME, BC5CDR_NER_MODEL_REVISION, BC5CDR_LABEL_MAP, symptoms_from_symp=True),
}


def ner_spec(model: str | None = None) -> NerSpec:
    """A key of NER_SPECS, a Hugging Face name or None (OMAKER_NER_MODEL). An unknown name is loaded
    without a pinned revision and with the d4data labels."""
    key = model or ner_model()
    if key in NER_SPECS:
        return NER_SPECS[key]
    return next((s for s in NER_SPECS.values() if s.name == key), NerSpec(key, None, NER_LABEL_MAP))


@lru_cache(maxsize=1)
def symptom_terms() -> frozenset[str]:
    """Normalized rdfs:label and exact synonyms of the bundled Symptom Ontology (omaker/resources/symp.owl)."""
    from omaker.ontology.builder import load_world_ontology
    from omaker.paths import package_resource

    _world, onto = load_world_ontology(str(package_resource("symp.owl")))
    return frozenset(build_label_index(onto, names=False))


def normalize_label(label: str) -> str:
    """Lower-cases a model label and strips only a leading B-/I- prefix."""
    return re.sub(r"^[bi]-", "", label.lower())


class BiomedicalNER:
    def __init__(self, model_name: str | None = None, min_score: float = 0.5, device: int | None = None):
        """model_name: "d4data", "bc5cdr", a Hugging Face name or None (OMAKER_NER_MODEL, read now)."""
        spec = ner_spec(model_name)

        import torch
        from transformers import pipeline

        if device is None:
            device = 0 if torch.cuda.is_available() else -1
        self.min_score = min_score
        self.label_map = spec.label_map
        self.symptoms = symptom_terms() if spec.symptoms_from_symp else None
        self.last_rejected = []  # (text, label, score) of detections that were ignored
        self.pipe = pipeline(
            "token-classification",
            model=spec.name,
            revision=spec.revision,
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
                etype = self.label_map.get(label)
                if etype is None or item["score"] < self.min_score:
                    self.last_rejected.append((sentence[item["start"]:item["end"]], item["entity_group"], float(item["score"])))
                    continue
                start, end = self._snap_to_word(sentence, item["start"], item["end"])
                mention = sentence[start:end]
                if etype == "DISEASE" and self.symptoms is not None and norm_term(mention) in self.symptoms:
                    etype = "SYMPTOM"
                entities.append(Entity(mention, s_start + start, s_start + end, etype, float(item["score"])))

        # Remove overlaps, keeping the highest-scoring entity.
        entities.sort(key=lambda e: -e.score)
        kept: list[Entity] = []
        for e in entities:
            if all(e.end <= k.start or e.start >= k.end for k in kept):
                kept.append(e)
        return sorted(kept, key=lambda e: e.start)
