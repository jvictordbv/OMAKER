"""Candidate pair generation: entities in the same sentence, filtered by type."""
from __future__ import annotations

from collections.abc import Iterable

from omaker.domain.labels import ALLOWED_TYPE_PAIRS
from omaker.domain.text import split_sentences
from omaker.nlp.ner import Entity


def generate_pairs(text: str, entities: Iterable[Entity], allowed=ALLOWED_TYPE_PAIRS) -> list[dict]:
    """Returns sample dicts ready for RelationExtractorPURE.predict.

    Each sample uses the *sentence* as text and spans relative to it, so the
    model never sees more than one sentence and markers are never truncated.
    """
    entities = sorted(entities, key=lambda e: e.start)
    samples = []
    for s_start, s_end in split_sentences(text):
        inside = [e for e in entities if e.start >= s_start and e.end <= s_end]
        sentence = text[s_start:s_end]
        for a in inside:
            for b in inside:
                if a is b or (a.type, b.type) not in allowed:
                    continue
                samples.append(
                    {
                        "text": sentence,
                        "sub_name": a.text,
                        "sub_type": a.type,
                        "sub_span": (a.start - s_start, a.end - s_start),
                        "obj_name": b.text,
                        "obj_type": b.type,
                        "obj_span": (b.start - s_start, b.end - s_start),
                    }
                )
    return samples
