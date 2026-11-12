"""Leitor do BioRED (Luo et al., 2022) para o esquema do OMAKER (decisão D5).

O BioRED anota relações por documento, entre conceitos (ids), sem direção. O PURE classifica pares dentro
de uma frase. A conversão:

- tipos: ChemicalEntity vira DRUG, DiseaseOrPhenotypicFeature vira DISEASE; os demais ficam de fora;
- rótulos: Positive_Correlation vira causes, Negative_Correlation vira treats; o sujeito é sempre o químico;
- cada par (id químico, id doença) presente na mesma frase gera um exemplo, com a primeira menção de cada id;
- par com relação de outro tipo (Association e afins) é descartado; par sem relação vira no_relation.

Limitação: o rótulo vem do documento, então uma frase pode citar os dois sem afirmar a relação.

Uso:
    uv run python -m omaker.relations.biored --download [--review-sample 100]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import random
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import requests

from omaker.domain.labels import NO_RELATION
from omaker.domain.text import split_sentences
from omaker.paths import project_root
from omaker.relations.data import PARTS, RelationExample, Splits, save_splits

BIORED_URL = "https://ftp.ncbi.nlm.nih.gov/pub/lu/BioRED/BIORED.zip"
OFFICIAL_FILES = {"train": "Train.PubTator", "dev": "Dev.PubTator", "test": "Test.PubTator"}
TYPE_MAP = {"ChemicalEntity": "DRUG", "DiseaseOrPhenotypicFeature": "DISEASE"}
LABEL_MAP = {"Positive_Correlation": "causes", "Negative_Correlation": "treats"}


@dataclass(frozen=True)
class Mention:
    start: int
    end: int
    text: str
    type: str
    ids: tuple[str, ...]


@dataclass(frozen=True)
class Document:
    pmid: str
    text: str
    mentions: tuple[Mention, ...]
    relations: tuple[tuple[str, str, str], ...]   # (tipo, id1, id2)


def parse_pubtator(content: str) -> list[Document]:
    docs: dict[str, dict] = {}
    for line in content.splitlines():
        if not line.strip():
            continue
        head = line[:30]
        if "|t|" in head or "|a|" in head:
            pmid, kind, body = line.split("|", 2)
            docs.setdefault(pmid, {"t": "", "a": "", "m": [], "r": []})[kind] = body
            continue
        fields = line.split("\t")
        doc = docs.setdefault(fields[0], {"t": "", "a": "", "m": [], "r": []})
        if len(fields) == 6:
            doc["m"].append(fields)
        elif len(fields) == 5:
            doc["r"].append((fields[1], fields[2], fields[3]))
        else:
            raise ValueError(f"PMID {fields[0]}: linha com {len(fields)} campos: {line[:80]!r}")

    out = []
    for pmid, d in docs.items():
        text = d["t"] + " " + d["a"]
        mentions = []
        for _, s, e, mtext, mtype, ids in d["m"]:
            start, end = int(s), int(e)
            if text[start:end] != mtext:
                raise ValueError(f"PMID {pmid}: offsets {start}-{end} não batem com '{mtext}'")
            mentions.append(Mention(start, end, mtext, mtype, tuple(i.strip() for i in ids.split(","))))
        out.append(Document(pmid, text, tuple(mentions), tuple(d["r"])))
    return out


def _pair_labels(doc: Document) -> dict[frozenset, str | None]:
    """Rótulo do OMAKER por par de ids; None quando a relação existe mas não é mapeada."""
    labels: dict[frozenset, str | None] = {}
    for rtype, a, b in doc.relations:
        key = frozenset((a, b))
        mapped = LABEL_MAP.get(rtype)
        if key in labels and labels[key] != mapped:
            labels[key] = None   # tipos conflitantes para o mesmo par: descarta
        else:
            labels[key] = mapped
    return labels


def document_examples(doc: Document) -> list[RelationExample]:
    labels = _pair_labels(doc)
    examples = []
    for s0, s1 in split_sentences(doc.text):
        first: dict[str, dict[str, Mention]] = {"DRUG": {}, "DISEASE": {}}
        for m in sorted(doc.mentions, key=lambda m: m.start):
            etype = TYPE_MAP.get(m.type)
            if etype is None or m.start < s0 or m.end > s1:
                continue
            for i in m.ids:
                first[etype].setdefault(i, m)
        sentence = doc.text[s0:s1]
        for chem_id, chem in first["DRUG"].items():
            for dis_id, dis in first["DISEASE"].items():
                if chem is dis or (chem.start < dis.end and dis.start < chem.end):
                    continue
                key = frozenset((chem_id, dis_id))
                if key in labels and labels[key] is None:
                    continue
                relation = labels.get(key) or NO_RELATION
                examples.append(RelationExample(
                    sentence, chem.text, "DRUG", dis.text, "DISEASE", relation,
                    sub_span=(chem.start - s0, chem.end - s0), obj_span=(dis.start - s0, dis.end - s0)))
    return _dedupe(examples)


def _dedupe(examples: list[RelationExample]) -> list[RelationExample]:
    """Uma menção com vários ids pode repetir o mesmo par de spans; fica o primeiro rótulo positivo."""
    best: dict[tuple, RelationExample] = {}
    for e in examples:
        key = (e.text, e.sub_span, e.obj_span)
        if key not in best or (best[key].relation == NO_RELATION and e.relation != NO_RELATION):
            best[key] = e
    return list(best.values())


def load_biored(directory) -> Splits:
    directory = Path(directory)
    digest = hashlib.sha256()
    parts = {}
    for part in PARTS:
        path = directory / OFFICIAL_FILES[part]
        if not path.exists():
            raise FileNotFoundError(f"{path} não existe. Baixe com: uv run python -m omaker.relations.biored "
                                    f"--download")
        content = path.read_bytes()
        digest.update(content)
        parts[part] = [e for doc in parse_pubtator(content.decode("utf-8")) for e in document_examples(doc)]
    manifest = {
        "seed": None,
        "fractions": None,
        "source_sha256": digest.hexdigest(),
        "stratified": False,
        "official_split": True,
        "source": "BioRED",
        "mapping": dict(LABEL_MAP),
        "types": dict(TYPE_MAP),
        "counts": {p: dict(sorted(Counter(e.relation for e in parts[p]).items())) for p in PARTS},
    }
    return Splits(parts["train"], parts["dev"], parts["test"], manifest)


# ----------------------------------------------------------------------------- download e linha de comando
def _fetch(url: str, target: Path) -> None:
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(target, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


def _extract(zip_path: Path, dest: Path) -> None:
    """Extrai só os três PubTator, pelo nome do arquivo (nunca pelo caminho guardado no zip)."""
    wanted = set(OFFICIAL_FILES.values())
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = Path(info.filename).name
            if name in wanted:
                tmp = dest / (name + ".part")
                tmp.write_bytes(zf.read(info))
                tmp.replace(dest / name)


def download(dest, url: str = BIORED_URL, fetch=_fetch) -> Path:
    """Baixa e extrai o BioRED em dest. Retomável: pula o que já existe; um download parcial não conta."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if all((dest / f).exists() for f in OFFICIAL_FILES.values()):
        return dest
    zip_path = dest / "BIORED.zip"
    if zip_path.exists() and not zipfile.is_zipfile(zip_path):
        zip_path.unlink()
    if not zip_path.exists():
        part = dest / "BIORED.zip.part"
        try:
            fetch(url, part)
        except BaseException:
            part.unlink(missing_ok=True)
            raise
        part.replace(zip_path)
    _extract(zip_path, dest)
    return dest


