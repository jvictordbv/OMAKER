"""Otimização do prompt de relações com DSPy, com um LM falso (sem Ollama e sem internet)."""
import json

import pytest

dspy = pytest.importorskip("dspy")

from dspy.utils import DummyLM  # noqa: E402

from omaker.llm import optimize as opt  # noqa: E402
from omaker.llm.relations import RELATION_INSTRUCTION  # noqa: E402
from omaker.relations.data import RelationExample, Splits, save_splits  # noqa: E402

GOLD = {}


def _examples(part: str, n: int) -> list[RelationExample]:
    out = []
    for i in range(n):
        rel = ("treats", "causes")[i % 2]
        text = f"Sentence {part}-{i:02d} about drug{part}{i} and disease{part}{i}."
        GOLD[text] = rel
        out.append(RelationExample(text, f"drug{part}{i}", "DRUG", f"disease{part}{i}", "DISEASE", rel))
    return out


@pytest.fixture
def splits_dir(tmp_path):
    splits = Splits(_examples("train", 6), _examples("dev", 4), _examples("test", 4), {"source": "teste"})
    return save_splits(splits, tmp_path / "splits")


class OracleLM(DummyLM):
    """Answers the gold relation only when the prompt carries demonstrations; without them, no_relation.

    So the zero-shot baseline scores 0 and any program with few-shot examples scores 1.
    """

    def __init__(self):
        super().__init__({}, follow_examples=True)
        self.calls = 0
        self.sentences = []

    def _use_example(self, messages):
        self.calls += 1
        sentence = next(s for s in GOLD if s in messages[-1]["content"])
        self.sentences.append(sentence)
        has_demos = any(s in m["content"] for m in messages[:-1] for s in GOLD)
        return self._format_answer_fields({"relation": GOLD[sentence] if has_demos else "no_relation"})


def _run(splits_dir, tmp_path, lm, *extra):
    argv = ["--splits", str(splits_dir), "--runs-dir", str(tmp_path / "runs"), "--train-size", "3",
            "--candidates", "1", "--demos", "2", "--labeled", "2", *extra]
    return opt.main(argv, lm=lm)


def test_baseline_program_uses_the_handwritten_instruction_without_examples():
    program = opt.build_program(RELATION_INSTRUCTION, [])
    assert program.signature.instructions == RELATION_INSTRUCTION
    assert program.demos == []
    assert opt.export_prompt(program) == {"format": 1, "instruction": RELATION_INSTRUCTION, "examples": []}


def test_export_prompt_is_plain_json_and_round_trips():
    demo = {"sentence": "Aspirin prevents stroke.", "subject": "Aspirin", "subject_type": "DRUG",
            "object": "stroke", "object_type": "DISEASE", "relation": "prevents"}
    program = opt.build_program("Classify.", [demo])
    exported = opt.export_prompt(program)
    assert exported == {"format": 1, "instruction": "Classify.", "examples": [demo]}
    assert json.loads(json.dumps(exported)) == exported
    assert opt.export_prompt(opt.build_program(exported["instruction"], exported["examples"])) == exported


def test_evaluate_scores_with_micro_f1_without_no_relation():
    examples = [RelationExample("A treats B here.", "A", "DRUG", "B", "DISEASE", "treats"),
                RelationExample("C and D were seen.", "C", "DRUG", "D", "DISEASE", "no_relation")]
    lm = DummyLM({"A treats B here.": {"relation": "treats"}, "C and D were seen.": {"relation": "treats"}})
    with dspy.context(lm=lm):
        result = opt.evaluate(opt.build_program(RELATION_INSTRUCTION, []), examples)
    assert result["n"] == 2 and result["errors"] == 0
    assert result["predictions"] == ["treats", "treats"]
    assert result["micro"]["tp"] == 1 and result["micro"]["fp"] == 1
    assert result["micro"]["f1"] == pytest.approx(2 / 3)
    assert result["per_class"]["treats"]["precision"] == 0.5


def test_unparseable_answer_counts_as_no_relation():
    examples = [RelationExample("E treats F.", "E", "DRUG", "F", "DISEASE", "treats")]
    with dspy.context(lm=DummyLM({"E treats F.": {"relation": "maybe"}})):
        result = opt.evaluate(opt.build_program(RELATION_INSTRUCTION, []), examples)
    assert result["predictions"] == ["no_relation"] and result["errors"] == 1


