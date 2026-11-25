"""Configuração do OMAKER lida do ambiente na hora do uso (não na importação).

Variáveis reconhecidas:
- OLLAMA_HOST: endereço do Ollama (padrão http://localhost:11434; sem esquema, recebe http://).
- OMAKER_ENTITIES: de onde vêm as entidades: ner, llm ou both (padrão both).
- OMAKER_CHECKPOINT: caminho do checkpoint do PURE (padrão omaker_pure.pt na raiz do projeto; no .exe,
  %LOCALAPPDATA%\\OMAKER\\models).
- OMAKER_NO_DOWNLOAD: 1 desliga o download automático do checkpoint publicado (omaker/relations/download.py).
- OMAKER_JAVA: java.exe usado pelo HermiT; lido por omaker.ontology.java.find_java.
- OMAKER_LLM_SEED: semente enviada ao Ollama (padrão: nenhuma); a avaliação usa 0 para reprodutibilidade.
- OMAKER_LLM_PROMPT: prompt de relações do LLM: default (o escrito à mão) ou optimized (o exportado por
  python -m omaker.llm.optimize --install, em omaker/llm/prompts/relations_optimized.json).
- OMAKER_NER_MODEL: NER biomédico: d4data (padrão, d4data/biomedical-ner-all) ou bc5cdr
  (judithrosell/BC5CDR_PubMedBERT_NER, com sintomas tipados pela Symptom Ontology).

As preferências da interface (modelo, temperatura, pastas, Protégé) ficam no QSettings da GUI.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
ENTITY_SOURCES = ("ner", "llm", "both")
LLM_PROMPTS = ("default", "optimized")
NER_MODELS = ("d4data", "bc5cdr")


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
    source = env.get("OMAKER_ENTITIES", "").strip().lower() or "both"
    if source not in ENTITY_SOURCES:
        raise ValueError(f"OMAKER_ENTITIES='{env.get('OMAKER_ENTITIES')}' inválido; use ner, llm ou both.")
    return source


def checkpoint(env: Mapping[str, str] | None = None) -> Path | None:
    env = os.environ if env is None else env
    value = env.get("OMAKER_CHECKPOINT", "").strip()
    return Path(value) if value else None


def llm_seed(env: Mapping[str, str] | None = None) -> int | None:
    env = os.environ if env is None else env
    value = env.get("OMAKER_LLM_SEED", "").strip()
    return int(value) if value else None


def llm_prompt(env: Mapping[str, str] | None = None) -> str:
    """Validated OMAKER_LLM_PROMPT. Checked only where the LLM classifies relations."""
    env = os.environ if env is None else env
    value = env.get("OMAKER_LLM_PROMPT", "").strip().lower() or "default"
    if value not in LLM_PROMPTS:
        raise ValueError(f"OMAKER_LLM_PROMPT='{env.get('OMAKER_LLM_PROMPT')}' inválido; use default ou optimized.")
    return value


def ner_model(env: Mapping[str, str] | None = None) -> str:
    """Validated OMAKER_NER_MODEL. Checked only where the NER is created."""
    env = os.environ if env is None else env
    value = env.get("OMAKER_NER_MODEL", "").strip().lower() or "d4data"
    if value not in NER_MODELS:
        raise ValueError(f"OMAKER_NER_MODEL='{env.get('OMAKER_NER_MODEL')}' inválido; use d4data ou bc5cdr.")
    return value


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """All settings at once (validates every variable)."""
    env = os.environ if env is None else env
    return Settings(ollama_host(env), entity_source(env), checkpoint(env))
