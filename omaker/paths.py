"""Caminhos independentes do diretório corrente."""
from __future__ import annotations

import sys
from pathlib import Path

from omaker.config import load_settings
from omaker.domain.labels import DEFAULT_CHECKPOINT


def project_root() -> Path:
    """Pasta que contém OMAKER.py (num executável PyInstaller, a pasta de recursos)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    return project_root().joinpath(*parts)


def package_resource(name: str) -> Path:
    """Arquivo de dados do pacote (omaker/resources/), no código-fonte e no executável."""
    return Path(__file__).resolve().parent / "resources" / name


def default_checkpoint_path() -> Path:
    return load_settings().checkpoint or project_root() / DEFAULT_CHECKPOINT
