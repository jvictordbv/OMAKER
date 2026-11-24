from omaker import self_check


def test_self_check_passes_from_source(tmp_path):
    out = tmp_path / "check.txt"
    assert self_check.run(out) == 0, out.read_text(encoding="utf-8")
    assert out.read_text(encoding="utf-8").rstrip().endswith("OK")


def test_self_check_reports_a_missing_module(tmp_path, monkeypatch):
    monkeypatch.setattr(self_check, "MODULES", ("omaker", "modulo_que_nao_existe"))
    out = tmp_path / "check.txt"
    assert self_check.run(out) == 1
    text = out.read_text(encoding="utf-8")
    assert "FALHOU  import modulo_que_nao_existe" in text and text.rstrip().endswith("FALHOU")


def test_entrypoint_runs_the_self_check_without_opening_the_window(tmp_path, monkeypatch):
    from omaker import __main__ as entry

    seen = []
    monkeypatch.setattr(self_check, "run", lambda out: seen.append(out) or 0)
    assert entry.main(["OMAKER.exe", "--self-check", str(tmp_path / "x.txt")]) == 0
    assert seen == [str(tmp_path / "x.txt")]
