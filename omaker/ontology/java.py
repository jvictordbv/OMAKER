"""Finds a Java executable for the HermiT reasoner even when `java` is not on PATH.

owlready2 only looks at PATH. On Windows Java is often installed under Program Files without
being on PATH, and Protégé ships its own JRE next to Protege.exe.
"""
from __future__ import annotations

import os
import re
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path

DEFAULT_ROOTS: tuple[Path, ...] = (
    Path(r"C:\Program Files\Java"),
    Path(r"C:\Program Files\Eclipse Adoptium"),
    Path(r"C:\Program Files\Microsoft"),
)


def _version_key(folder: Path) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", folder.name))


def _newest_in(root: Path) -> Path | None:
    try:
        candidates = [d / "bin" / "java.exe" for d in root.iterdir() if d.is_dir()]
    except OSError:
        return None
    candidates = [c for c in candidates if c.is_file()]
    return max(candidates, key=lambda c: _version_key(c.parent.parent), default=None)


def find_java(protege_exe: str = "", env: Mapping[str, str] | None = None,
              roots: Sequence[Path] = DEFAULT_ROOTS) -> str | None:
    env = os.environ if env is None else env

    explicit = env.get("OMAKER_JAVA", "")
    if explicit and Path(explicit).is_file():
        return explicit

    java_home = env.get("JAVA_HOME", "")
    if java_home:
        candidate = Path(java_home) / "bin" / "java.exe"
        if candidate.is_file():
            return str(candidate)

    on_path = shutil.which("java")
    if on_path:
        return on_path

    for root in roots:
        newest = _newest_in(Path(root))
        if newest:
            return str(newest)

    if protege_exe:
        bundled = Path(protege_exe).parent / "jre" / "bin" / "java.exe"
        if bundled.is_file():
            return str(bundled)
    return None
