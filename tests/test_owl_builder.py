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


def test_run_reasoner_without_java_explains(monkeypatch):
    monkeypatch.setattr(owl_builder.shutil, "which", lambda _: None)
    monkeypatch.setattr(owl_builder, "sync_reasoner_hermit", _raise(AssertionError("não deveria rodar")))
    world, _ = owl_builder.new_world_ontology("http://t.org/x.owl")
    lines = []
    assert owl_builder.run_reasoner(world, log=lines.append) is ReasonerStatus.UNAVAILABLE
    assert any("Java não encontrado" in line for line in lines)


def test_run_reasoner_consistent(tmp_path, monkeypatch):
    java = tmp_path / "java.exe"
    java.write_bytes(b"")
    monkeypatch.setattr(owl_builder, "sync_reasoner_hermit", lambda *a, **k: None)
    world, _ = owl_builder.new_world_ontology("http://t.org/x.owl")
    assert owl_builder.run_reasoner(world, log=lambda m: None, java_exe=str(java)) is ReasonerStatus.CONSISTENT


def test_run_reasoner_inconsistent(tmp_path, monkeypatch):
    java = tmp_path / "java.exe"
    java.write_bytes(b"")
    err = owl_builder.OwlReadyInconsistentOntologyError("boom")
    monkeypatch.setattr(owl_builder, "sync_reasoner_hermit", _raise(err))
    world, _ = owl_builder.new_world_ontology("http://t.org/x.owl")
    assert owl_builder.run_reasoner(world, log=lambda m: None, java_exe=str(java)) is ReasonerStatus.INCONSISTENT


def _record_find_java(monkeypatch):
    """Replaces find_java (looked up at call time by HybridEngine) with a recorder returning None."""
    from core import java_locator

    recebidos = []

    def fake(protege_exe="", *a, **k):
        recebidos.append(protege_exe)
        return None

    monkeypatch.setattr(java_locator, "find_java", fake)
    return recebidos


def test_construir_reports_reasoner_unavailable(tmp_path, monkeypatch, sample_extraction):
    _no_java(monkeypatch)
    recebidos = _record_find_java(monkeypatch)
    tax, triples = sample_extraction
    logs = []
    result = HybridEngine.construir(tax, triples, "t", str(tmp_path), "http://t.org/", logs.append)
    assert os.path.exists(result.path)
    assert result.reasoner is ReasonerStatus.UNAVAILABLE
    assert result.relations_added == 3
    assert recebidos == [""]
    assert any("Java não encontrado" in line for line in logs)


def test_gerar_ontologia_passes_protege_exe_to_find_java(tmp_path, monkeypatch, sample_extraction):
    _no_java(monkeypatch)
    recebidos = _record_find_java(monkeypatch)
    monkeypatch.setattr(HybridEngine, "extrair", staticmethod(lambda *a, **k: sample_extraction))
    result = HybridEngine.gerar_ontologia("texto", "t", "", "m", 0.1, str(tmp_path), "http://t.org/",
                                          lambda m: None, protege_exe=r"X\Protege.exe")
    assert recebidos == [r"X\Protege.exe"]
    assert result.reasoner is ReasonerStatus.UNAVAILABLE


def test_atualizar_ontologia_passes_protege_exe_to_find_java(tmp_path, monkeypatch, sample_extraction):
    _no_java(monkeypatch)
    recebidos = _record_find_java(monkeypatch)
    tax, triples = sample_extraction
    monkeypatch.setattr(HybridEngine, "extrair", staticmethod(lambda *a, **k: (tax, triples)))
    first = HybridEngine.construir(tax, triples, "t", str(tmp_path), "http://t.org/", lambda m: None)
    recebidos.clear()
    result = HybridEngine.atualizar_ontologia(first.path, "texto", "", lambda m: None,
                                              protege_exe=r"X\Protege.exe")
    assert recebidos == [r"X\Protege.exe"]
    assert result.reasoner is ReasonerStatus.UNAVAILABLE


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
