import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_button_reenabled_after_synonym_error(qtbot, monkeypatch):
    import omaker.ui.main_window as m

    shown = []
    monkeypatch.setattr(m.QMessageBox, "critical", lambda *a, **k: shown.append(a[2]))
    win = m.OntoApp()
    qtbot.addWidget(win)
    win.btn_rodar_sinonimos.setEnabled(False)
    win.ao_falhar_sinonimos("x")
    assert win.btn_rodar_sinonimos.isEnabled()
    assert shown == ["x"]


def test_synonyms_default_independent_of_cwd(qtbot, monkeypatch, tmp_path):
    from omaker import paths
    from omaker.ui import main_window as m

    monkeypatch.chdir(tmp_path)
    win = m.OntoApp()
    qtbot.addWidget(win)
    assert win.caminho_owl_sinonimos == str(paths.package_resource("symp.owl"))
    assert win.lbl_arquivo_sinonimos.text().endswith("symp.owl")
