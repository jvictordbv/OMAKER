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
    kw = {"epochs": 2, **kw}
    return TrainConfig(name="teste", data_path=str(DATA_PATH), runs_dir=str(tmp_path / "runs"), **kw)


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


class CrashingModel(FakeModel):
    """Cai no meio do treino, depois de `crash_after` passos de treino (simula queda de energia)."""

    crash_after = 0
    calls = 0

    def forward(self, samples):
        if self.training:
            CrashingModel.calls += 1
            if CrashingModel.calls > CrashingModel.crash_after:
                raise KeyboardInterrupt("queda simulada")
        return super().forward(samples)


def _crash_then_resume(tmp_path, crash_after, **kw):
    from omaker.relations.train import resume_training
    CrashingModel.calls, CrashingModel.crash_after = 0, crash_after
    cfg = _config(tmp_path, epochs=3, batch_size=2, **kw)
    with pytest.raises(KeyboardInterrupt):
        run_training(cfg, model_factory=CrashingModel)
    (run,) = (tmp_path / "runs").iterdir()
    assert (run / "last.pt").exists() and not (run / "metrics.json").exists()
    return resume_training(run, model_factory=FakeModel)


@pytest.mark.parametrize("crash_after", [3, 13, 21])   # meio da 1a época, meio da 2a, fim de época
def test_resume_after_crash_matches_uninterrupted_run(tmp_path, crash_after):
    reference = run_training(_config(tmp_path / "ref", epochs=3, batch_size=2, save_every_steps=2),
                             model_factory=FakeModel)
    resumed = _crash_then_resume(tmp_path / "crash", crash_after, save_every_steps=2)
    a = json.loads((reference / "metrics.json").read_text("utf-8"))
    b = json.loads((resumed / "metrics.json").read_text("utf-8"))
    assert a["history"] == b["history"]
    assert a["test"] == b["test"] and a["best_epoch"] == b["best_epoch"]
    assert not (resumed / "last.pt").exists()   # terminado: o ponto de retomada é apagado


def test_resume_of_finished_run_does_nothing(tmp_path):
    from omaker.relations.train import resume_training
    run = run_training(_config(tmp_path), model_factory=FakeModel)
    before = (run / "metrics.json").read_text("utf-8")
    assert resume_training(run, model_factory=FakeModel) == run
    assert (run / "metrics.json").read_text("utf-8") == before


def test_resume_without_checkpoint_fails_clearly(tmp_path):
    from omaker.relations.train import resume_training
    (tmp_path / "vazio").mkdir()
    with pytest.raises(FileNotFoundError, match="last.pt"):
        resume_training(tmp_path / "vazio", model_factory=FakeModel)


def test_missing_splits_dir_fails_clearly(tmp_path):
    with pytest.raises(FileNotFoundError, match="omaker.relations.biored"):
        run_training(_config(tmp_path, splits_dir=str(tmp_path / "nao-existe")), model_factory=FakeModel)


def test_biored_config_is_valid():
    from omaker.paths import project_root
    cfg = load_config(project_root() / "configs" / "pure_biored.toml")
    assert cfg.splits_dir == "data/biored/splits" and cfg.save_every_steps == 50
