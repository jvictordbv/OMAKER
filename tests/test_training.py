import json
from collections import Counter

import pytest
import torch
import torch.nn as nn

from omaker.domain.labels import REL2ID
from omaker.relations.config import TrainConfig, load_config
from omaker.relations.train import DATA_PATH, run_training

N_REL = len(REL2ID)


class FakeModel(nn.Module):
    """Mesma interface do RelationExtractorPURE, sem baixar o SpanBERT."""

    seen: Counter = Counter()   # textos que passaram pelo modelo em modo de avaliação

    def __init__(self, model_name="fake", num_relations=N_REL):
        super().__init__()
        self.model_name = model_name
        self.encoder = nn.Linear(2, 8)
        self.classifier = nn.Linear(8, num_relations)

    def forward(self, samples):
        if not self.training:
            FakeModel.seen.update(s["text"] for s in samples)
        x = torch.tensor([[len(s["text"]) / 100.0, len(s["sub_type"]) / 10.0] for s in samples])
        return self.classifier(torch.relu(self.encoder(x))), torch.ones(len(samples), dtype=torch.bool)

    def save(self, path, extra=None):
        torch.save({"state_dict": self.state_dict()}, path)


def _config(tmp_path, **kw):
    return TrainConfig(name="teste", data_path=str(DATA_PATH), runs_dir=str(tmp_path / "runs"), epochs=2, **kw)


def test_load_config_reads_toml_and_rejects_unknown_key(tmp_path):
    good = tmp_path / "ok.toml"
    good.write_text('[train]\nname = "base"\nepochs = 3\nfractions = [0.6, 0.2, 0.2]\n', encoding="utf-8")
    cfg = load_config(good)
    assert (cfg.name, cfg.epochs, cfg.fractions) == ("base", 3, (0.6, 0.2, 0.2))
    bad = tmp_path / "bad.toml"
    bad.write_text("[train]\nepocas = 3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="epocas"):
        load_config(bad)


def test_run_writes_artifacts(tmp_path):
    run = run_training(_config(tmp_path), model_factory=FakeModel)
    for name in ("config.toml", "splits/manifest.json", "splits/test.json", "metrics.json", "report.md", "model.pt"):
        assert (run / name).exists(), name
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    assert {"dev", "test", "best_epoch", "history"} <= set(metrics)
    assert len(metrics["history"]) == 2
    assert {"micro", "macro_f1", "per_class", "ci95"} <= set(metrics["test"])
    assert load_config(run / "config.toml").epochs == 2


def test_test_set_evaluated_once(tmp_path):
    FakeModel.seen = Counter()
    run = run_training(_config(tmp_path), model_factory=FakeModel)
    test_texts = [r["text"] for r in json.loads((run / "splits" / "test.json").read_text(encoding="utf-8"))]
    assert test_texts and all(FakeModel.seen[t] == 1 for t in test_texts)


def test_training_is_reproducible(tmp_path):
    a = json.loads((run_training(_config(tmp_path), model_factory=FakeModel) / "metrics.json").read_text("utf-8"))
    b = json.loads((run_training(_config(tmp_path), model_factory=FakeModel) / "metrics.json").read_text("utf-8"))
    assert a["test"] == b["test"] and a["history"] == b["history"]


def test_gui_checkpoint_untouched_without_install(tmp_path, monkeypatch):
    gui = tmp_path / "gui.pt"
    monkeypatch.setenv("OMAKER_CHECKPOINT", str(gui))
    run_training(_config(tmp_path), model_factory=FakeModel)
    assert not gui.exists()
    run_training(_config(tmp_path), model_factory=FakeModel, install=True)
    assert gui.exists()


def test_existing_splits_are_reused(tmp_path):
    first = run_training(_config(tmp_path), model_factory=FakeModel)
    again = run_training(_config(tmp_path, splits_dir=str(first / "splits"), seed=999), model_factory=FakeModel)
    for part in ("train", "dev", "test"):
        assert (first / "splits" / f"{part}.json").read_text("utf-8") == (again / "splits" / f"{part}.json").read_text("utf-8")


@pytest.mark.slow
def test_real_spanbert_one_epoch(tmp_path):
    run = run_training(_config(tmp_path, epochs=1))
    assert (run / "metrics.json").exists()
