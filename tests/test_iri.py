import re
from urllib.parse import urljoin

from core import owl_builder
from core.hybrid_engine import HybridEngine
from core.iri import ontology_iri
from core.owl_builder import ReasonerStatus


def test_empty_base_falls_back_to_default():
    assert ontology_iri("", "teste peste negra") == "http://www.mestrado.edu/ontologias/teste_peste_negra.owl"


def test_relative_base_falls_back():
    assert ontology_iri("#", "x") == "http://www.mestrado.edu/ontologias/x.owl"


def test_hash_base_becomes_slash():
    assert ontology_iri("http://a.org/o#", "x") == "http://a.org/o/x.owl"


def test_slash_base_kept():
    assert ontology_iri("http://a.org/o/", "x") == "http://a.org/o/x.owl"


def test_reserved_chars_removed_accents_kept():
    assert ontology_iri("http://a.org/", 'a#b?c ação') == "http://a.org/abc_ação.owl"


def test_construir_writes_absolute_iri(tmp_path, monkeypatch, sample_extraction):
    monkeypatch.setattr(owl_builder, "run_reasoner", lambda *a, **k: ReasonerStatus.UNAVAILABLE)
    tax, triples = sample_extraction
    logs = []
    result = HybridEngine.construir(tax, triples, "teste peste negra", str(tmp_path), "", logs.append)
    assert result.path.endswith("teste peste negra.owl")
    text = open(result.path, encoding="utf-8").read()
    print("\n".join(text.splitlines()[:10]))
    assert 'xml:base="http://www.mestrado.edu/ontologias/teste_peste_negra.owl"' in text
    base = re.search(r'xml:base="([^"]*)"', text).group(1)
    for about in re.findall(r'rdf:about="([^"]*)"', text):
        about = urljoin(base, about)  # rdf:about relativo resolve contra xml:base
        assert re.match(r"https?://[^/\s]+", about), about
        assert " " not in about and about.count("#") <= 1, about
    assert any("[IRI]" in m for m in logs)
