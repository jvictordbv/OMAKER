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


def test_pair_whose_object_marker_is_cut_is_no_relation_with_zero_confidence(tiny_fp16_model):
    from omaker.relations.model import MAX_LENGTH

    model = RelationExtractorPURE(model_name=tiny_fp16_model)
    long_text = "aspirin " + "prevents " * 300 + "stroke ."
    obj = long_text.rindex("stroke")
    cut = dict(text=long_text, sub_span=(0, 7), sub_type="DRUG", obj_span=(obj, obj + 6), obj_type="DISEASE")
    short = dict(text=SAMPLE_TEXT, sub_span=(0, 7), sub_type="DRUG", obj_span=(17, 23), obj_type="DISEASE")
    marked = model.mark_text(long_text, cut["sub_span"], "DRUG", cut["obj_span"], "DISEASE")
    assert len(model.tokenizer(marked)["input_ids"]) > MAX_LENGTH == 256   # o objeto fica depois do token 256

    (rel_cut, conf_cut), (rel_short, conf_short) = model.predict([cut, short])
    assert (rel_cut, conf_cut) == ("no_relation", 0.0)
    assert rel_short in REL2ID and 0.0 < conf_short <= 1.0   # o outro par do lote continua classificado


def test_pure_input_is_truncated_to_256_tokens(tiny_fp16_model, monkeypatch):
    model = RelationExtractorPURE(model_name=tiny_fp16_model)
    seen = []
    real = model.encoder.forward

    def spy(**enc):
        seen.append(enc["input_ids"].shape[1])
        return real(**enc)

    monkeypatch.setattr(model.encoder, "forward", spy)
    long_text = "aspirin stroke " + "prevents " * 400 + "."
    model.predict([dict(text=long_text, sub_span=(0, 7), sub_type="DRUG", obj_span=(8, 14), obj_type="DISEASE")])
    assert seen == [256]