def write_review_sample(examples, path, n: int = 100, seed: int = 42) -> Path:
    """CSV para conferir o mapeamento à mão: a mesma quantidade de exemplos de cada rótulo."""
    by_label: dict[str, list[RelationExample]] = defaultdict(list)
    for e in examples:
        by_label[e.relation].append(e)
    rng = random.Random(seed)
    labels = sorted(by_label)
    picked: list[RelationExample] = []
    for i, label in enumerate(labels):
        quota = n // len(labels) + (1 if i < n % len(labels) else 0)
        pool = list(by_label[label])
        rng.shuffle(pool)
        picked.extend(pool[:quota])
    rng.shuffle(picked)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frase", "quimico", "doenca", "rotulo", "correto", "observacao"])
        for e in picked:
            w.writerow([e.text, e.sub_name, e.obj_name, e.relation, "", ""])
    return path


def main(argv=None) -> Path:
    default_dest = project_root() / "data" / "biored"
    ap = argparse.ArgumentParser(description="Converte o BioRED para o esquema do OMAKER.")
    ap.add_argument("--dest", default=str(default_dest), help="pasta com os arquivos PubTator")
    ap.add_argument("--out", default="", help="pasta da divisão gerada (padrão: <dest>/splits)")
    ap.add_argument("--download", action="store_true", help=f"baixa {BIORED_URL} se ainda não estiver em --dest")
    ap.add_argument("--review-sample", type=int, default=0, help="grava N exemplos do treino para conferência")
    args = ap.parse_args(argv)

    dest = Path(args.dest)
    if args.download:
        download(dest)
    splits = load_biored(dest)
    out = save_splits(splits, Path(args.out) if args.out else dest / "splits")
    if args.review_sample:
        write_review_sample(splits.train, out / "revisao_mapeamento.csv", n=args.review_sample)
    print(f"Divisão gravada em {out}: {splits.manifest['counts']}")
    return out


if __name__ == "__main__":
    main()
