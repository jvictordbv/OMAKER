"""Configuração de um treino do PURE, lida de um TOML (seção [train]) e gravada junto com cada execução."""
from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from omaker.domain.labels import MODEL_NAME

DEFAULT_DATA = str(Path(__file__).parent / "train_relations.json")


@dataclass(frozen=True)
class TrainConfig:
    name: str = "pure"
    data_path: str = DEFAULT_DATA
    splits_dir: str = ""             # se existir, reaproveita a divisão gravada em vez de sortear outra
    seed: int = 42
    fractions: tuple[float, float, float] = (0.7, 0.15, 0.15)
    model_name: str = MODEL_NAME
    epochs: int = 15
    lr_encoder: float = 2e-5
    lr_classifier: float = 1e-3
    weight_decay: float = 0.01
    batch_size: int = 8
    grad_accum: int = 1
    runs_dir: str = "runs"


def load_config(path) -> TrainConfig:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8")).get("train", {})
    known = {f.name for f in fields(TrainConfig)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ValueError(f"chave desconhecida em [train]: {', '.join(unknown)}")
    if "fractions" in data:
        data["fractions"] = tuple(data["fractions"])
    return TrainConfig(**data)


def _toml_value(value) -> str:
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    return repr(value)


def dump_config(config: TrainConfig, path) -> None:
    lines = ["[train]"] + [f"{k} = {_toml_value(v)}" for k, v in asdict(config).items()]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
