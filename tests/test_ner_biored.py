import pytest

from omaker.evaluation import ner_biored as nb
from omaker.relations.biored import parse_pubtator
from tests.test_biored_gold import PUBTATOR, TEXT


@pytest.fixture
def docs():
    return parse_pubtator(PUBTATOR)


def _span(word, nth=0):
    start = -1
    for _ in range(nth + 1):
        start = TEXT.index(word, start + 1)
    return start, start + len(word)


def test_gold_has_only_chemicals_and_diseases(docs):
    gold = nb.gold_mentions(docs)
    assert {t for *_, t in gold} == {"Chemical", "Disease"}
    assert ("1", *_span("Cisplatin"), "Chemical") in gold


def test_exact_span_match_with_per_type_scores(docs):
    gold = nb.gold_mentions(docs)

    def extract(_text):
        return [(*_span("Cisplatin"), "Chemical"),            # acerto
                (*_span("acute kidney injury"), "Chemical"),  # span certo, tipo errado: conta no total, não no tipo
                (*_span("kidney injury"), "Disease"),          # nome cortado: erro
                (*_span("rats"), "Disease")]                   # não anotado: erro

    r = nb.evaluate(docs, extract)
    assert (r["total"]["tp"], r["total"]["fp"], r["total"]["fn"]) == (2, 2, len(gold) - 2)
    assert r["by_type"]["Chemical"]["tp"] == 1 and r["by_type"]["Disease"]["tp"] == 0
    assert r["gold"] == len(gold) and r["predicted"] == 4


def test_snap_expands_to_the_whole_word():
    text = "long QT syndrome and lamivudine"
    assert nb.snap(text, 6, 16) == (5, 16)     # "T syndrome" vira "QT syndrome"
    assert nb.snap(text, 21, 26) == (21, 31)


@pytest.mark.parametrize("label, expected", [("Chemical", "Chemical"), ("B-Disease", "Disease"),
                                             ("chemical", "Chemical"), ("Gene", None)])
def test_hf_labels_map_to_gold_types(label, expected):
    assert nb.hf_type(label) == expected
