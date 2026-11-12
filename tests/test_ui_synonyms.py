import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402


def test_button_reenabled_after_synonym_error(qtbot, monkeypatch):
    import omaker.ui.main_window as m

    shown = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *a, **k: shown.append(a[2]))
    win = m.OntoApp()
    qtbot.addWidget(win)
    page = win.pagina_sinonimos
    page.btn_rodar_sinonimos.setEnabled(False)
    page.ao_falhar_sinonimos("x")
    assert page.btn_rodar_sinonimos.isEnabled()
    assert shown == ["x"]


def test_synonyms_default_independent_of_cwd(qtbot, monkeypatch, tmp_path):
    from omaker import paths
    from omaker.ui import main_window as m

    monkeypatch.chdir(tmp_path)
    win = m.OntoApp()
    qtbot.addWidget(win)
    assert win.pagina_sinonimos.caminho_owl_sinonimos == str(paths.package_resource("symp.owl"))
    assert win.pagina_sinonimos.lbl_arquivo_sinonimos.text().endswith("symp.owl")
