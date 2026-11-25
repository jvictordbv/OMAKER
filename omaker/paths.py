"""Caminhos independentes do diretório corrente."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from omaker.config import checkpoint
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


def user_data_dir() -> Path:
    """Pasta gravável do usuário para os modelos baixados (%LOCALAPPDATA%\\OMAKER no Windows)."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "OMAKER"


def default_output_dir() -> Path:
    """Pasta de destino padrão das ontologias: Documentos/OMAKER do usuário (não a pasta corrente)."""
    return Path.home() / "Documents" / "OMAKER"


def default_checkpoint_path() -> Path:
    """OMAKER_CHECKPOINT; no .exe, a pasta do usuário (a do programa é temporária); senão, a raiz do projeto."""
    if checkpoint():
        return checkpoint()
    if getattr(sys, "frozen", False):
        return user_data_dir() / "models" / DEFAULT_CHECKPOINT
    return project_root() / DEFAULT_CHECKPOINT
