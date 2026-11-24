"""Prepara o checkpoint de um treino para publicação numa Release do GitHub.

    uv run python -m omaker.relations.release --run runs/<pasta> --out dist/modelo

Grava omaker_pure.pt, omaker_pure.calibration.json (se o treino foi calibrado) e SHA256SUMS. O checkpoint
publicado não leva as frases de treino (texto de resumos do PubMed): leva só os hashes delas, que bastam
para a verificação de contaminação da avaliação de ponta a ponta.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

import torch

from omaker.relations.calibration import sidecar_path
from omaker.relations.data import text_fingerprint

NAME = "omaker_pure"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(run, out) -> dict:
    run, out = Path(run), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ckpt = torch.load(run / "model.pt", map_location="cpu", weights_only=True)
    texts = ckpt.pop("train_texts", None)
    if texts is not None:
        ckpt["train_text_hashes"] = sorted({text_fingerprint(t) for t in texts})
    target = out / f"{NAME}.pt"
    torch.save(ckpt, target)
    files = [target]
    calibration = sidecar_path(run / "model.pt")
    if calibration.is_file():
        files.append(Path(shutil.copyfile(calibration, out / f"{NAME}.calibration.json")))
    sums = {f.name: _sha256(f) for f in files}
    (out / "SHA256SUMS").write_text("".join(f"{h}  {n}\n" for n, h in sums.items()), encoding="utf-8")
    return {"checkpoint": target, "sha256": sums[target.name], "files": sums}


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="pasta do treino (runs/<pasta>) com model.pt")
    ap.add_argument("--out", required=True, help="pasta de saída dos arquivos da Release")
    args = ap.parse_args(argv)
    result = export(args.run, args.out)
    for name, digest in result["files"].items():
        print(f"{digest}  {name}")
    return result


if __name__ == "__main__":
    main()
