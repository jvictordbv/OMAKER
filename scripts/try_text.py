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

from omaker.pipeline.engine import HybridEngine  # noqa: E402

HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests")  # sample texts

# What a careful human annotator would extract. (sub, relation, obj); names matched loosely.
SAMPLES = {
    1: dict(
        file="sample_text.txt",
        gold={
            ("metformin", "treats", "type 2 diabetes"),
            ("metformin", "causes", "vitamin b12 deficiency"),
            ("aspirin", "prevents", "myocardial infarction"),
            ("aspirin", "causes", "gastric bleeding"),
            ("paracetamol", "treats", "fever"),
            ("alcohol", "causes", "liver cirrhosis"),
            ("statins", "prevents", "stroke"),
        },
        # (subject, object): ANY relation between them is wrong, because the text does not state one.
        traps={
            ("ibuprofen", "headache"): "negated: 'did not relieve'",
            ("paracetamol", "cough"): "only co-mentioned",
            ("aspirin", "cardiovascular disease"): "only 'patients with' the disease",
            ("statins", "cholesterol"): "lowers a lab value; cholesterol is not a disease",
        },
    ),
    2: dict(  # held-out text: written before looking at any result on it
        file="sample_text_2.txt",
        gold={
            ("warfarin", "prevents", "stroke"),
            ("warfarin", "causes", "bleeding"),
            ("oseltamivir", "treats", "influenza"),
            ("salbutamol", "treats", "wheezing"),
            ("bcg", "prevents", "tuberculosis"),
        },
        traps={
            ("warfarin", "atrial fibrillation"): "only 'patients with' the disease",
            ("amoxicillin", "headache"): "only temporal ('after starting')",
            ("amoxicillin", "nausea"): "only temporal ('after starting')",
            ("insulin", "fatigue"): "negated: 'was not effective'",
        },
    ),
}


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
    path = args.file or os.path.join(HERE, sample["file"])
    text = open(path, encoding="utf-8").read().strip()

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
