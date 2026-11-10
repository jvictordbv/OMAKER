"""Small text helpers shared by the NER and the pair generator."""
import re

# Split after . ! ? when followed by whitespace and an uppercase letter or digit.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_LAST_TOKEN = re.compile(r"(\S+)\.$")

# Abbreviations that end with a period but do not end a sentence ("Dr. Smith", "e.g. Aspirin", "Fig. 2").
# Single letters are left out on purpose: "Hepatitis B. Patients..." is a real sentence boundary.
ABBREVIATIONS = frozenset({
    "dr", "mr", "mrs", "ms", "prof", "st", "e.g", "i.e", "vs", "cf", "fig", "figs", "eq", "no", "approx", "ca",
})


def _ends_with_abbreviation(text: str, end: int) -> bool:
    m = _LAST_TOKEN.search(text, max(0, end - 24), end)  # short window: abbreviations are short
    return bool(m) and m.group(1).lstrip("([").lower() in ABBREVIATIONS


def split_sentences(text: str) -> list[tuple[int, int]]:
    """Returns (start, end) character offsets of each sentence."""
    spans, cursor = [], 0
    for m in _SENT_SPLIT.finditer(text):
        if _ends_with_abbreviation(text, m.start()):
            continue
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
