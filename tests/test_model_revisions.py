"""Os modelos do Hugging Face são carregados numa revisão (commit) fixa, sem internet nos testes."""
import re

import pytest
import transformers

from omaker.domain.labels import MODEL_NAME, MODEL_REVISION, NER_MODEL_NAME, NER_MODEL_REVISION
from omaker.nlp import synonyms


@pytest.mark.parametrize("revision", [MODEL_REVISION, NER_MODEL_REVISION, synonyms.SYNONYM_MODEL_REVISION])
def test_revisions_are_full_commit_hashes(revision):
    assert re.fullmatch(r"[0-9a-f]{40}", revision)


def test_ner_pipeline_gets_pinned_revision(monkeypatch):
    from omaker.nlp.ner import BiomedicalNER

    seen = {}
    # by name: importing sentence_transformers replaces sys.modules["transformers"] with a new lazy module
    monkeypatch.setattr("transformers.pipeline", lambda *a, **k: seen.update(k) or object())
    BiomedicalNER(device=-1)
    assert seen["model"] == NER_MODEL_NAME and seen["revision"] == NER_MODEL_REVISION


def test_sentence_bert_gets_pinned_revision(monkeypatch):
    seen = {}
    monkeypatch.setattr(synonyms, "SentenceTransformer", lambda name, **k: seen.update(name=name, **k))
    synonyms.SynonymDetector()
    assert seen == {"name": synonyms.SYNONYM_MODEL_NAME, "revision": synonyms.SYNONYM_MODEL_REVISION}


def test_pure_pins_spanbert_revision_in_training_and_load(tiny_fp16_model, tmp_path, monkeypatch):
    """O nome do SpanBERT é servido pelo BERT mínimo; registra a revisão pedida em cada construtor."""
    from omaker.relations.model import RelationExtractorPURE

    calls = []

    def recording(cls):
        original = cls.from_pretrained

        def fake(name, *a, **k):
            calls.append((cls.__name__, name, k.pop("revision", None)))
            return original(tiny_fp16_model, *a, **k)
        return fake

    for cls in (transformers.AutoTokenizer, transformers.AutoModel, transformers.AutoConfig):
        monkeypatch.setattr(cls, "from_pretrained", recording(cls))

    model = RelationExtractorPURE()
    spanbert = [c for c in calls if c[1] == MODEL_NAME]
    assert {c[0] for c in spanbert} >= {"AutoTokenizer", "AutoModel"}
    assert all(c[2] == MODEL_REVISION for c in spanbert)

    ckpt = tmp_path / "pure.pt"
    model.save(str(ckpt))
    calls.clear()
    RelationExtractorPURE.load(str(ckpt), device="cpu")
    spanbert = [c for c in calls if c[1] == MODEL_NAME]
    assert {c[0] for c in spanbert} == {"AutoTokenizer", "AutoConfig"}
    assert all(c[2] == MODEL_REVISION for c in spanbert)
    assert not any(c[0] == "AutoModel" for c in calls)
