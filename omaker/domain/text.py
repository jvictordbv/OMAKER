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


# Palavras muito comuns em português e espanhol que quase não aparecem em texto médico em inglês.
# De fora ficam as que também são inglês ("a", "as", "do", "no", "e").
_NON_ENGLISH_MARKERS = frozenset({
    "de", "que", "não", "para", "com", "uma", "um", "os", "dos", "das", "da", "em", "por", "é", "são", "foi",
    "pelo", "pela", "ao", "aos", "mas", "ou", "seu", "sua",
    "el", "la", "los", "las", "del", "y", "con", "una", "es", "en", "su", "pero",
})
_WORD = re.compile(r"[^\W\d_]+")


def looks_non_english(text: str, min_words: int = 12, threshold: float = 0.08) -> bool:
    """Heurística: o texto parece estar em português ou espanhol? Os modelos do OMAKER esperam inglês.

    Textos curtos nunca são marcados (poucas palavras não bastam para decidir).
    """
    words = [w.lower() for w in _WORD.findall(text)]
    if len(words) < min_words:
        return False
    hits = sum(w in _NON_ENGLISH_MARKERS for w in words)
    return hits / len(words) >= threshold
