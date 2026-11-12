"""Abre uma ontologia no Protégé."""
import os
import subprocess


def abrir_no_protege(caminho_owl: str, protege_exe: str) -> subprocess.Popen:
    if not protege_exe or not os.path.isfile(protege_exe):
        raise FileNotFoundError(
            f"Protégé não encontrado em '{protege_exe}'. "
            "Informe o Protege.exe nas Configurações."
        )
    if not caminho_owl or not os.path.isfile(caminho_owl):
        raise FileNotFoundError(f"Ontologia não encontrada: '{caminho_owl}'")
    return subprocess.Popen(
        [protege_exe, os.path.abspath(caminho_owl)],
        cwd=os.path.dirname(protege_exe),
    )
