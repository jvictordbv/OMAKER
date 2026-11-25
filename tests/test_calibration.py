import json

import pytest
import torch

from omaker.domain.labels import NO_RELATION, REL2ID
from omaker.relations import calibration as cal
from tests.test_relation_extractor import SAMPLE_TEXT


def test_ece_is_zero_when_confidence_matches_accuracy():
    conf = torch.tensor([1.0, 1.0, 0.5, 0.5])
    correct = torch.tensor([True, True, True, False])
    value, bins = cal.ece(conf, correct, n_bins=10)
    assert value == pytest.approx(0.0, abs=1e-6)
    assert sum(b["n"] for b in bins) == 4


def test_ece_measures_overconfidence():
    conf = torch.full((10,), 0.9)
    correct = torch.tensor([True] * 5 + [False] * 5)
    value, _bins = cal.ece(conf, correct, n_bins=10)
    assert value == pytest.approx(0.4, abs=1e-6)


def test_fit_temperature_recovers_overconfident_scale():
    """Logits três vezes maiores que os verdadeiros: a temperatura ajustada volta a ~3."""
    gen = torch.Generator().manual_seed(0)
    true_logits = torch.randn(4000, 4, generator=gen) * 1.5
    labels = torch.multinomial(torch.softmax(true_logits, -1), 1, generator=gen).squeeze(1)
    t = cal.fit_temperature(true_logits * 3.0, labels)
    assert t == pytest.approx(3.0, rel=0.1)


def test_confidences_divide_logits_by_temperature():
    logits = torch.tensor([[2.0, 0.0], [0.0, 4.0]])
    conf1, pred1 = cal.confidences(logits, 1.0)
    conf2, pred2 = cal.confidences(logits, 2.0)
    assert pred1.tolist() == pred2.tolist() == [0, 1]   # a temperatura não muda a classe prevista
    assert (conf2 < conf1).all()


def test_apply_threshold_turns_low_confidence_relations_into_no_relation():
    preds = ["treats", "causes", NO_RELATION]
    assert cal.apply_threshold(preds, [0.9, 0.4, 0.3], 0.5) == ["treats", NO_RELATION, NO_RELATION]


def test_best_threshold_drops_wrong_low_confidence_predictions():
    golds = ["treats", "causes", NO_RELATION, NO_RELATION]
    preds = ["treats", "causes", "treats", "causes"]
    confs = [0.95, 0.9, 0.55, 0.5]          # os dois erros têm confiança baixa
    threshold, f1 = cal.best_threshold(golds, preds, confs, grid=[0.0, 0.6, 0.97])
    assert threshold == 0.6 and f1 == pytest.approx(1.0)


def test_sidecar_is_read_next_to_the_checkpoint(tmp_path):
    ckpt = tmp_path / "model.pt"
    assert cal.read_calibration(ckpt) is None
    cal.sidecar_path(ckpt).write_text(json.dumps({"temperature": 1.7, "threshold": 0.55}), encoding="utf-8")
    assert cal.sidecar_path(ckpt).name == "model.calibration.json"
    assert cal.read_calibration(ckpt) == {"temperature": 1.7, "threshold": 0.55}


def test_loaded_model_uses_calibration_sidecar(tiny_fp16_model, tmp_path):
    from omaker.relations.model import RelationExtractorPURE

    ckpt = tmp_path / "model.pt"
    RelationExtractorPURE(model_name=tiny_fp16_model).save(str(ckpt))
    sample = dict(text=SAMPLE_TEXT, sub_span=(0, 7), sub_type="DRUG", obj_span=(17, 23), obj_type="DISEASE")

    plain = RelationExtractorPURE.load(str(ckpt), device="cpu")
    assert plain.temperature == 1.0 and plain.threshold is None
    (_rel, conf_plain), = plain.predict([sample])

    cal.sidecar_path(ckpt).write_text(json.dumps({"temperature": 50.0, "threshold": 0.4}), encoding="utf-8")
    hot = RelationExtractorPURE.load(str(ckpt), device="cpu")
    assert hot.temperature == 50.0 and hot.threshold == 0.4
    (_rel, conf_hot), = hot.predict([sample])
    assert conf_hot < conf_plain and conf_hot == pytest.approx(1 / len(REL2ID), abs=0.05)


def test_install_copies_calibration_only_to_the_same_model(tmp_path, monkeypatch):
    run = tmp_path / "run"
    run.mkdir()
    (run / "model.pt").write_bytes(b"pesos A")
    cal.sidecar_path(run / "model.pt").write_text('{"temperature": 2.0, "threshold": 0.4}', encoding="utf-8")
    gui = tmp_path / "gui.pt"
    monkeypatch.setenv("OMAKER_CHECKPOINT", str(gui))

    gui.write_bytes(b"pesos B")                 # outro modelo instalado: não copia
    assert cal.install(run) is False and not cal.sidecar_path(gui).exists()
    gui.write_bytes(b"pesos A")                 # o mesmo modelo: copia
    assert cal.install(run) is True
    assert cal.read_calibration(gui) == {"temperature": 2.0, "threshold": 0.4}
