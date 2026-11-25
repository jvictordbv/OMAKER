import os

from omaker.ontology import builder as owl_builder
from omaker.ontology.builder import ReasonerStatus
from omaker.pipeline.engine import HybridEngine


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
    from omaker.ontology import java as java_locator

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
    result = HybridEngine.gerar_ontologia("texto", "t", "m", 0.1, str(tmp_path), "http://t.org/",
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
    result = HybridEngine.atualizar_ontologia(first.path, "texto", lambda m: None,
                                              protege_exe=r"X\Protege.exe")
    assert recebidos == [r"X\Protege.exe"]
    assert result.reasoner is ReasonerStatus.UNAVAILABLE


def test_atualizar_returns_ontology_result(tmp_path, monkeypatch, sample_extraction):
    from omaker.pipeline.engine import OntologyResult

    tax, triples = sample_extraction
    monkeypatch.setattr(owl_builder, "run_reasoner", lambda *a, **k: ReasonerStatus.UNAVAILABLE)
    first = HybridEngine.construir(tax, triples, "t", str(tmp_path), "http://t.org/", lambda m: None)
    monkeypatch.setattr(HybridEngine, "extrair", staticmethod(lambda *a, **k: (tax, triples)))
    result = HybridEngine.atualizar_ontologia(first.path, "texto", lambda m: None)
    assert isinstance(result, OntologyResult)
    assert result.path == first.path
    assert result.reasoner is ReasonerStatus.UNAVAILABLE
    assert isinstance(result.relations_added, int)


EMPTY_TAX = {"classes": {}, "instances": {}, "disjoint": []}


def _new_onto(taxonomy=EMPTY_TAX, triples=()):
    _world, onto = owl_builder.new_world_ontology("http://t.org/nova.owl")
    owl_builder.populate(onto, taxonomy, list(triples), log=lambda m: None)
    return onto


# ---- ONT-06: estrutura básica da ontologia
def test_new_ontology_has_the_root_and_the_four_base_classes():
    onto = _new_onto()
    root = onto["BiomedicalEntity"]
    assert root is not None and owl_builder.Thing in root.is_a
    for base in ("Drug", "Symptom", "Disease", "Gene"):
        assert onto[base].is_a == [root], base


def test_new_ontology_has_the_three_object_properties_with_drug_domain_on_treats_and_prevents():
    onto = _new_onto()
    for rel in ("treats", "causes", "prevents"):
        assert issubclass(onto[rel], owl_builder.ObjectProperty), rel
    assert onto["treats"].domain == [onto["Drug"]]
    assert onto["prevents"].domain == [onto["Drug"]]
    assert onto["causes"].domain == []


def test_new_ontology_declares_the_base_classes_disjoint():
    onto = _new_onto()
    bases = {onto[b] for b in ("Drug", "Symptom", "Disease", "Gene")}
    assert [set(d.entities) for d in onto.disjoint_classes()] == [bases]


# ---- ONT-07: indivíduos
def test_individual_gets_a_safe_identifier_and_the_original_text_as_label():
    onto = _new_onto({"classes": {}, "instances": {"back pain": "Symptom"}, "disjoint": []})
    ind = onto["back_pain"]
    assert ind is not None and ind.label == ["back pain"] and onto["Symptom"] in ind.is_a


def test_individual_named_like_a_class_gets_the_ind_suffix():
    onto = _new_onto({"classes": {"Fever": "Symptom"}, "instances": {"Fever": "Fever"}, "disjoint": []})
    ind = onto["Fever_ind"]
    assert ind is not None and ind.label == ["Fever"] and ind.is_a == [onto["Fever"]]
    assert isinstance(onto["Fever"], owl_builder.owlready2.ThingClass)   # a classe continua sendo classe
