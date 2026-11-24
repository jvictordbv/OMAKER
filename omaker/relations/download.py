"""Baixa o checkpoint do PURE publicado numa Release do GitHub (usado pelo .exe leve e na primeira execução).

    uv run python -m omaker.relations.download            # baixa para o caminho padrão do checkpoint

O download é retomável (arquivo .part e cabeçalho Range), confere o sha256 e só então troca o nome do
arquivo. OMAKER_NO_DOWNLOAD=1 desliga o download automático (por exemplo, sem internet).
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

RELEASE = "https://github.com/jvictordbv/OMAKER/releases/download/pure-biored-v1"
PURE_MODEL = {
    "url": f"{RELEASE}/omaker_pure.pt",
    "sha256": "28d480da0038bfde17bb8037a463d1f9a90087f7fa1f835cf347c2b851504aa9",
    "calibration_url": f"{RELEASE}/omaker_pure.calibration.json",
    "calibration_sha256": "b1d8a41bb24837db6e0f5d7497da62598a3fab1299807ae29ca6a9857de783a7",
}
CHUNK = 1 << 20


def partial_path(dest: Path) -> Path:
    return dest.with_name(dest.name + ".part")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def download_file(url: str, dest, sha256: str | None, progress=None, session=None) -> Path:
    """Baixa url para dest, continuando um .part que já exista. progress(fração) é chamado durante o download."""
    import requests

    session = session or requests.Session()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = partial_path(dest)
    done = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={done}-"} if done else {}
    with session.get(url, headers=headers, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        if done and resp.status_code != 206:   # o servidor ignorou o Range: recomeça do zero
            done = 0
        total = done + int(resp.headers.get("Content-Length", 0) or 0)
        with part.open("ab" if done else "wb") as f:
            for block in resp.iter_content(CHUNK):
                f.write(block)
                done += len(block)
                if progress and total:
                    progress(done / total)
    if sha256 and _sha256(part) != sha256:
        part.unlink()
        raise ValueError(f"O arquivo baixado de {url} não confere com o sha256 esperado; baixe de novo.")
    part.replace(dest)
    return dest


def ensure_pure_checkpoint(dest, log) -> bool:
    """Garante o checkpoint em dest, baixando-o se faltar. Devolve False (e registra o motivo) se não conseguir."""
    dest = Path(dest)
    if dest.exists():
        return True
    if os.environ.get("OMAKER_NO_DOWNLOAD", "").strip() not in ("", "0"):
        return False
    log(f"> [PURE] Model not found. Downloading it once (about 440 MB) to {dest} ...")
    marks = set()

    def progress(fraction):
        mark = int(fraction * 10)
        if mark not in marks:
            marks.add(mark)
            log(f"  [PURE] download {mark * 10}%")

    try:
        download_file(PURE_MODEL["url"], dest, PURE_MODEL["sha256"], progress)
        calibration = dest.with_name(dest.stem + ".calibration.json")
        download_file(PURE_MODEL["calibration_url"], calibration, PURE_MODEL["calibration_sha256"])
    except Exception as err:  # noqa: BLE001  sem internet, Release fora do ar etc.: o pipeline segue sem o PURE
        log(f"> [PURE] Download failed ({err}). Relations will be classified by the LLM; "
            f"the download resumes next time.")
        return False
    log("> [PURE] Model downloaded.")
    return True


def main(argv=None) -> int:
    from omaker.paths import default_checkpoint_path

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", default=None, help="onde gravar (padrão: caminho padrão do checkpoint)")
    dest = Path(ap.parse_args(argv).dest or default_checkpoint_path())
    os.environ.pop("OMAKER_NO_DOWNLOAD", None)   # pedido explícito: baixa mesmo com o automático desligado
    return 0 if ensure_pure_checkpoint(dest, print) else 1


if __name__ == "__main__":
    raise SystemExit(main())
