"""Mede um NER contra as menções de químicos e doenças anotadas no teste do BioRED.

    uv run python -m omaker.evaluation.ner_biored                  # NER do OMAKER (OMAKER_NER_MODEL, padrão d4data)
    uv run python -m omaker.evaluation.ner_biored --ner bc5cdr     # NER do OMAKER com o BC5CDR e a tipagem de sintomas
    uv run python -m omaker.evaluation.ner_biored --model judithrosell/BC5CDR_PubMedBERT_NER   # modelo cru

Gabarito: as menções ChemicalEntity e DiseaseOrPhenotypicFeature dos resumos de teste. Uma menção prevista
acerta só se o início e o fim baterem exatamente (depois de estender o trecho até a palavra inteira, como o
OMAKER faz). O total é um micro-F1 sobre todas as menções e ignora o tipo; por tipo, o tipo também precisa bater.
Tipos do OMAKER: DRUG conta como químico; DISEASE e SYMPTOM, como doença (o BioRED não separa sintoma).
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from omaker.config import NER_MODELS
from omaker.evaluation.metrics import _prf
from omaker.paths import project_root

GOLD_TYPES = {"ChemicalEntity": "Chemical", "DiseaseOrPhenotypicFeature": "Disease"}
OMAKER_TYPES = {"DRUG": "Chemical", "DISEASE": "Disease", "SYMPTOM": "Disease"}
TYPES = ("Chemical", "Disease")


def gold_mentions(docs) -> set[tuple]:
    """{(pmid, início, fim, tipo)} das menções de químicos e doenças."""
    return {(d.pmid, m.start, m.end, GOLD_TYPES[m.type]) for d in docs for m in d.mentions if m.type in GOLD_TYPES}


def snap(text: str, start: int, end: int) -> tuple[int, int]:
    """Estende o trecho até a palavra inteira ("T syndrome" vira "QT syndrome")."""
    while start > 0 and text[start - 1].isalnum():
        start -= 1
    while end < len(text) and text[end].isalnum():
        end += 1
    return start, end


def hf_type(label: str) -> str | None:
    """Rótulo de um NER do Hugging Face treinado no BC5CDR (Chemical/Disease, com ou sem B-/I-)."""
    label = label.lower().removeprefix("b-").removeprefix("i-")
    return {"chemical": "Chemical", "disease": "Disease"}.get(label)


def _spans(items) -> set[tuple]:
    return {i[:3] for i in items}   # (pmid, início, fim), sem o tipo


def evaluate(docs, extract) -> dict:
    """extract(texto) devolve [(início, fim, tipo)], com tipo em TYPES ou None."""
    gold = gold_mentions(docs)
    pred = {(d.pmid, s, e, t) for d in docs for s, e, t in extract(d.text)}
    g, p = _spans(gold), _spans(pred)
    by_type = {}
    for t in TYPES:
        gt, pt = _spans(i for i in gold if i[3] == t), _spans(i for i in pred if i[3] == t)
        by_type[t] = asdict(_prf(len(gt & pt), len(pt - gt), len(gt - pt)))
    return {"gold": len(g), "predicted": len(p), "total": asdict(_prf(len(g & p), len(p - g), len(g - p))),
            "by_type": by_type}


def omaker_extractor(device: int = -1, model: str | None = None):
    """O NER do pipeline (omaker/nlp/ner.py), com o mesmo pós-processamento; model: d4data, bc5cdr ou
    None (OMAKER_NER_MODEL)."""
    from omaker.nlp.ner import BiomedicalNER

    ner = BiomedicalNER(model, device=device)
    return lambda text: [(e.start, e.end, OMAKER_TYPES.get(e.type)) for e in ner.extract(text)]


def hf_extractor(model: str, device: int = -1):
    """Um NER do Hugging Face com rótulos Chemical/Disease, frase a frase, com os trechos estendidos."""
    from transformers import pipeline

    from omaker.domain.text import split_sentences

    pipe = pipeline("token-classification", model=model, aggregation_strategy="simple", device=device)

    def extract(text):
        sents = split_sentences(text)
        out = []
        for (s0, s1), items in zip(sents, pipe([text[s:e] for s, e in sents], batch_size=8), strict=True):
            for it in items:
                s, e = snap(text[s0:s1], it["start"], it["end"])
                out.append((s0 + s, s0 + e, hf_type(it["entity_group"])))
        return out

    return extract


def report(name: str, r: dict) -> str:
    rows = [f"| total | {r['total']['precision']:.3f} | {r['total']['recall']:.3f} | {r['total']['f1']:.3f} |"]
    rows += [f"| {t} | {v['precision']:.3f} | {v['recall']:.3f} | {v['f1']:.3f} |" for t, v in r["by_type"].items()]
    return "\n".join([f"Modelo: `{name}`. Menções no gabarito: {r['gold']}; previstas: {r['predicted']}.", "",
                      "| Tipo | P | R | F1 |", "|---|---|---|---|", *rows])


def main(argv=None) -> dict:
    from omaker.relations.biored import parse_pubtator

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--biored", default=str(project_root() / "data" / "biored"),
                    help="pasta com Test.PubTator (padrão: data/biored)")
    which = ap.add_mutually_exclusive_group()
    which.add_argument("--model", default=None, help="NER do Hugging Face com rótulos Chemical/Disease "
                                                     "(padrão: o NER do OMAKER)")
    which.add_argument("--ner", choices=NER_MODELS, default=None,
                       help="NER do OMAKER a medir (padrão: OMAKER_NER_MODEL, ou d4data)")
    ap.add_argument("--device", type=int, default=-1, help="-1 para CPU, 0 para a primeira GPU")
    ap.add_argument("--out", default=None, help="grava o resultado em JSON")
    args = ap.parse_args(argv)

    docs = parse_pubtator((Path(args.biored) / "Test.PubTator").read_text(encoding="utf-8"))
    if args.model:
        name, extract = args.model, hf_extractor(args.model, args.device)
    else:
        from omaker.nlp.ner import ner_spec
        name, extract = f"{ner_spec(args.ner).name} (OMAKER)", omaker_extractor(args.device, args.ner)
    r = evaluate(docs, extract)
    print(report(name, r))
    if args.out:
        Path(args.out).write_text(json.dumps({"model": name, **r}, indent=1), encoding="utf-8")
    return r


if __name__ == "__main__":
    main()
