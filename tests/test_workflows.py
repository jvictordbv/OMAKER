"""Guardas da configuração do CI e do empacotamento (o que dá para conferir sem rodar o CI)."""
import re
import tomllib
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _load(name):
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _triggers(wf):
    return wf.get("on", wf.get(True))   # o YAML 1.1 lê a chave "on" como True


def _run(job):
    return "\n".join(step.get("run", "") for step in job["steps"])


# ---- RNF-21: fluxos do CI com permissões mínimas
@pytest.mark.parametrize("name", ["ci.yml", "exe.yml"])
def test_workflows_are_read_only_by_default(name):
    assert _load(name)["permissions"] == {"contents": "read"}


def test_only_the_release_job_can_write_to_the_repository():
    for name in ("ci.yml", "exe.yml"):
        for job_name, job in _load(name)["jobs"].items():
            if (name, job_name) == ("exe.yml", "release"):
                assert job["permissions"] == {"contents": "write"}
            else:
                assert "permissions" not in job, (name, job_name)


@pytest.mark.parametrize("name", ["ci.yml", "exe.yml"])
def test_every_external_action_is_pinned_by_commit_sha(name):
    uses = [step["uses"] for job in _load(name)["jobs"].values() for step in job["steps"] if "uses" in step]
    assert uses
    assert all(re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", u) for u in uses), uses


# ---- RNF-07: Windows e Python 3.12
def test_project_requires_python_3_12():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["requires-python"] == ">=3.12,<3.13"


def test_tests_and_executable_build_run_on_windows():
    assert _load("ci.yml")["jobs"]["testes"]["runs-on"] == "windows-latest"
    assert _load("exe.yml")["jobs"]["exe"]["runs-on"] == "windows-latest"


# ---- RNF-18: CI com lint e testes em todo push
def test_ci_runs_lint_and_the_fast_suite_on_every_push_and_pull_request():
    ci = _load("ci.yml")
    assert {"push", "pull_request"} <= set(_triggers(ci))
    run = _run(ci["jobs"]["testes"])
    assert "ruff check ." in run
    assert 'pytest -q -m "not slow and not ollama"' in run


def test_ruff_rules_are_the_documented_ones():
    lint = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["ruff"]["lint"]
    assert set(lint["select"]) == {"E", "F", "W", "B", "I", "UP", "BLE"}
    assert lint["ignore"] == ["E501"]


def test_pre_commit_hook_runs_ruff_and_the_fast_suite():
    hooks = [h for repo in yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))["repos"]
             for h in repo["hooks"]]
    assert any(h["id"] == "ruff" for h in hooks)
    (pytest_hook,) = [h for h in hooks if "pytest" in h.get("entry", "")]
    assert '-m "not slow and not ollama"' in pytest_hook["entry"] and pytest_hook.get("always_run")


# ---- DIS-06: publicação do executável
def test_executable_workflow_fails_when_self_check_fails_and_zips_the_folder():
    exe = _load("exe.yml")["jobs"]["exe"]
    names = [step.get("name", "") for step in exe["steps"]]
    check = exe["steps"][names.index("Conferir o executavel (--self-check)")]["run"]
    assert "--self-check" in check and "if ($p.ExitCode -ne 0) { exit 1 }" in check
    assert names.index("Conferir o executavel (--self-check)") < names.index("Compactar")
    assert "OMAKER-windows.zip" in exe["steps"][names.index("Compactar")]["run"]


def test_release_job_attaches_the_zip_to_the_tag_release_creating_it_if_needed():
    wf = _load("exe.yml")
    assert "v*" in _triggers(wf)["push"]["tags"]
    release = wf["jobs"]["release"]
    assert release["needs"] == "exe" and release["if"] == "startsWith(github.ref, 'refs/tags/v')"
    run = _run(release)
    assert "gh release view" in run and "|| gh release create" in run
    assert "gh release upload" in run and "OMAKER-windows.zip" in run


# ---- RNF-15: tamanho do executável e dos modelos
def test_executable_does_not_bundle_the_models():
    spec = (ROOT / "OMAKER.spec").read_text(encoding="utf-8")
    assert ".pt'" not in spec and "omaker_pure" not in spec and "spanbert" not in spec.lower()


def test_executable_workflow_reports_the_size_of_the_built_folder():
    exe = _load("exe.yml")["jobs"]["exe"]
    (size,) = [step for step in exe["steps"] if step.get("name") == "Tamanho"]
    assert "dist\\OMAKER" in size["run"] and "MB" in size["run"]
