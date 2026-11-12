import shutil

import pytest
from owlready2 import Thing, World, locstr

from omaker import paths
from omaker.ontology.alignment import OMAKER_NAMESPACE, build_label_index, is_external
from omaker.ontology.builder import load_world_ontology, new_world_ontology, populate

OBO = "http://purl.obolibrary.org/obo/"
SYMPTOM, NAUSEA, FEVER, BACKACHE = (OBO + i for i in ("SYMP_0000462", "SYMP_0000458", "SYMP_0000613", "SYMP_0000006"))


@pytest.fixture
def symp(tmp_path):
    """Cópia da symp.owl (nunca o recurso do pacote)."""
    dest = tmp_path / "symp.owl"
    shutil.copy(paths.package_resource("symp.owl"), dest)
    return load_world_ontology(str(dest))


def _tax(instances):
    return {"classes": {}, "instances": instances, "disjoint": []}


def _ind(onto, label):
    return next(i for i in onto.individuals() if label in i.label)


def test_label_index_has_labels_and_synonyms(symp):
    _world, onto = symp
    index = build_label_index(onto)
    assert index["nausea"].iri == NAUSEA
    assert index["symptom"].iri == SYMPTOM
    assert index["back pain"].iri == BACKACHE          # oboInOwl:hasExactSynonym de "backache"
    assert is_external(onto)


def test_symp_update_reuses_symptom_and_has_no_parallel_classes(symp):
    world, onto = symp
    populate(onto, _tax({"aspirin": "Drug", "fever": "Symptom"}), [], log=lambda _: None)
    assert onto.search_one(iri="http://purl.obolibrary.org/obo/symp.owl#Drug") is None
    assert onto.search_one(iri="http://purl.obolibrary.org/obo/symp.owl#Symptom") is None
    drug_cls = _ind(onto, "aspirin").is_a[0]
    assert drug_cls.iri.startswith(OMAKER_NAMESPACE)
    assert world[SYMPTOM] in _ind(onto, "fever").is_a[0].ancestors()


def test_reused_class_not_in_alldisjoint(symp):
    world, onto = symp
    populate(onto, _tax({"aspirin": "Drug", "fever": "Symptom"}), [], log=lambda _: None)
    for group in onto.disjoint_classes():
        assert world[SYMPTOM] not in group.entities


def test_second_update_is_idempotent(symp):
    _world, onto = symp
    tax = _tax({"aspirin": "Drug", "fever": "Symptom"})
    populate(onto, tax, [], log=lambda _: None)
    counts = (len([c for c in onto.classes() if c.iri.startswith(OMAKER_NAMESPACE)]), len(list(onto.individuals())))
    populate(onto, tax, [], log=lambda _: None)
    assert counts == (len([c for c in onto.classes() if c.iri.startswith(OMAKER_NAMESPACE)]),
                      len(list(onto.individuals())))


def test_unrelated_external_ontology_gets_omaker_bases(tmp_path):
    world = World()
    onto = world.get_ontology("http://teste.org/carros.owl")
    with onto:
        carro = type("Carro", (Thing,), {})
        carro.label = [locstr("carro", lang="pt")]
    populate(onto, _tax({"aspirin": "Drug"}), [], log=lambda _: None)
    for name in ("Drug", "Disease", "Symptom", "BiomedicalEntity"):
        cls = onto.search_one(iri=OMAKER_NAMESPACE + name)
        assert cls is not None, name
    assert carro.is_a == [Thing]


def test_new_ontology_is_not_external():
    _world, onto = new_world_ontology("http://www.mestrado.edu/ontologias/nova.owl")
    assert not is_external(onto)


def test_instance_typed_by_label(symp):
    world, onto = symp
    populate(onto, _tax({"nausea": "Symptom"}), [], log=lambda _: None)
    assert world[NAUSEA] in _ind(onto, "nausea").is_a


def test_instance_typed_by_exact_synonym(symp):
    world, onto = symp
    populate(onto, _tax({"back pain": "Symptom"}), [], log=lambda _: None)
    assert world[BACKACHE] in _ind(onto, "back pain").is_a


def test_match_outside_entity_branch_is_ignored(symp):
    world, onto = symp
    populate(onto, _tax({"nausea": "Drug"}), [], log=lambda _: None)
    cls = _ind(onto, "nausea").is_a[0]
    assert cls.iri == OMAKER_NAMESPACE + "Drug"
    assert world[NAUSEA] not in _ind(onto, "nausea").is_a


def test_new_ontology_unchanged():
    _world, onto = new_world_ontology("http://www.mestrado.edu/ontologias/nova.owl")
    logs = []
    populate(onto, _tax({"nausea": "Symptom", "aspirin": "Drug"}), [], log=logs.append)
    assert not any("[ALIGN]" in line for line in logs)
    assert _ind(onto, "nausea").is_a[0].name == "Symptom"
