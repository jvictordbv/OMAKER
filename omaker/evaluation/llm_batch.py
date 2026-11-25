"""Mede o prompt de relações do LLM pelo caminho do pipeline: lotes de 15 pares por pedido, saída JSON.

A otimização (omaker.llm.optimize) mede um par por pedido; aqui os mesmos pares de validação e de teste do
BioRED passam por `classify_pairs`, como no pipeline quando não há checkpoint do PURE (débito DT-28).
Compara o prompt escrito à mão com o otimizado (omaker/llm/prompts/relations_optimized.json).

Cada lote respondido é gravado em state.json: se cair, `--resume runs/<pasta>` continua do lote seguinte.

    uv run python -m omaker.evaluation.llm_batch                 # dev e teste, os dois prompts
    uv run python -m omaker.evaluation.llm_batch --limit 30      # fumaça
    uv run python -m omaker.evaluation.llm_batch --resume runs/<pasta>
"""
from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from omaker.domain.labels import NO_RELATION
from omaker.evaluation.metrics import classification_prf
from omaker.llm.client import LLMError
from omaker.llm.relations import (
    OPTIMIZED_PROMPT,
    PAIR_BATCH,
    RELATION_SYSTEM,
    RELATIONS,
    classify_pairs,
    optimized_system,
)
from omaker.paths import project_root
from omaker.relations.data import PARTS, load_splits, sha256_of

PROMPTS = ("default", "optimized")
EVAL_PARTS = ("dev", "test")
DEFAULTS = {
    "splits": str(project_root() / "data" / "biored" / "splits"),
    "model": "qwen3:8b-q4_K_M",
    "host": None,          # None: OLLAMA_HOST
    "temperature": 0.0,
    "seed": 0,             # OMAKER_LLM_SEED durante a execução
    "limit": None,         # None: dev e teste inteiros
}
RESUME_MUST_MATCH = ("splits", "model", "temperature", "seed", "limit")


def sample(items: list, n: int | None, seed: int) -> list:
    """n itens sorteados com a semente, na ordem original (todos se n for None ou maior que a lista)."""
    if n is None or n >= len(items):
        return list(items)
    return [items[i] for i in sorted(random.Random(seed).sample(range(len(items)), n))]


def systems(prompt_file: Path | None = None) -> dict:
    """O texto de sistema de cada prompt, montado como no pipeline."""
    prompt_file = prompt_file or OPTIMIZED_PROMPT
    if not prompt_file.is_file():
        raise FileNotFoundError(f"{prompt_file} não existe: rode `python -m omaker.llm.optimize --install` antes.")
    optimized = json.loads(prompt_file.read_text(encoding="utf-8"))
    return {"default": RELATION_SYSTEM, "optimized": optimized_system(optimized)}


def batches(examples: list) -> list[list[dict]]:
    """Lotes de PAIR_BATCH pares consecutivos, no formato de par que o pipeline manda ao LLM."""
    pairs = [{k: getattr(e, k) for k in ("text", "sub_name", "sub_type", "obj_name", "obj_type")} for e in examples]
    return [pairs[i:i + PAIR_BATCH] for i in range(0, len(pairs), PAIR_BATCH)]


def classify_batch(client, batch: list[dict], system: str, temperature: float) -> dict:
    """Um pedido ao LLM; se falhar (JSON inválido, limite de tokens), o lote fica todo no_relation."""
    try:
        preds = [rel for rel, _ in classify_pairs(client, batch, temperature, lambda _msg: None, system=system)]
        return {"predictions": preds, "error": None}
    except LLMError as err:
        return {"predictions": [NO_RELATION] * len(batch), "error": str(err)[:300]}


def score(golds: list[str], done: list[dict]) -> dict:
    preds = [p for b in done for p in b["predictions"]]
    s = classification_prf(golds, preds)
    return {"n": len(golds), "failed_batches": sum(1 for b in done if b["error"]),
            "micro": asdict(s["micro"]), "macro_f1": s["macro_f1"],
            "per_class": {k: asdict(v) for k, v in s["per_class"].items()}}


def _write_json(path: Path, data) -> None:
    tmp = path.with_suffix(".part")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def _row(name: str, r: dict) -> str:
    m = r["micro"]
    per_class = " | ".join(f"{r['per_class'][lab]['f1']:.3f}" if lab in r["per_class"] else "-" for lab in RELATIONS)
    return (f"| {name} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {r['macro_f1']:.3f} "
            f"| {per_class} | {r['failed_batches']} |")


