from pathlib import Path

from core import java_locator
from core.java_locator import find_java


def _exe(base: Path, *parts: str) -> Path:
    path = base.joinpath(*parts, "bin", "java.exe")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def _no_path(monkeypatch):
    monkeypatch.setattr(java_locator.shutil, "which", lambda _: None)


def test_omaker_java_wins(tmp_path, monkeypatch):
    mine = tmp_path / "meu_java.exe"
    mine.write_bytes(b"")
    home = _exe(tmp_path, "home")
    monkeypatch.setattr(java_locator.shutil, "which", lambda _: str(tmp_path / "path_java.exe"))
    env = {"OMAKER_JAVA": str(mine), "JAVA_HOME": str(tmp_path / "home")}
    assert find_java(env=env, roots=[]) == str(mine)
    assert home.exists()


def test_java_home_used(tmp_path, monkeypatch):
    _no_path(monkeypatch)
    java = _exe(tmp_path, "home")
    env = {"JAVA_HOME": str(tmp_path / "home")}
    assert find_java(env=env, roots=[]) == str(java)


def test_path_used_before_program_files(tmp_path, monkeypatch):
    on_path = tmp_path / "onpath" / "java.exe"
    on_path.parent.mkdir()
    on_path.write_bytes(b"")
    _exe(tmp_path / "root", "jdk-17")
    monkeypatch.setattr(java_locator.shutil, "which", lambda _: str(on_path))
    assert find_java(env={}, roots=[tmp_path / "root"]) == str(on_path)


def test_newest_jdk_in_roots(tmp_path, monkeypatch):
    _no_path(monkeypatch)
    root = tmp_path / "root"
    _exe(root, "jdk-9")
    _exe(root, "jdk-17.0.2")
    newest = _exe(root, "jdk-26.0.1")
    assert find_java(env={}, roots=[root]) == str(newest)


def test_protege_bundled_jre(tmp_path, monkeypatch):
    _no_path(monkeypatch)
    (tmp_path / "Protege.exe").write_bytes(b"")
    java = tmp_path / "jre" / "bin" / "java.exe"
    java.parent.mkdir(parents=True)
    java.write_bytes(b"")
    assert find_java(str(tmp_path / "Protege.exe"), env={}, roots=[]) == str(java)


def test_none_when_nothing(monkeypatch):
    _no_path(monkeypatch)
    assert find_java(env={}, roots=[]) is None


def test_missing_omaker_java_falls_through(tmp_path, monkeypatch):
    _no_path(monkeypatch)
    java = _exe(tmp_path, "home")
    env = {"OMAKER_JAVA": str(tmp_path / "nao_existe.exe"), "JAVA_HOME": str(tmp_path / "home")}
    assert find_java(env=env, roots=[]) == str(java)


def test_java_home_without_java_falls_through(tmp_path, monkeypatch):
    _no_path(monkeypatch)
    (tmp_path / "home").mkdir()
    root = tmp_path / "root"
    java = _exe(root, "jdk-17")
    env = {"JAVA_HOME": str(tmp_path / "home")}
    assert find_java(env=env, roots=[root]) == str(java)
