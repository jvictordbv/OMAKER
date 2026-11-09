import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_button_reenabled_after_synonym_error(qtbot, monkeypatch):
    import ui.main_window as m

    shown = []
    monkeypatch.setattr(m.QMessageBox, "critical", lambda *a, **k: shown.append(a[2]))
    win = m.OntoApp()
    qtbot.addWidget(win)
    win.btn_rodar_sinonimos.setEnabled(False)
    win.ao_falhar_sinonimos("x")
    assert win.btn_rodar_sinonimos.isEnabled()
    assert shown == ["x"]