def report(state: dict, metrics: dict) -> str:
    md = state["metadata"]
    header = ["| Prompt | P | R | micro-F1 | macro-F1 | " + " | ".join(f"F1 {lab}" for lab in RELATIONS)
              + " | Lotes com falha |",
              "|---|---|---|---|---|" + "---|" * len(RELATIONS) + "---|"]
    names = {"default": "Escrito à mão", "optimized": "Otimizado"}
    lines = [f"# {md['created'][:10]}: prompt de relações medido em lotes de {PAIR_BATCH} pares (caminho do pipeline)",
             "", f"Modelo: `{md['model']}`. Temperatura {md['temperature']}, semente {md['seed']}. "
             f"Dados: `{md['splits']}`. Commit `{md['commit']}`.", ""]
    for part in EVAL_PARTS:
        lines += [f"## {'Validação' if part == 'dev' else 'Teste'} ({md['n_' + part]} pares)", "", *header,
                  *(_row(names[p], metrics[p][part]) for p in PROMPTS), ""]
    lines += ["Notas:",
              "- micro-F1 sem `no_relation`. Um lote com falha (JSON inválido ou limite de tokens) conta todo "
              "como `no_relation`.",
              f"- Lotes de {PAIR_BATCH} pares consecutivos, com o JSON de saída do pipeline (`classify_pairs`).", ""]
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    s = argparse.SUPPRESS   # opção não dada fica fora de args: na retomada vale a da execução gravada
    ap = argparse.ArgumentParser(description="Mede o prompt de relações do LLM em lotes, como no pipeline.")
    ap.add_argument("--splits", default=s, help="pasta com train/dev/test.json (padrão: data/biored/splits)")
    ap.add_argument("--model", default=s, help=f"modelo do Ollama (padrão: {DEFAULTS['model']})")
    ap.add_argument("--host", default=s, help="endereço do Ollama (padrão: OLLAMA_HOST)")
    ap.add_argument("--temperature", type=float, default=s, help="temperatura (padrão: 0.0)")
    ap.add_argument("--seed", type=int, default=s, help="semente do Ollama e do sorteio (padrão: 0)")
    ap.add_argument("--limit", type=int, default=s, help="usa só N pares sorteados de dev e de teste (fumaça)")
    ap.add_argument("--runs-dir", default=str(project_root() / "runs"))
    ap.add_argument("--resume", metavar="PASTA_DO_RUN", help="continua uma execução interrompida (runs/<pasta>)")
    return ap


def _splits_sha256(directory) -> dict:
    return {p: sha256_of(Path(directory) / f"{p}.json") for p in PARTS}


def _load_state(args, system_texts: dict) -> tuple[Path, dict]:
    given = {k: v for k, v in vars(args).items() if k in DEFAULTS}
    if args.resume:
        run = Path(args.resume)
        state = json.loads((run / "state.json").read_text(encoding="utf-8"))
        saved = state["metadata"]
        for key in RESUME_MUST_MATCH:
            if key in given and given[key] != saved[key]:
                raise ValueError(f"não dá para retomar {run}: '{key}' mudou ({saved[key]!r} para {given[key]!r})")
        if _splits_sha256(saved["splits"]) != saved["splits_sha256"]:
            raise ValueError(f"não dá para retomar {run}: os dados em {saved['splits']} mudaram")
        if state["systems"] != system_texts:
            raise ValueError(f"não dá para retomar {run}: o texto de um dos prompts mudou")
        if "host" in given:
            saved["host"] = given["host"]
        return run, state
    from omaker.evaluation.e2e import _commit

    settings = {**DEFAULTS, **given}
    settings["splits"] = str(Path(settings["splits"]))
    metadata = {**settings, "splits_sha256": _splits_sha256(settings["splits"]), "commit": _commit(),
                "created": datetime.now().isoformat(timespec="seconds")}
    run = Path(args.runs_dir) / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-llm-lotes")
    run.mkdir(parents=True, exist_ok=False)
    state = {"metadata": metadata, "systems": system_texts, "results": {}}
    _write_json(run / "state.json", state)
    return run, state


def main(argv=None, client=None) -> Path:
    """Roda (ou retoma) a medição; `client` substitui o Ollama (testes)."""
    args = _parser().parse_args(argv)
    system_texts = systems()
    run, state = _load_state(args, system_texts)
    md, results = state["metadata"], state["results"]
    splits = load_splits(md["splits"])
    data = {part: sample(getattr(splits, part), md["limit"], md["seed"]) for part in EVAL_PARTS}
    md.update({f"n_{part}": len(data[part]) for part in EVAL_PARTS})
    if client is None:
        from omaker.llm.client import OllamaClient

        client = OllamaClient(md["model"], md["host"])
        client.check()   # falha já se o Ollama ou o modelo faltar

    previous_seed = os.environ.get("OMAKER_LLM_SEED")
    os.environ["OMAKER_LLM_SEED"] = str(md["seed"])
    try:
        for part in EVAL_PARTS:
            part_batches = batches(data[part])
            for prompt in PROMPTS:
                done = results.setdefault(f"{prompt}/{part}", [])
                if len(done) == len(part_batches):
                    print(f"{prompt}/{part}: já feito, pulando.", flush=True)
                    continue
                print(f"{prompt}/{part}: lote {len(done) + 1} de {len(part_batches)}...", flush=True)
                for batch in part_batches[len(done):]:
                    done.append(classify_batch(client, batch, system_texts[prompt], md["temperature"]))
                    _write_json(run / "state.json", state)
                    if len(done) % 5 == 0 or len(done) == len(part_batches):
                        print(f"  {prompt}/{part}: {len(done)}/{len(part_batches)} lotes", flush=True)
    finally:
        if previous_seed is None:
            os.environ.pop("OMAKER_LLM_SEED", None)
        else:
            os.environ["OMAKER_LLM_SEED"] = previous_seed

    metrics = {p: {part: score([e.relation for e in data[part]], results[f"{p}/{part}"]) for part in EVAL_PARTS}
               for p in PROMPTS}
    _write_json(run / "metrics.json", {"metadata": md, **metrics})
    (run / "report.md").write_text(report(state, metrics), encoding="utf-8")
    print((run / "report.md").read_text(encoding="utf-8"))
    print(f"Resultados em {run}")
    return run


if __name__ == "__main__":
    main()
