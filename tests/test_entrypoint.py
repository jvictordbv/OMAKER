import os
import runpy
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ENTRYPOINT = Path(__file__).resolve().parents[1] / "OMAKER.py"


def test_main_returns_exec_code(monkeypatch):
    from PySide6.QtWidgets import QApplication

    from omaker import __main__ as entry

    monkeypatch.setattr(QApplication, "exec", lambda self: 0)
    assert entry.main([]) == 0


def test_legacy_entrypoint_runs_main(monkeypatch):
    from omaker import __main__ as entry

    monkeypatch.setattr(entry, "main", lambda argv=None: 7)
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(ENTRYPOINT), run_name="__main__")
    assert exc.value.code == 7
