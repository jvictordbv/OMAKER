from omaker import paths


def test_checkpoint_path_independent_of_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("OMAKER_CHECKPOINT", raising=False)
    monkeypatch.chdir(tmp_path)
    assert paths.default_checkpoint_path() == paths.project_root() / "omaker_pure.pt"


def test_checkpoint_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("OMAKER_CHECKPOINT", str(tmp_path / "x.pt"))
    assert paths.default_checkpoint_path() == tmp_path / "x.pt"


def test_project_root_holds_entrypoint_and_resource_path():
    assert (paths.project_root() / "OMAKER.py").exists()
    assert paths.resource_path("omaker", "domain", "labels.py").exists()
