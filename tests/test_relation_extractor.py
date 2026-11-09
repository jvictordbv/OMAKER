import pytest
import torch
from transformers import BertConfig, BertModel, BertTokenizerFast

from core.labels import MODEL_NAME, REL2ID
from core.relation_extractor import RelationExtractorPURE

SAMPLE_TEXT = "aspirin prevents stroke ."


@pytest.fixture
def tiny_fp16_model(tmp_path):
    """Tiny BERT saved in float16 (like the SpanBERT checkpoint) plus its tokenizer; offline."""
    path = tmp_path / "tiny_bert"
    path.mkdir()
    vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"] + SAMPLE_TEXT.split()
    (path / "vocab.txt").write_text("\n".join(vocab) + "\n", encoding="utf-8")
    BertTokenizerFast(vocab_file=str(path / "vocab.txt")).save_pretrained(path)
    config = BertConfig(
        vocab_size=64, hidden_size=32, num_hidden_layers=1, num_attention_heads=2, intermediate_size=64
    )
    BertModel(config).half().save_pretrained(path)
    return str(path)


def _roundtrip(model_name, tmp_path):
    model = RelationExtractorPURE(model_name=model_name)
    assert {p.dtype for p in model.parameters()} == {torch.float32}
    ckpt = tmp_path / "pure.pt"
    model.save(str(ckpt))
    loaded = RelationExtractorPURE.load(str(ckpt), device="cpu")
    assert {p.dtype for p in loaded.parameters()} == {torch.float32}
    sample = dict(text=SAMPLE_TEXT, sub_span=(0, 7), sub_type="DRUG", obj_span=(17, 23), obj_type="DISEASE")
    (rel, conf), = loaded.predict([sample])
    assert rel in REL2ID and 0.0 <= conf <= 1.0


def test_load_fp16_base_model_predicts(tiny_fp16_model, tmp_path):
    _roundtrip(tiny_fp16_model, tmp_path)


def test_load_rejects_incompatible_labels(tiny_fp16_model, tmp_path):
    ckpt = tmp_path / "pure.pt"
    RelationExtractorPURE(model_name=tiny_fp16_model).save(str(ckpt), extra={"rel2id": {"treats": 0}})
    with pytest.raises(ValueError, match="Retrain"):
        RelationExtractorPURE.load(str(ckpt), device="cpu")


@pytest.mark.slow
def test_spanbert_roundtrip(tmp_path):
    _roundtrip(MODEL_NAME, tmp_path)
