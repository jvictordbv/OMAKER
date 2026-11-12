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


def test_version_matches_pyproject():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert omaker.__version__ == project["version"]


def test_spec_is_valid_python():
    ast.parse((ROOT / "OMAKER.spec").read_text(encoding="utf-8"))
