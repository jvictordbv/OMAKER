import pytest
from owlready2 import Thing, World, locstr

from omaker.ontology.builder import add_equivalences, load_world_ontology


@pytest.fixture
def base_owl(tmp_path):
    """Ontologia mínima: Doenca (doença), Enfermidade (enfermidade), Carro (carro)."""
    world = World()
    onto = world.get_ontology("http://teste.org/base.owl")
    with onto:
        for name, label in [("Doenca", "doença"), ("Enfermidade", "enfermidade"), ("Carro", "carro")]:
            cls = type(name, (Thing,), {})
            cls.label = [locstr(label, lang="pt")]
    path = tmp_path / "base.owl"
    onto.save(file=str(path), format="rdfxml")
    return path


def _equivalents(path, a, b):
    _, onto = load_world_ontology(str(path))
    ca, cb = onto[a], onto[b]
    return cb in ca.equivalent_to or ca in cb.equivalent_to


def test_equivalence_written_to_copy(base_owl, tmp_path):
    before = base_owl.read_bytes()
    dest = tmp_path / "out" / "base_sinonimos.owl"
    report = add_equivalences(str(base_owl), {0: ["doença", "enfermidade"]}, str(dest), log=lambda _: None)
    assert report.added == 1
    assert report.groups_written == [["doença", "enfermidade"]]
    assert report.path == str(dest)
    assert _equivalents(dest, "Doenca", "Enfermidade")
    assert base_owl.read_bytes() == before


def test_group_with_one_match_is_skipped(base_owl, tmp_path):
    report = add_equivalences(str(base_owl), {0: ["carro", "automóvel"]}, str(tmp_path / "x.owl"), log=lambda _: None)
    assert report.added == 0
    assert report.not_found == ["automóvel"]
    assert report.groups_written == []


def test_match_ignores_case_and_underscores(base_owl, tmp_path):
    dest = tmp_path / "y.owl"
    report = add_equivalences(str(base_owl), {0: ["DOENÇA", "Enfermidade"]}, str(dest), log=lambda _: None)
    assert report.added == 1
    assert _equivalents(dest, "Doenca", "Enfermidade")
