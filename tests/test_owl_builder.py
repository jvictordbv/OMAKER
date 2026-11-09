import os

from core import owl_builder
from core.hybrid_engine import HybridEngine
from core.owl_builder import ReasonerStatus


def _raise(exc):
    def fn(*args, **kwargs):
        raise exc
    return fn


def _no_java(monkeypatch):
    monkeypatch.setattr(owl_builder.shutil, "which", lambda _: None)
    monkeypatch.setattr(owl_builder, "sync_reasoner_hermit", _raise(FileNotFoundError("java")))


def test_run_reasoner_unavailable_without_java(monkeypatch):
    _no_java(monkeypatch)
    world, _ = owl_builder.new_world_ontology("http://t.org/x.owl")
    assert owl_builder.run_reasoner(world, log=lambda m: None) is ReasonerStatus.UNAVAILABLE


def test_run_reasoner_consistent(monkeypatch):
    monkeypatch.setattr(owl_builder, "sync_reasoner_hermit", lambda *a, **k: None)
    world, _ = owl_builder.new_world_ontology("http://t.org/x.owl")
    assert owl_builder.run_reasoner(world, log=lambda m: None) is ReasonerStatus.CONSISTENT


def test_run_reasoner_inconsistent(monkeypatch):
    err = owl_builder.OwlReadyInconsistentOntologyError("boom")
    monkeypatch.setattr(owl_builder, "sync_reasoner_hermit", _raise(err))
    world, _ = owl_builder.new_world_ontology("http://t.org/x.owl")
    assert owl_builder.run_reasoner(world, log=lambda m: None) is ReasonerStatus.INCONSISTENT


def test_construir_reports_reasoner_unavailable(tmp_path, monkeypatch, sample_extraction):
    _no_java(monkeypatch)
    tax, triples = sample_extraction
    result = HybridEngine.construir(tax, triples, "t", str(tmp_path), "http://t.org/", lambda m: None)
    assert os.path.exists(result.path)
    assert result.reasoner is ReasonerStatus.UNAVAILABLE
    assert result.relations_added == 3


def test_atualizar_returns_ontology_result(tmp_path, monkeypatch, sample_extraction):
    from core.hybrid_engine import OntologyResult

    tax, triples = sample_extraction
    monkeypatch.setattr(owl_builder, "run_reasoner", lambda *a, **k: ReasonerStatus.UNAVAILABLE)
    first = HybridEngine.construir(tax, triples, "t", str(tmp_path), "http://t.org/", lambda m: None)
    monkeypatch.setattr(HybridEngine, "extrair", staticmethod(lambda *a, **k: (tax, triples)))
    result = HybridEngine.atualizar_ontologia(first.path, "texto", "", lambda m: None)
    assert isinstance(result, OntologyResult)
    assert result.path == first.path
    assert result.reasoner is ReasonerStatus.UNAVAILABLE
    assert isinstance(result.relations_added, int)
