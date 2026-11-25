"""SynonymDetector com embeddings falsos no lugar do Sentence-BERT (nada é baixado)."""
import math

import numpy as np
import pytest

from omaker.nlp import synonyms as syn

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class FakeEncoder:
    """encode(termos) -> vetores fixos por termo; guarda o que recebeu."""

    def __init__(self, vectors):
        self.vectors, self.calls = vectors, []

    def encode(self, terms):
        self.calls.append(list(terms))
        return np.array([self.vectors[t] for t in terms], dtype=float)


def _unit(angle_cos):
    """Vetor 2D unitário cuja similaridade de cosseno com (1, 0) é angle_cos."""
    return [angle_cos, math.sqrt(1 - angle_cos ** 2)]


@pytest.fixture
def detector(monkeypatch):
    """make(vectors) -> SynonymDetector com o encoder falso; registra o nome de modelo pedido."""
    loaded = []

    def fake_sentence_transformer(name, revision=None):
        loaded.append(name)
        return None

    monkeypatch.setattr(syn, "SentenceTransformer", fake_sentence_transformer)

    def make(vectors):
        d = syn.SynonymDetector()
        d.model = FakeEncoder(vectors)
        d.loaded = loaded
        return d

    return make


# ---- SIN-01: agrupamento por similaridade
def test_detector_loads_the_multilingual_minilm_model(detector):
    assert detector({}).loaded == [MODEL]


def test_synonyms_are_grouped_and_an_isolated_term_is_left_out(detector):
    d = detector({"fever": [1.0, 0.0], "pyrexia": _unit(0.98), "cough": [0.0, 1.0]})
    groups = d.agrupar_sinonimos(["fever", "pyrexia", "cough"])
    assert sorted(map(sorted, groups.values())) == [["fever", "pyrexia"]]
    assert all(len(g) >= 2 for g in groups.values())


@pytest.mark.parametrize("similarity, grouped", [(0.80, True), (0.70, False)])
def test_cosine_distance_threshold_is_0_25(detector, similarity, grouped):
    d = detector({"a": [1.0, 0.0], "b": _unit(similarity)})
    assert bool(d.agrupar_sinonimos(["a", "b"])) is grouped   # distância 0,20 agrupa; 0,30 não


def test_clustering_uses_average_linkage(detector, monkeypatch):
    # a-b e b-c estão perto (distância 0,2), a-c longe (0,5): com ligação média, o terceiro termo fica de fora
    # (média 0,35 > 0,25); com ligação simples, os três se juntariam.
    dist = np.array([[0.0, 0.2, 0.5], [0.2, 0.0, 0.2], [0.5, 0.2, 0.0]])
    monkeypatch.setattr(syn, "cosine_similarity", lambda _v: 1 - dist)
    d = detector({"a": [0.0], "b": [0.0], "c": [0.0]})
    groups = d.agrupar_sinonimos(["a", "b", "c"])
    assert [sorted(g) for g in groups.values()] in ([["a", "b"]], [["b", "c"]])


# ---- SIN-02: poucos termos
@pytest.mark.parametrize("terms", [[], ["fever"]])
def test_fewer_than_two_terms_give_no_group_and_no_embedding(detector, terms):
    d = detector({"fever": [1.0, 0.0]})
    assert d.agrupar_sinonimos(terms) == {}
    assert d.model.calls == []
