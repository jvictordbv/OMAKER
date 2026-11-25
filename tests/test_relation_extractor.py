import pytest
import torch

from omaker.domain.labels import MODEL_NAME, REL2ID
from omaker.relations.model import RelationExtractorPURE

SAMPLE_TEXT = "aspirin prevents stroke ."


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


def _no_base_weights(*_a, **_k):
    raise AssertionError("load must build the encoder from its config, not download the base weights")


def test_load_builds_encoder_from_config_without_base_weights(tiny_fp16_model, tmp_path, monkeypatch):
    import transformers

    torch.manual_seed(0)
    model = RelationExtractorPURE(model_name=tiny_fp16_model)
    ckpt = tmp_path / "pure.pt"
    model.save(str(ckpt), extra={"train_text_hashes": ["ab" * 32], "train_texts": [SAMPLE_TEXT]})
    sample = dict(text=SAMPLE_TEXT, sub_span=(0, 7), sub_type="DRUG", obj_span=(17, 23), obj_type="DISEASE")
    model.eval()
    with torch.no_grad():
        expected_logits = model([sample])[0]
    expected = model.predict([sample])

    monkeypatch.setattr(transformers.AutoModel, "from_pretrained", _no_base_weights)
    monkeypatch.setattr(transformers.PreTrainedModel, "from_pretrained", _no_base_weights)
    loaded = RelationExtractorPURE.load(str(ckpt), device="cpu")

    assert {p.dtype for p in loaded.parameters()} == {torch.float32}
    assert len(loaded.tokenizer) == len(model.tokenizer)
    with torch.no_grad():
        torch.testing.assert_close(loaded([sample])[0], expected_logits)
    (rel, conf), = loaded.predict([sample])
    assert rel == expected[0][0] and conf == pytest.approx(expected[0][1])


def test_load_uses_weights_only(tiny_fp16_model, tmp_path, monkeypatch):
    ckpt = tmp_path / "pure.pt"
    RelationExtractorPURE(model_name=tiny_fp16_model).save(str(ckpt))
    calls, original = [], torch.load
    monkeypatch.setattr(torch, "load", lambda *a, **k: calls.append(k) or original(*a, **k))
    RelationExtractorPURE.load(str(ckpt), device="cpu")
    assert calls and all(k.get("weights_only") is True for k in calls)


@pytest.mark.slow
def test_spanbert_roundtrip(tmp_path):
    _roundtrip(MODEL_NAME, tmp_path)
