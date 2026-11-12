from omaker.evaluation import biored_gold as bg
from omaker.relations import biored

TITLE = "Cisplatin-induced nephrotoxicity is reduced by magnesium."
ABSTRACT = ("Cisplatin caused acute kidney injury and nausea in rats. Magnesium prevented the renal damage. "
            "Glucose levels were linked to diabetes. Patients with diabetes had hypertension.")
TEXT = TITLE + " " + ABSTRACT


def _m(mention, etype, ids, nth=0):
    start = -1
    for _ in range(nth + 1):
        start = TEXT.index(mention, start + 1)
    return f"1\t{start}\t{start + len(mention)}\t{mention}\t{etype}\t{ids}"


PUBTATOR = "\n".join([
    f"1|t|{TITLE}",
    f"1|a|{ABSTRACT}",
    _m("Cisplatin", "ChemicalEntity", "C1"),
    _m("nephrotoxicity", "DiseaseOrPhenotypicFeature", "D1"),
    _m("magnesium", "ChemicalEntity", "C2"),
    _m("Cisplatin", "ChemicalEntity", "C1", nth=1),
    _m("acute kidney injury", "DiseaseOrPhenotypicFeature", "D1"),
    _m("nausea", "DiseaseOrPhenotypicFeature", "D2"),
    _m("Magnesium", "ChemicalEntity", "C2"),
    _m("renal damage", "DiseaseOrPhenotypicFeature", "D1"),
    _m("Glucose", "ChemicalEntity", "C3"),
    _m("diabetes", "DiseaseOrPhenotypicFeature", "D3"),
    _m("diabetes", "DiseaseOrPhenotypicFeature", "D3", nth=1),
    _m("hypertension", "DiseaseOrPhenotypicFeature", "D4"),
    "1\tPositive_Correlation\tC1\tD1\tNovel",
    "1\tNegative_Correlation\tD1\tC2\tNovel",
    "1\tAssociation\tC3\tD3\tNo",
]) + "\n\n"


def _doc():
    (doc,) = bg.gold_docs(biored.parse_pubtator(PUBTATOR))
    return doc


def test_gold_doc_keeps_text_and_mapped_relations():
    doc = _doc()
    assert doc.id == "biored-1" and doc.text == TEXT and doc.heldout
    assert doc.gold == {("C1", "D1"): {"causes"}, ("C2", "D1"): {"treats", "prevents"}}
    assert ("C3", "D3") in doc.ignored


def test_any_surface_form_of_the_concept_matches():
    score = bg.score_doc(_doc(), [("cisplatin", "causes", "Acute kidney injury"),
                                  ("Magnesium", "prevents", "renal damage")])
    assert (score.tp, score.fp, score.fn) == (2, 0, 0)


def test_one_hit_per_gold_pair_even_with_several_names():
    score = bg.score_doc(_doc(), [("Cisplatin", "causes", "nephrotoxicity"),
                                  ("Cisplatin", "causes", "acute kidney injury")])
    assert (score.tp, score.fp, score.fn) == (1, 0, 1)


def test_wrong_relation_unrelated_pair_and_unknown_entity_are_false_positives():
    score = bg.score_doc(_doc(), [("Cisplatin", "treats", "nephrotoxicity"),   # relação errada
                                  ("Cisplatin", "causes", "nausea"),            # par sem relação anotada
                                  ("Cisplatin", "causes", "symptom")])          # entidade não anotada
    assert (score.tp, score.fp, score.fn) == (0, 3, 2)


def test_out_of_scope_predictions_are_ignored():
    score = bg.score_doc(_doc(), [("Glucose", "causes", "diabetes"),         # Association: rótulo incerto
                                  ("diabetes", "causes", "hypertension")])  # doença e doença: não anotado
    assert (score.tp, score.fp, score.fn, score.ignored) == (0, 0, 2, 2)


def test_reversed_direction_is_a_false_positive():
    score = bg.score_doc(_doc(), [("nephrotoxicity", "causes", "Cisplatin")])
    assert (score.tp, score.fp) == (0, 1)


def test_load_biored_gold_reads_the_test_part(tmp_path):
    (tmp_path / "Test.PubTator").write_text(PUBTATOR, encoding="utf-8")
    docs = bg.load_biored_gold(tmp_path, limit=None)
    assert [d.id for d in docs] == ["biored-1"]
