"""Guardas de empacotamento: o que o .spec e o pyproject precisam acompanhar."""
import ast
import re
import tomllib
from pathlib import Path

import omaker

ROOT = Path(__file__).resolve().parents[1]


def test_spec_lists_all_package_data():
    spec = (ROOT / "OMAKER.spec").read_text(encoding="utf-8")
    listed = {Path(src).as_posix() for src, _dest in re.findall(r"\(\s*'(omaker/[^']+)'\s*,\s*'([^']+)'\s*\)", spec)}
    data = {p.relative_to(ROOT).as_posix() for p in (ROOT / "omaker").rglob("*")
            if p.is_file() and p.suffix not in {".py", ".pyc"} and "__pycache__" not in p.parts}
    assert data <= listed, f"arquivos de dados fora do OMAKER.spec: {sorted(data - listed)}"


def test_spec_ships_the_optimized_prompt_once_installed():
    """O prompt otimizado só existe depois de `omaker.llm.optimize --install`; o .spec já o inclui quando houver."""
    from omaker.llm.relations import OPTIMIZED_PROMPT

    spec = (ROOT / "OMAKER.spec").read_text(encoding="utf-8")
    rel = OPTIMIZED_PROMPT.resolve().relative_to(ROOT / "omaker").as_posix()
    assert f"('omaker/{rel}', 'omaker/{Path(rel).parent.as_posix()}')" in spec


def test_dspy_is_optional_and_outside_the_exe_build():
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["optional-dependencies"]
    assert any(d.startswith("dspy") for d in extras["dspy"])
    assert not any(d.startswith("dspy") for d in extras["dev"])   # o .exe é montado com --extra dev


def test_version_matches_pyproject():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert omaker.__version__ == project["version"]


def test_spec_is_valid_python():
    ast.parse((ROOT / "OMAKER.spec").read_text(encoding="utf-8"))


def test_license_ships_with_the_executable():
    spec = (ROOT / "OMAKER.spec").read_text(encoding="utf-8")
    assert "('LICENSE', '.')" in spec and (ROOT / "LICENSE").is_file()
    assert 'license = "AGPL-3.0-only"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
