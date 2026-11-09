"""Small text helpers shared by the NER and the pair generator."""
import re
from typing import List, Tuple

# Split after . ! ? when followed by whitespace and an uppercase letter or digit.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def split_sentences(text: str) -> List[Tuple[int, int]]:
    """Returns (start, end) character offsets of each sentence."""
    spans, cursor = [], 0
    for m in _SENT_SPLIT.finditer(text):
        spans.append((cursor, m.start()))
        cursor = m.end()
    spans.append((cursor, len(text)))
    return [(s, e) for s, e in spans if text[s:e].strip()]


def to_identifier(name: str, capitalize: bool = False) -> str:
    """Makes a string safe to use as an OWL entity name."""
    ident = re.sub(r"[^\w]+", "_", name.strip()).strip("_") or "Unnamed"
    if ident[0].isdigit():
        ident = "_" + ident
    return ident[0].upper() + ident[1:] if capitalize else ident