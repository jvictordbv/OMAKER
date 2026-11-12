import pytest

from omaker.relations import biored
from omaker.relations.data import RelationExample

TITLE = "Aspirin reduces stroke risk."
ABSTRACT = ("Aspirin prevented stroke in trials. Cisplatin caused nephrotoxicity and nausea. "
            "Glucose was measured in diabetes.")
TEXT = TITLE + " " + ABSTRACT


def _m(pmid, text, mention, etype, ids, start_at=0):
    s = TEXT.index(mention, start_at)
    return f"{pmid}\t{s}\t{s + len(mention)}\t{mention}\t{etype}\t{ids}"


def _doc(pmid="1"):
    a2 = TEXT.index("Aspirin", 1)
    lines = [
        f"{pmid}|t|{TITLE}",
        f"{pmid}|a|{ABSTRACT}",
        _m(pmid, TEXT, "Aspirin", "ChemicalEntity", "D001"),
        _m(pmid, TEXT, "stroke", "DiseaseOrPhenotypicFeature", "D020"),
        _m(pmid, TEXT, "Aspirin", "ChemicalEntity", "D001", a2),
        _m(pmid, TEXT, "stroke", "DiseaseOrPhenotypicFeature", "D020", a2),
        _m(pmid, TEXT, "Cisplatin", "ChemicalEntity", "D002"),
        _m(pmid, TEXT, "nephrotoxicity", "DiseaseOrPhenotypicFeature", "D030,D031"),
        _m(pmid, TEXT, "nausea", "DiseaseOrPhenotypicFeature", "D040"),
        _m(pmid, TEXT, "Glucose", "ChemicalEntity", "D003"),
        _m(pmid, TEXT, "diabetes", "DiseaseOrPhenotypicFeature", "D050"),
        f"{pmid}\tNegative_Correlation\tD020\tD001\tNovel",     # sem direção: a doença pode vir primeiro
        f"{pmid}\tPositive_Correlation\tD002\tD031\tNovel",     # casa com um dos ids da menção
        f"{pmid}\tAssociation\tD003\tD050\tNo",                 # tipo não mapeado: o par é descartado
    ]
    return "\n".join(lines) + "\n\n"


def test_parse_pubtator_reads_text_mentions_and_relations():
    (doc,) = biored.parse_pubtator(_doc("7"))
    assert doc.pmid == "7"
    assert doc.text == TEXT
    assert len(doc.mentions) == 9
    m = doc.mentions[5]
    assert TEXT[m.start:m.end] == "nephrotoxicity" and m.ids == ("D030", "D031")
    assert ("Negative_Correlation", "D020", "D001") in doc.relations


def test_parse_pubtator_rejects_offsets_that_do_not_match_the_text():
    bad = _doc().replace("\t0\t7\tAspirin", "\t1\t8\tAspirin", 1)
    with pytest.raises(ValueError, match="PMID 1"):
        biored.parse_pubtator(bad)


def _by_pair(examples):
    return {(e.text, e.sub_name, e.obj_name): e for e in examples}


def test_document_examples_maps_labels_per_sentence():
    (doc,) = biored.parse_pubtator(_doc())
    ex = _by_pair(biored.document_examples(doc))
    s1, s2, s3 = TITLE, "Aspirin prevented stroke in trials.", "Cisplatin caused nephrotoxicity and nausea."
    assert ex[(s1, "Aspirin", "stroke")].relation == "treats"       # Negative_Correlation
    assert ex[(s2, "Aspirin", "stroke")].relation == "treats"
    assert ex[(s3, "Cisplatin", "nephrotoxicity")].relation == "causes"   # Positive_Correlation
    assert ex[(s3, "Cisplatin", "nausea")].relation == "no_relation"
    assert not any(e.sub_name == "Glucose" for e in ex.values())   # Association: descartado
    assert len(ex) == 4


def test_document_examples_use_sentence_relative_spans_and_omaker_types():
    (doc,) = biored.parse_pubtator(_doc())
    for e in biored.document_examples(doc):
        assert isinstance(e, RelationExample)
        assert (e.sub_type, e.obj_type) == ("DRUG", "DISEASE")
        assert e.text[slice(*e.sub_span)] == e.sub_name
        assert e.text[slice(*e.obj_span)] == e.obj_name


def test_pair_split_across_sentences_gives_no_example():
    (doc,) = biored.parse_pubtator(_doc())
    assert not any(e.sub_name == "Aspirin" and e.obj_name == "nausea" for e in biored.document_examples(doc))


def test_load_biored_uses_official_parts(tmp_path):
    for part, pmid in (("Train", "1"), ("Dev", "2"), ("Test", "3")):
        (tmp_path / f"{part}.PubTator").write_text(_doc(pmid), encoding="utf-8")
    splits = biored.load_biored(tmp_path)
    assert len(splits.train) == len(splits.dev) == len(splits.test) == 4
    m = splits.manifest
    assert m["official_split"] is True and m["stratified"] is False
    assert m["mapping"] == {"Positive_Correlation": "causes", "Negative_Correlation": "treats"}
    assert m["counts"]["test"] == {"causes": 1, "no_relation": 1, "treats": 2}
    assert len(m["source_sha256"]) == 64


def test_load_biored_missing_file_says_how_to_get_it(tmp_path):
    with pytest.raises(FileNotFoundError, match="--download"):
        biored.load_biored(tmp_path)
