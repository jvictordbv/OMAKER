"""Configuração do OMAKER lida do ambiente na hora do uso (não na importação).

Variáveis reconhecidas:
- OLLAMA_HOST: endereço do Ollama (padrão http://localhost:11434; sem esquema, recebe http://).
- OMAKER_ENTITIES: de onde vêm as entidades: ner, llm ou both (padrão both).
- OMAKER_CHECKPOINT: caminho do checkpoint do PURE (padrão omaker_pure.pt na raiz do projeto).
- OMAKER_JAVA: java.exe usado pelo HermiT; lido por omaker.ontology.java.find_java.

As preferências da interface (modelo, temperatura, pastas, Protégé) ficam no QSettings da GUI.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
ENTITY_SOURCES = ("ner", "llm", "both")


@dataclass(frozen=True)
class Settings:
    ollama_host: str
    entity_source: str
    checkpoint: Path | None


def ollama_host(env: Mapping[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    host = env.get("OLLAMA_HOST", "").strip() or DEFAULT_OLLAMA_HOST
    return host if host.startswith("http") else "http://" + host


def entity_source(env: Mapping[str, str] | None = None) -> str:
    """Validated OMAKER_ENTITIES. Checked only where entities are extracted, so a typo
    does not break commands that never use it (training, the Ollama client)."""
    env = os.environ if env is None else env
    source = env.get("OMAKER_ENTITIES", "both").strip().lower()
    if source not in ENTITY_SOURCES:
        raise ValueError(f"OMAKER_ENTITIES='{env.get('OMAKER_ENTITIES')}' inválido; use ner, llm ou both.")
    return source


def checkpoint(env: Mapping[str, str] | None = None) -> Path | None:
    env = os.environ if env is None else env
    value = env.get("OMAKER_CHECKPOINT", "").strip()
    return Path(value) if value else None


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """All settings at once (validates every variable)."""
    env = os.environ if env is None else env
    return Settings(ollama_host(env), entity_source(env), checkpoint(env))
