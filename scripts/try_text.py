"""Runs the real pipeline on a text and (for the bundled samples) scores it against a gold standard.

Run from the project root, with Ollama open:
    uv run python scripts/try_text.py --sample 1           # bundled sample 1 (default) + scoring
    uv run python scripts/try_text.py --sample 2           # held-out sample 2 + scoring
    uv run python scripts/try_text.py --file my_text.txt   # your own text (no scoring)
Env: OMAKER_ENTITIES=ner|llm|both   OMAKER_JAVA=<path to java.exe>
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omaker.evaluation.e2e import GOLD_SAMPLES, load_gold  # noqa: E402
from omaker.pipeline.engine import HybridEngine  # noqa: E402

# Gabarito (o que um anotador cuidadoso extrairia) e "armadilhas": omaker/evaluation/gold/samples.json.
SAMPLES = {i: dict(text=d.text, gold=set(d.triples), traps={(s, o): why for s, o, why in d.traps})
           for i, d in enumerate(load_gold(GOLD_SAMPLES), start=1)}


def same(a, b):
    """Tolerant match: 'diabetes' ~ 'type 2 diabetes'."""
    a, b = a.lower(), b.lower()
    return a == b or a in b or b in a


def matches(t, g):
    # triple layout: (subject, subject_type, relation, object, object_type, confidence)
    return same(t[0], g[0]) and t[2] == g[1] and same(t[3], g[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--sample", type=int, default=1, choices=sorted(SAMPLES))
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--out", default="try_text_result")
    args = ap.parse_args()

    sample = SAMPLES[args.sample] if args.file is None else None
    text = sample["text"] if sample else open(args.file, encoding="utf-8").read().strip()

    def log(m):
        print(m)

    taxonomy, triples = HybridEngine.extrair(text, args.model, 0.1, log)

    print("\n================ RESULT ================")
    print(f"Entities ({len(taxonomy['instances'])}):")
    for name, cls in taxonomy["instances"].items():
        print(f"  {name:28s} -> {cls}")
    print(f"\nExtra classes: {taxonomy['classes'] or '(none)'}")
    print(f"\nTriples ({len(triples)}):")
    for s, _, r, o, _, conf in triples:
        print(f"  {s} --[{r}]--> {o}   ({'LLM' if conf is None else f'{conf:.0%}'})")

    if sample:
        gold, traps = sample["gold"], sample["traps"]
        def is_trap(t):
            return next((why for (s, o), why in traps.items() if same(t[0], s) and same(t[3], o)), None)

        found = list(triples)
        hit = {g for g in gold if any(matches(t, g) for t in found)}
        tp = [t for t in found if any(matches(t, g) for g in gold)]
        precision = len(tp) / len(found) if found else 0.0
        print("\n================ SCORE ================")
        print(f"Recall    {len(hit)}/{len(gold)} = {len(hit) / len(gold):.0%}")
        print(f"Precision {len(tp)}/{len(found)} = {precision:.0%}")
        for g in sorted(gold - hit):
            print(f"  MISSED   {g}")
        for t in found:
            if t in tp:
                continue
            why = is_trap(t)
            print(f"  {'TRAP ' if why else 'EXTRA'}    {t[0]} --[{t[2]}]--> {t[3]}   ({why or 'not in gold: check by hand'})")

    print()
    HybridEngine.construir(taxonomy, triples, args.out, ".", "http://omaker.org/onto/", log)


if __name__ == "__main__":
    main()
