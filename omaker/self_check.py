"""Verificação do executável: `OMAKER.exe --self-check arquivo.txt`.

O .exe é uma janela (sem console), então o resultado vai para um arquivo. Importa tudo o que o
pipeline usa, inclusive os módulos que o transformers só carrega na hora (BERT do SpanBERT e do
Sentence-BERT, DistilBERT do NER), monta modelos mínimos sem baixar nada e confere os arquivos de
dados. O CI roda isto no .exe montado: um módulo esquecido pelo PyInstaller aparece aqui, e não no
computador do usuário.
"""
from __future__ import annotations

import traceback
from pathlib import Path

MODULES = (
    "torch",
    "transformers",
    "transformers.pipelines.token_classification",
    "transformers.models.bert.modeling_bert",
    "transformers.models.bert.tokenization_bert",
    "transformers.models.distilbert.modeling_distilbert",
    "sentence_transformers",
    "sklearn",
    "owlready2",
    "requests",
    "PySide6.QtWidgets",
    "omaker.pipeline.engine",
    "omaker.relations.model",
    "omaker.relations.download",
    "omaker.nlp.ner",
    "omaker.nlp.synonyms",
    "omaker.ui.main_window",
)


def _tiny_models() -> None:
    """Instancia BERT e DistilBERT mínimos (sem download) e roda um passo."""
    import torch
    from transformers import BertConfig, BertModel, DistilBertConfig, DistilBertForTokenClassification

    small = dict(vocab_size=50, hidden_size=16, num_hidden_layers=1, num_attention_heads=2, intermediate_size=32)
    ids = torch.tensor([[1, 2, 3]])
    BertModel(BertConfig(**small))(ids)
    DistilBertForTokenClassification(DistilBertConfig(vocab_size=50, dim=16, n_layers=1, n_heads=2,
                                                      hidden_dim=32, num_labels=3))(ids)


def _data_files() -> list[str]:
    import owlready2

    from omaker.paths import package_resource, project_root

    missing = [str(p) for p in (package_resource("symp.owl"), project_root() / "LICENSE") if not p.is_file()]
    hermit = Path(owlready2.__file__).parent / "hermit"
    if not hermit.is_dir():
        missing.append(str(hermit))
    return missing


def run(out_path) -> int:
    """Grava 'OK' (código 0) ou a lista de falhas (código 1) em out_path."""
    import importlib

    lines, failed = [], False
    for name in MODULES:
        try:
            importlib.import_module(name)
            lines.append(f"ok      import {name}")
        except Exception:  # noqa: BLE001  qualquer falha de import vira uma linha do relatório
            failed = True
            lines.append(f"FALHOU  import {name}\n{traceback.format_exc()}")
    for label, check in (("modelos mínimos", _tiny_models),):
        try:
            check()
            lines.append(f"ok      {label}")
        except Exception:  # noqa: BLE001
            failed = True
            lines.append(f"FALHOU  {label}\n{traceback.format_exc()}")
    try:
        missing = _data_files()
    except Exception:  # noqa: BLE001
        missing = [traceback.format_exc()]
    for path in missing:
        failed = True
        lines.append(f"FALHOU  arquivo de dados ausente: {path}")
    if not missing:
        lines.append("ok      arquivos de dados")
    lines.append("FALHOU" if failed else "OK")
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 1 if failed else 0
