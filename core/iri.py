"""IRI absoluto e sem espacos para a ontologia gerada (OWL 2 exige IRI absoluto)."""
import re
from urllib.parse import urlparse

DEFAULT_URI_BASE = "http://www.mestrado.edu/ontologias/"

_REMOVIDOS = re.compile(r'[#?/\%"<>{}|^`]')


def normalize_base(uri_base: str) -> tuple[str, bool]:
    """Devolve (base valida terminada em '/', True se foi trocada pelo padrao)."""
    base = (uri_base or "").strip()
    partes = urlparse(base)
    if partes.scheme not in ("http", "https") or not partes.netloc:
        return DEFAULT_URI_BASE, True
    if re.search(r"\s", partes.path):
        return DEFAULT_URI_BASE, True
    if base.endswith("#"):
        base = base[:-1] + "/"
    elif not base.endswith("/"):
        base += "/"
    return base, False


def ontology_iri(uri_base: str, nome_arquivo: str) -> str:
    base, _ = normalize_base(uri_base)
    nome = _REMOVIDOS.sub("", re.sub(r"\s+", "_", nome_arquivo.strip()))
    return f"{base}{nome or 'ontologia'}.owl"
