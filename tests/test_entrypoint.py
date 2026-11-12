import os
import runpy
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ENTRYPOINT = Path(__file__).resolve().parents[1] / "OMAKER.py"


def test_main_returns_exec_code(qapp, qtbot, monkeypatch):
    # qapp: usa o QApplication do pytest-qt. Um QApplication criado aqui seria destruído antes das
    # janelas e o Python cairia ao encerrar (segfault intermitente no CI).
    from PySide6.QtWidgets import QApplication

    from omaker import __main__ as entry

    monkeypatch.setattr(QApplication, "exec", lambda self: 0)
    before = set(QApplication.topLevelWidgets())
    assert entry.main([]) == 0
    for widget in set(QApplication.topLevelWidgets()) - before:
        qtbot.addWidget(widget)  # fechadas e apagadas pelo pytest-qt no fim do teste


def test_legacy_entrypoint_runs_main(monkeypatch):
    from omaker import __main__ as entry

    monkeypatch.setattr(entry, "main", lambda argv=None: 7)
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(ENTRYPOINT), run_name="__main__")
    assert exc.value.code == 7