def test_full_run_writes_metrics_report_and_plain_prompt(splits_dir, tmp_path):
    lm = OracleLM()
    run = _run(splits_dir, tmp_path, lm)
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["baseline"]["dev"]["micro"]["f1"] == 0.0
    assert metrics["optimized"]["dev"]["micro"]["f1"] == 1.0
    assert metrics["optimized"]["test"]["micro"]["f1"] == 1.0
    assert metrics["baseline"]["test"]["n"] == 4
    prompt = json.loads((run / "relations_prompt.json").read_text(encoding="utf-8"))
    assert prompt["format"] == 1 and isinstance(prompt["instruction"], str) and prompt["examples"]
    for ex in prompt["examples"]:
        assert set(ex) == {"sentence", "subject", "subject_type", "object", "object_type", "relation"}
        assert "train-" in ex["sentence"]   # exemplos só do treino, nunca de dev ou teste
    report = (run / "report.md").read_text(encoding="utf-8")
    assert "Baseline" in report and "Otimizado" in report and "micro-F1" in report
    state = json.loads((run / "state.json").read_text(encoding="utf-8"))
    assert set(state["steps"]) == {"baseline_dev", "optimize", "final"}
    # o teste é avaliado uma vez, só na etapa final: 4 frases, baseline e otimizado
    assert sum("test-" in s for s in lm.sentences) == 8


def test_resume_skips_finished_steps(splits_dir, tmp_path):
    run = _run(splits_dir, tmp_path, OracleLM())
    before = (run / "metrics.json").read_text(encoding="utf-8")
    lm = OracleLM()
    assert opt.main(["--resume", str(run)], lm=lm) == run
    assert lm.calls == 0
    assert (run / "metrics.json").read_text(encoding="utf-8") == before


def test_resume_redoes_only_the_missing_step(splits_dir, tmp_path):
    run = _run(splits_dir, tmp_path, OracleLM())
    state_path = run / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    del state["steps"]["final"]
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (run / "metrics.json").unlink()
    lm = OracleLM()
    opt.main(["--resume", str(run)], lm=lm)
    assert lm.calls == 8   # só o teste, com o programa otimizado reconstruído do JSON
    assert all("test-" in s for s in lm.sentences)
    assert json.loads((run / "metrics.json").read_text(encoding="utf-8"))["optimized"]["test"]["micro"]["f1"] == 1.0


def test_resume_refuses_changed_settings(splits_dir, tmp_path):
    run = _run(splits_dir, tmp_path, OracleLM())
    with pytest.raises(ValueError, match="model"):
        opt.main(["--resume", str(run), "--model", "outro:modelo"], lm=OracleLM())


def test_install_copies_the_prompt(splits_dir, tmp_path, monkeypatch):
    target = tmp_path / "pkg" / "prompts" / "relations_optimized.json"
    monkeypatch.setattr(opt, "INSTALLED_PROMPT", target)
    run = _run(splits_dir, tmp_path, OracleLM(), "--install")
    assert json.loads(target.read_text(encoding="utf-8")) == json.loads(
        (run / "relations_prompt.json").read_text(encoding="utf-8"))


def test_installed_prompt_is_what_classify_pairs_reads():
    from omaker.llm import relations

    assert opt.INSTALLED_PROMPT == relations.OPTIMIZED_PROMPT


def test_make_lm_points_to_local_ollama_without_thinking():
    lm = opt.make_lm("qwen3:8b-q4_K_M", "localhost:11434")
    assert lm.model == "ollama_chat/qwen3:8b-q4_K_M"
    assert lm.kwargs["api_base"] == "http://localhost:11434/v1"
    assert lm.kwargs["temperature"] == 0.0
    assert lm.kwargs["reasoning_effort"] == "none"   # o Ollama traduz para think=false


def test_optimizer_choice():
    def metric(*_a):
        return 1.0

    assert isinstance(opt.make_optimizer("bootstrap", metric, demos=2, labeled=2, candidates=3, threads=1),
                      dspy.BootstrapFewShotWithRandomSearch)
    with dspy.context(lm=DummyLM([])):   # o MIPROv2 pega o LM do contexto ao ser criado
        mipro = opt.make_optimizer("mipro", metric, demos=2, labeled=2, candidates=3, threads=1)
    assert isinstance(mipro, dspy.MIPROv2) and mipro.auto == "light"
