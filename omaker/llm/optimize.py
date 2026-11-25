"""Otimização do prompt de classificação de relações do LLM com DSPy (experimento opcional e reproduzível).

    uv sync --extra dev --extra dspy
    uv run python -m omaker.llm.optimize --splits data/biored/splits
    uv run python -m omaker.llm.optimize --resume runs/<pasta> [--install]

O DSPy é um extra opcional e só este módulo o importa: o pipeline lê o prompt exportado (JSON simples) sem ele.

Protocolo:
- uma chamada ao LLM por par (frase, sujeito com tipo, objeto com tipo), resposta treats, causes, prevents ou
  no_relation; temperatura 0 e semente fixa;
- baseline: a instrução escrita à mão (RELATION_INSTRUCTION, o RELATION_SYSTEM sem o pedido de JSON, porque o
  formato da resposta é do DSPy), sem exemplos;
- otimização: o otimizador do DSPy escolhe os exemplos few-shot (e, com MIPROv2, a instrução) a partir de um
  trainset sorteado do treino (semente fixa), pontuando os candidatos na validação (dev) pela acurácia por par;
- o teste é avaliado uma única vez, na etapa final, para o baseline e para o otimizado;
- métricas: micro-F1 sem no_relation (omaker.evaluation.metrics.classification_prf), macro-F1 e F1 por classe.

Retomada: o cache em disco do DSPy fica em runs/<pasta>/cache (chamadas já feitas não são refeitas) e cada etapa
pronta (baseline_dev, optimize, final) fica em runs/<pasta>/state.json; --resume pula as etapas prontas.

Ressalva: o pipeline manda lotes de 15 pares por pedido, com saída JSON; aqui cada pedido tem um par.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

try:
    import dspy
except ImportError as err:  # extra opcional
    raise ImportError("O DSPy é opcional: instale com `uv sync --extra dev --extra dspy`.") from err
from dspy.utils.exceptions import AdapterParseError

from omaker.config import ollama_host
from omaker.domain.labels import NO_RELATION
from omaker.evaluation.metrics import classification_prf
from omaker.llm.relations import OPTIMIZED_PROMPT, RELATION_INSTRUCTION, RELATIONS
from omaker.paths import project_root
from omaker.relations.data import PARTS, load_splits, sha256_of

FIELDS = ("sentence", "subject", "subject_type", "object", "object_type")
LABELS = (*RELATIONS, NO_RELATION)
PROMPT_FORMAT = 1
INSTALLED_PROMPT = OPTIMIZED_PROMPT
EVAL_SEED = 0
OPTIMIZERS = ("bootstrap", "mipro")
DEFAULTS = {
    "splits": str(project_root() / "data" / "biored" / "splits"),
    "model": "qwen3:8b-q4_K_M",
    "host": None,          # None: OLLAMA_HOST
    "optimizer": "bootstrap",
    "train_size": 60,
    "seed": 0,
    "limit": None,         # None: dev e teste inteiros
    "demos": 4,
    "labeled": 4,
    "candidates": 8,
    "threads": 1,
}
# Retomar só faz sentido se o que define o resultado não mudou (host e threads podem mudar).
RESUME_MUST_MATCH = ("splits", "model", "optimizer", "train_size", "seed", "limit", "demos", "labeled", "candidates")


class RelationPair(dspy.Signature):
    """Classify the relation between the subject and the object in the sentence."""

    sentence: str = dspy.InputField()
    subject: str = dspy.InputField()
    subject_type: str = dspy.InputField()
    object: str = dspy.InputField()
    object_type: str = dspy.InputField()
    relation: Literal[LABELS] = dspy.OutputField()


def make_lm(model: str, host: str | None = None):
    """LM do DSPy no Ollama local (API compatível com a da OpenAI), sem o raciocínio do qwen3."""
    base = ollama_host({"OLLAMA_HOST": host} if host else None).rstrip("/")
    return dspy.LM(f"ollama_chat/{model}", api_base=f"{base}/v1", temperature=0.0, max_tokens=1024,
                   reasoning_effort="none",   # o Ollama traduz para think=false
                   seed=EVAL_SEED, cache=True)


def to_example(e) -> dspy.Example:
    return dspy.Example(sentence=e.text.strip(), subject=e.sub_name, subject_type=e.sub_type, object=e.obj_name,
                        object_type=e.obj_type, relation=e.relation).with_inputs(*FIELDS)


def build_program(instruction: str, examples: list[dict]) -> dspy.Predict:
    """Programa de um par a partir da instrução e dos exemplos few-shot (o formato do JSON exportado)."""
    program = dspy.Predict(RelationPair.with_instructions(instruction))
    program.demos = [dspy.Example(**{k: e[k] for k in (*FIELDS, "relation")}).with_inputs(*FIELDS)
                     for e in examples]
    return program


def export_prompt(program) -> dict:
    """Instrução e exemplos como texto (sem pickle do DSPy): é o que classify_pairs lê."""
    predictor = program.predictors()[0]
    keys = (*FIELDS, "relation")
    examples = [{k: str(d[k]) for k in keys} for d in predictor.demos if all(k in d for k in keys)]
    return {"format": PROMPT_FORMAT, "instruction": predictor.signature.instructions, "examples": examples}


def accuracy(example, prediction, trace=None) -> float:
    return float(getattr(prediction, "relation", None) == example.relation)


def evaluate(program, examples) -> dict:
    """Prevê cada par e mede; resposta ilegível conta como no_relation (e entra em `errors`).

    Falhas do LM (Ollama fora do ar) não são engolidas: a execução para e a retomada continua dali.
    """
    preds, errors = [], 0
    for e in examples:
        ex = to_example(e)
        try:
            rel = program(**ex.inputs()).relation
        except AdapterParseError:
            rel, errors = NO_RELATION, errors + 1
        preds.append(rel if rel in LABELS else NO_RELATION)
    scores = classification_prf([e.relation for e in examples], preds)
    return {"n": len(examples), "errors": errors, "micro": asdict(scores["micro"]), "macro_f1": scores["macro_f1"],
            "per_class": {k: asdict(v) for k, v in scores["per_class"].items()}, "predictions": preds}


def make_optimizer(name: str, metric, demos: int, labeled: int, candidates: int, threads: int, seed: int = 0,
                   max_errors: int = 10):
    if name == "bootstrap":
        return dspy.BootstrapFewShotWithRandomSearch(
            metric=metric, max_bootstrapped_demos=demos, max_labeled_demos=labeled,
            num_candidate_programs=candidates, num_threads=threads, max_errors=max_errors)
    if name == "mipro":   # com auto="light" o próprio MIPROv2 decide quantos candidatos testar
        return dspy.MIPROv2(metric=metric, auto="light", max_bootstrapped_demos=demos, max_labeled_demos=labeled,
                            num_threads=threads, seed=seed, max_errors=max_errors)
    raise ValueError(f"otimizador desconhecido: {name} (use {', '.join(OPTIMIZERS)})")


def sample(items: list, n: int | None, seed: int) -> list:
    """n itens sorteados com a semente, na ordem original (todos se n for None ou maior que a lista)."""
    if n is None or n >= len(items):
        return list(items)
    return [items[i] for i in sorted(random.Random(seed).sample(range(len(items)), n))]


def _splits_sha256(directory) -> dict:
    return {p: sha256_of(Path(directory) / f"{p}.json") for p in PARTS}


def _write_json(path: Path, data) -> None:
    tmp = path.with_suffix(".part")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def _without_predictions(result: dict) -> dict:
    return {k: v for k, v in result.items() if k != "predictions"}


def _metrics(state: dict) -> dict:
    steps = state["steps"]
    return {
        "metadata": state["metadata"],
        "baseline": {"dev": _without_predictions(steps["baseline_dev"]),
                     "test": _without_predictions(steps["final"]["baseline_test"])},
        "optimized": {"dev": _without_predictions(steps["optimize"]["dev"]),
                      "test": _without_predictions(steps["final"]["optimized_test"])},
        "prompt": steps["optimize"]["prompt"],
    }


def _row(name: str, r: dict) -> str:
    m = r["micro"]
    per_class = " | ".join(f"{r['per_class'][lab]['f1']:.3f}" if lab in r["per_class"] else "-" for lab in RELATIONS)
    return (f"| {name} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {r['macro_f1']:.3f} "
            f"| {per_class} | {r['errors']} |")


def _report(metrics: dict) -> str:
    md, prompt = metrics["metadata"], metrics["prompt"]
    header = ["| Prompt | P | R | micro-F1 | macro-F1 | " + " | ".join(f"F1 {lab}" for lab in RELATIONS) + " | Erros |",
              "|---|---|---|---|---|" + "---|" * len(RELATIONS) + "---|"]
    lines = [f"# {md['created'][:10]}: otimização do prompt de relações com DSPy", "",
             f"Modelo: `{md['model']}`. Otimizador: `{md['optimizer']}`. Dados: `{md['splits']}`.",
             f"Treino amostrado: {md['n_train']} pares (semente {md['seed']}). Validação: {md['n_dev']} pares. "
             f"Teste: {md['n_test']} pares.",
             f"Prompt otimizado: {len(prompt['examples'])} exemplo(s) few-shot.", ""]
    for title, part in (("Validação (dev)", "dev"), ("Teste (avaliado uma única vez)", "test")):
        lines += [f"## {title}", "", *header, _row("Baseline", metrics["baseline"][part]),
                  _row("Otimizado", metrics["optimized"][part]), ""]
    lines += ["Notas:",
              "- micro-F1 sem `no_relation`; Erros: respostas ilegíveis, contadas como `no_relation`.",
              "- O otimizado foi escolhido na validação: o F1 dele em dev é otimista; o teste é a medida honesta.",
              "- Aqui cada pedido tem um par; o pipeline manda lotes de 15 pares por pedido, com saída JSON.",
              "", "## Instrução otimizada", "", "```text", prompt["instruction"], "```", ""]
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    s = argparse.SUPPRESS   # opção não dada fica fora de args: na retomada vale a da execução gravada
    ap = argparse.ArgumentParser(description="Otimiza o prompt de relações do LLM com DSPy (Ollama local).")
    ap.add_argument("--splits", default=s, help="pasta com train/dev/test.json (padrão: data/biored/splits)")
    ap.add_argument("--model", default=s, help=f"modelo do Ollama (padrão: {DEFAULTS['model']})")
    ap.add_argument("--host", default=s, help="endereço do Ollama (padrão: OLLAMA_HOST)")
    ap.add_argument("--optimizer", default=s, choices=OPTIMIZERS,
                    help="bootstrap: BootstrapFewShotWithRandomSearch (padrão); mipro: MIPROv2 auto=light")
    ap.add_argument("--train-size", type=int, default=s, help="pares sorteados do treino (padrão: 60)")
    ap.add_argument("--seed", type=int, default=s, help="semente do sorteio (padrão: 0)")
    ap.add_argument("--limit", type=int, default=s, help="usa só N pares sorteados de dev e de teste (fumaça)")
    ap.add_argument("--demos", type=int, default=s, help="máximo de exemplos gerados pelo LLM (padrão: 4)")
    ap.add_argument("--labeled", type=int, default=s, help="máximo de exemplos rotulados do treino (padrão: 4)")
    ap.add_argument("--candidates", type=int, default=s, help="programas candidatos do bootstrap (padrão: 8)")
    ap.add_argument("--threads", type=int, default=s, help="chamadas em paralelo no otimizador (padrão: 1)")
    ap.add_argument("--runs-dir", default=str(project_root() / "runs"))
    ap.add_argument("--resume", metavar="PASTA_DO_RUN", help="continua uma execução interrompida (runs/<pasta>)")
    ap.add_argument("--install", action="store_true",
                    help="copia o prompt otimizado para omaker/llm/prompts/relations_optimized.json")
    return ap


def _new_run(runs_dir) -> Path:
    stem = Path(runs_dir) / f"{datetime.now():%Y%m%d-%H%M%S}-dspy"
    run, k = stem, 2
    while run.exists():
        run, k = Path(f"{stem}-{k}"), k + 1
    run.mkdir(parents=True)
    return run


def _load_state(args) -> tuple[Path, dict]:
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
        state["metadata"] = {**saved, **{k: given[k] for k in ("host", "threads") if k in given}}
        return run, state
    from omaker.evaluation.e2e import _commit

    settings = {**DEFAULTS, **given}
    settings["splits"] = str(Path(settings["splits"]))
    metadata = {**settings, "splits_sha256": _splits_sha256(settings["splits"]), "commit": _commit(),
                "dspy_version": dspy.__version__, "created": datetime.now().isoformat(timespec="seconds")}
    run = _new_run(args.runs_dir)
    state = {"metadata": metadata, "steps": {}}
    _write_json(run / "state.json", state)   # já no início: uma queda na primeira etapa ainda deixa o que retomar
    return run, state


def main(argv=None, lm=None) -> Path:
    """Roda (ou retoma) as etapas; `lm` substitui o Ollama (testes)."""
    args = _parser().parse_args(argv)
    run, state = _load_state(args)
    md, steps = state["metadata"], state["steps"]
    splits = load_splits(md["splits"])
    train = sample(splits.train, md["train_size"], md["seed"])
    dev = sample(splits.dev, md["limit"], md["seed"])
    test = sample(splits.test, md["limit"], md["seed"])
    md.update(n_train=len(train), n_dev=len(dev), n_test=len(test))
    if lm is None:
        from omaker.llm.client import OllamaClient

        OllamaClient(md["model"], md["host"]).check()   # falha já se o Ollama ou o modelo faltar
        dspy.configure_cache(enable_disk_cache=True, enable_memory_cache=True, disk_cache_dir=str(run / "cache"))
        lm = make_lm(md["model"], md["host"])

    def save():
        _write_json(run / "state.json", state)

    baseline = build_program(RELATION_INSTRUCTION, [])
    with dspy.context(lm=lm):
        if "baseline_dev" in steps:
            print("baseline_dev: já feito, pulando.")
        else:
            print(f"baseline_dev: avaliando o prompt atual em {len(dev)} pares de validação...", flush=True)
            steps["baseline_dev"] = evaluate(baseline, dev)
            save()
        if "optimize" in steps:
            print("optimize: já feito, pulando.")
        else:
            print(f"optimize: {md['optimizer']} com {len(train)} pares de treino, escolha em {len(dev)} de "
                  f"validação (muitas chamadas ao LLM)...", flush=True)
            optimizer = make_optimizer(md["optimizer"], accuracy, md["demos"], md["labeled"], md["candidates"],
                                       md["threads"], md["seed"], max_errors=max(10, (len(train) + len(dev)) // 10))
            compiled = optimizer.compile(build_program(RELATION_INSTRUCTION, []),
                                         trainset=[to_example(e) for e in train],
                                         valset=[to_example(e) for e in dev])
            prompt = export_prompt(compiled)
            # Avaliado como será usado: reconstruído do JSON exportado.
            steps["optimize"] = {"prompt": prompt,
                                 "dev": evaluate(build_program(prompt["instruction"], prompt["examples"]), dev)}
            save()
        prompt = steps["optimize"]["prompt"]
        _write_json(run / "relations_prompt.json", prompt)
        if "final" in steps:
            print("final: já feito, pulando.")
        else:
            print(f"final: baseline e otimizado no teste ({len(test)} pares, uma única vez)...", flush=True)
            optimized = build_program(prompt["instruction"], prompt["examples"])
            steps["final"] = {"baseline_test": evaluate(baseline, test), "optimized_test": evaluate(optimized, test)}
            save()
    metrics = _metrics(state)
    _write_json(run / "metrics.json", metrics)
    (run / "report.md").write_text(_report(metrics), encoding="utf-8")
    print((run / "report.md").read_text(encoding="utf-8"))
    if args.install:
        INSTALLED_PROMPT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(run / "relations_prompt.json", INSTALLED_PROMPT)
        print(f"Prompt instalado em {INSTALLED_PROMPT}; use com OMAKER_LLM_PROMPT=optimized.")
    print(f"Resultados em {run}")
    return run


if __name__ == "__main__":
    main()
