"""BiomedicalNER com um pipeline falso no lugar do modelo do Hugging Face (nada é baixado)."""
import pytest

from omaker.domain.labels import NER_MODEL_NAME
from omaker.nlp import ner as ner_mod


def _item(sentence, word, label, score, start=None):
    """Detecção no formato do pipeline token-classification (posições relativas à frase)."""
    start = sentence.index(word) if start is None else start
    return {"entity_group": label, "score": score, "start": start, "end": start + len(word), "word": word}


@pytest.fixture
def make_ner(monkeypatch):
    """make_ner(detect) -> BiomedicalNER cujo pipeline chama detect(frase) para cada frase."""
    import sys

    from transformers import pipeline  # noqa: F401  carrega o atributo preguiçoso, que troca o módulo em sys.modules

    transformers = sys.modules["transformers"]   # o módulo que o "from transformers import pipeline" do NER lê
    created = {}

    def fake_pipeline(task, **kwargs):
        created.update(task=task, **kwargs)

        def pipe(sentences, batch_size=8):
            created.setdefault("sentences", []).extend(sentences)
            return [created["detect"](s) for s in sentences]

        return pipe

    monkeypatch.setattr(transformers, "pipeline", fake_pipeline)

    def make(detect):
        created["detect"] = detect
        model = ner_mod.BiomedicalNER(device=-1)
        model.created = created
        return model

    return make


# ---- ENT-02: NER biomédico por frase
def test_ner_uses_the_biomedical_model_with_subtoken_aggregation(make_ner):
    model = make_ner(lambda s: [])
    assert model.created["task"] == "token-classification"
    assert model.created["model"] == NER_MODEL_NAME == "d4data/biomedical-ner-all"
    assert model.created["aggregation_strategy"] == "simple"


def test_ner_runs_sentence_by_sentence_and_offsets_count_from_the_start_of_the_text(make_ner):
    text = "Patients were stable. They received aspirin daily."

    def detect(sentence):
        return [_item(sentence, "aspirin", "Medication", 0.99)] if "aspirin" in sentence else []

    model = make_ner(detect)
    (e,) = model.extract(text)
    assert model.created["sentences"] == ["Patients were stable.", "They received aspirin daily."]
    assert (e.start, e.end) == (text.index("aspirin"), text.index("aspirin") + len("aspirin"))
    assert text[e.start:e.end] == e.text == "aspirin"


# ---- ENT-03: rótulos aceitos do NER
@pytest.mark.parametrize("label, etype", [
    ("medication", "DRUG"), ("Sign_symptom", "SYMPTOM"), ("Disease_disorder", "DISEASE"), ("B-Medication", "DRUG"),
])
def test_ner_maps_only_the_three_accepted_labels(make_ner, label, etype):
    text = "Patients had fever."
    model = make_ner(lambda s: [_item(s, "fever", label, 0.9)])
    (e,) = model.extract(text)
    assert e.type == etype and model.last_rejected == []


def test_ner_ignores_labels_outside_the_mapping_and_records_them(make_ner):
    text = "The tumor grew."
    model = make_ner(lambda s: [_item(s, "tumor", "Coreference", 0.92)])
    assert model.extract(text) == []
    assert model.last_rejected == [("tumor", "Coreference", pytest.approx(0.92))]


@pytest.mark.parametrize("score, kept", [(0.40, False), (0.49, False), (0.50, True), (0.51, True)])
def test_ner_keeps_detections_with_score_of_at_least_one_half(make_ner, score, kept):
    text = "Patients had fever."
    model = make_ner(lambda s: [_item(s, "fever", "Sign_symptom", score)])
    entities = model.extract(text)
    assert bool(entities) is kept
    assert (model.last_rejected == [("fever", "Sign_symptom", pytest.approx(score))]) is not kept


def test_engine_logs_the_ignored_detection_with_label_and_score(make_ner, monkeypatch):
    from omaker.pipeline import engine as he

    text = "Aspirin shrank the tumor."
    model = make_ner(lambda s: [_item(s, "Aspirin", "Medication", 0.99), _item(s, "tumor", "Coreference", 0.92)])
    monkeypatch.setenv("OMAKER_ENTITIES", "ner")
    logs = []
    tax, triples = he.HybridEngine.extrair(text, "qwen3:8b", 0.1, logs.append, ner=model, with_taxonomy=False)
    assert "  [NER] ignored: 'tumor' labelled Coreference (0.92)" in logs
    assert set(tax["instances"]) == {"Aspirin"} and triples == []


def test_engine_logs_at_most_ten_ignored_detections(make_ner, monkeypatch):
    from omaker.pipeline import engine as he

    words = [f"w{i}" for i in range(12)]
    text = "Aspirin " + " ".join(words) + " end."
    model = make_ner(lambda s: [_item(s, "Aspirin", "Medication", 0.99)]
                     + [_item(s, w, "Coreference", 0.9, start=s.index(f" {w} ") + 1) for w in words])
    monkeypatch.setenv("OMAKER_ENTITIES", "ner")
    logs = []
    he.HybridEngine.extrair(text, "qwen3:8b", 0.1, logs.append, ner=model, with_taxonomy=False)
    assert len(model.last_rejected) == 12
    assert len([line for line in logs if "[NER] ignored:" in line]) == 10


# ---- ENT-05: menção estendida à palavra inteira
def test_ner_extends_a_cut_mention_to_the_whole_word(make_ner):
    text = "The patient had QT syndrome."
    model = make_ner(lambda s: [_item(s, "T syndrome", "Disease_disorder", 0.9)])
    (e,) = model.extract(text)
    assert e.text == "QT syndrome" and text[e.start:e.end] == "QT syndrome"


# ---- ENT-06: sobreposição no NER
def test_ner_keeps_the_highest_scoring_of_two_overlapping_detections(make_ner):
    text = "She had chronic kidney disease."
    model = make_ner(lambda s: [_item(s, "kidney disease", "Disease_disorder", 0.60),
                                _item(s, "chronic kidney", "Disease_disorder", 0.95)])
    (e,) = model.extract(text)
    assert e.text == "chronic kidney" and e.score == pytest.approx(0.95)


def test_ner_returns_mentions_in_text_order(make_ner):
    text = "Fever and nausea followed aspirin."
    model = make_ner(lambda s: [_item(s, "aspirin", "Medication", 0.99), _item(s, "nausea", "Sign_symptom", 0.7),
                                _item(s, "Fever", "Sign_symptom", 0.8)])
    assert [e.text for e in model.extract(text)] == ["Fever", "nausea", "aspirin"]
