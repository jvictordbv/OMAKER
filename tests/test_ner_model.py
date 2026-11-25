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


# ---- NER escolhível (OMAKER_NER_MODEL): d4data (padrão) ou bc5cdr, registro 0014
def test_default_ner_is_d4data_with_its_pinned_revision(make_ner):
    from omaker.domain.labels import NER_MODEL_REVISION

    model = make_ner(lambda s: [])
    assert model.created["model"] == "d4data/biomedical-ner-all"
    assert model.created["revision"] == NER_MODEL_REVISION


def test_bc5cdr_uses_its_name_and_pinned_revision(make_ner, monkeypatch):
    from omaker.domain.labels import BC5CDR_NER_MODEL_NAME, BC5CDR_NER_MODEL_REVISION

    monkeypatch.setenv("OMAKER_NER_MODEL", "bc5cdr")
    model = make_ner(lambda s: [])
    assert model.created["model"] == BC5CDR_NER_MODEL_NAME == "judithrosell/BC5CDR_PubMedBERT_NER"
    assert model.created["revision"] == BC5CDR_NER_MODEL_REVISION
    assert model.created["aggregation_strategy"] == "simple"


@pytest.mark.parametrize("label, etype", [
    ("Chemical", "DRUG"), ("B-Chemical", "DRUG"), ("Disease", "DISEASE"), ("I-Disease", "DISEASE"),
])
def test_bc5cdr_maps_chemical_to_drug_and_disease_to_disease(make_ner, monkeypatch, label, etype):
    monkeypatch.setenv("OMAKER_NER_MODEL", "bc5cdr")
    text = "Patients had lupus."
    model = make_ner(lambda s: [_item(s, "lupus", label, 0.9)])
    (e,) = model.extract(text)
    assert e.type == etype and model.last_rejected == []


def test_each_model_ignores_the_labels_of_the_other(make_ner, monkeypatch):
    text = "Patients had lupus."
    assert make_ner(lambda s: [_item(s, "lupus", "Disease", 0.9)]).extract(text) == []
    monkeypatch.setenv("OMAKER_NER_MODEL", "bc5cdr")
    model = make_ner(lambda s: [_item(s, "lupus", "Disease_disorder", 0.9)])
    assert model.extract(text) == []
    assert model.last_rejected == [("lupus", "Disease_disorder", pytest.approx(0.9))]


def test_bc5cdr_disease_matching_the_symptom_ontology_becomes_symptom(make_ner, monkeypatch):
    monkeypatch.setenv("OMAKER_NER_MODEL", "bc5cdr")
    text = "Aspirin caused Back  Pain, fever and hypertension."
    model = make_ner(lambda s: [_item(s, "Aspirin", "Chemical", 0.99), _item(s, "Back  Pain", "Disease", 0.9),
                                _item(s, "fever", "Disease", 0.9), _item(s, "hypertension", "Disease", 0.9)])
    # "back pain" é sinônimo exato de "backache" na SYMP; "fever" é rótulo; "hypertension" não está nela
    assert [(e.text, e.type) for e in model.extract(text)] == [
        ("Aspirin", "DRUG"), ("Back  Pain", "SYMPTOM"), ("fever", "SYMPTOM"), ("hypertension", "DISEASE")]


def test_d4data_does_not_retype_diseases_by_the_symptom_ontology(make_ner):
    text = "Patients had fever."
    (e,) = make_ner(lambda s: [_item(s, "fever", "Disease_disorder", 0.9)]).extract(text)
    assert e.type == "DISEASE"


def test_symptom_terms_are_labels_and_exact_synonyms_loaded_once_from_the_package(tmp_path, monkeypatch):
    ner_mod.symptom_terms.cache_clear()
    monkeypatch.chdir(tmp_path)   # o recurso empacotado não depende da pasta corrente
    terms = ner_mod.symptom_terms()
    assert {"fever", "nausea", "back pain"} <= terms and "hypertension" not in terms
    assert not any(t.startswith("symp_") for t in terms)   # nomes das classes (SYMP_0000613) não contam
    assert ner_mod.symptom_terms() is terms and ner_mod.symptom_terms.cache_info().misses == 1


def test_ner_model_is_read_when_the_ner_is_created(make_ner, monkeypatch):
    monkeypatch.setenv("OMAKER_NER_MODEL", "bc5cdr")
    assert make_ner(lambda s: []).created["model"] == "judithrosell/BC5CDR_PubMedBERT_NER"
    monkeypatch.setenv("OMAKER_NER_MODEL", "d4data")
    assert make_ner(lambda s: []).created["model"] == "d4data/biomedical-ner-all"


def test_invalid_ner_model_raises_when_the_ner_is_created(make_ner, monkeypatch):
    monkeypatch.setenv("OMAKER_NER_MODEL", "pubmedbert")
    with pytest.raises(ValueError, match="OMAKER_NER_MODEL.*d4data ou bc5cdr"):
        make_ner(lambda s: [])
