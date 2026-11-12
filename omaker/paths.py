"""Caminhos independentes do diretório corrente."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from omaker.domain.labels import DEFAULT_CHECKPOINT


def project_root() -> Path:
    """Pasta que contém OMAKER.py (num executável PyInstaller, a pasta de recursos)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    return project_root().joinpath(*parts)


def default_checkpoint_path() -> Path:
    env = os.environ.get("OMAKER_CHECKPOINT")
    return Path(env) if env else project_root() / DEFAULT_CHECKPOINT
