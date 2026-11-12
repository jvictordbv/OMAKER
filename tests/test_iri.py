import re
from urllib.parse import urljoin

from omaker.ontology import builder as owl_builder
from omaker.ontology.builder import ReasonerStatus
from omaker.ontology.iri import ontology_iri
from omaker.pipeline.engine import HybridEngine


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


def test_base_with_whitespace_falls_back():
    assert ontology_iri("http://a.org/meu dir/", "x") == "http://www.mestrado.edu/ontologias/x.owl"


def test_name_only_reserved_chars():
    assert ontology_iri("http://a.org/", "#?/") == "http://a.org/ontologia.owl"


def test_construir_writes_absolute_iri(tmp_path, monkeypatch, sample_extraction):
    monkeypatch.setattr(owl_builder, "run_reasoner", lambda *a, **k: ReasonerStatus.UNAVAILABLE)
    tax, triples = sample_extraction
    logs = []
    result = HybridEngine.construir(tax, triples, "teste peste negra", str(tmp_path), "", logs.append)
    assert result.path.endswith("teste peste negra.owl")
    text = open(result.path, encoding="utf-8").read()
    assert 'xml:base="http://www.mestrado.edu/ontologias/teste_peste_negra.owl"' in text
    base = re.search(r'xml:base="([^"]*)"', text).group(1)
    for about in re.findall(r'rdf:about="([^"]*)"', text):
        about = urljoin(base, about)  # rdf:about relativo resolve contra xml:base
        assert re.match(r"https?://[^/\s]+", about), about
        assert " " not in about and about.count("#") <= 1, about
    assert any("[IRI]" in m for m in logs)
