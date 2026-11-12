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


def _synonyms_page(qtbot, tmp_path):
    from PySide6.QtCore import QSettings

    from omaker.ui import main_window as m

    win = m.OntoApp(configuracoes=QSettings(str(tmp_path / "cfg.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.pagina_configuracoes.input_diretorio.setText(str(tmp_path))
    return win, win.pagina_sinonimos   # win precisa continuar referenciada


def test_synonyms_not_written_without_confirmation(qtbot, monkeypatch, tmp_path):
    from omaker.ui.pages import synonyms

    win, page = _synonyms_page(qtbot, tmp_path)
    calls = []
    monkeypatch.setattr(synonyms, "add_equivalences", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *a, **k: QtWidgets.QMessageBox.No)
    page.ao_concluir_sinonimos({0: ["a", "b"]}, "")
    assert calls == []


def test_synonyms_written_after_confirmation(qtbot, monkeypatch, tmp_path):
    from omaker.ontology.builder import EquivalenceReport
    from omaker.ui.pages import synonyms

    win, page = _synonyms_page(qtbot, tmp_path)
    calls = []

    def fake(src, groups, dest, log=print):
        calls.append(dest)
        return EquivalenceReport(1, [["a", "b"]], [], dest)

    shown = []
    monkeypatch.setattr(synonyms, "add_equivalences", fake)
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *a, **k: QtWidgets.QMessageBox.Yes)
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: shown.append(a[2]))
    page.ao_concluir_sinonimos({0: ["a", "b"]}, "")
    assert len(calls) == 1
    assert calls[0].endswith("symp_sinonimos.owl") and calls[0].startswith(str(tmp_path))
    assert "1 equivalência" in shown[0]
