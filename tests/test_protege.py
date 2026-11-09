import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from core import protege


class FakePopen:
    chamadas = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        FakePopen.chamadas.append(self)


@pytest.fixture
def fake(monkeypatch):
    FakePopen.chamadas = []
    monkeypatch.setattr(protege.subprocess, "Popen", FakePopen)
    return FakePopen


def _arquivos(tmp_path, nome_owl="onto.owl"):
    exe = tmp_path / "Protege.exe"
    exe.write_text("x")
    owl = tmp_path / nome_owl
    owl.write_text("<rdf/>")
    return str(exe), str(owl)


def test_opens_with_argument_list(tmp_path, fake):
    exe, owl = _arquivos(tmp_path)
    protege.abrir_no_protege(owl, exe)
    chamada = fake.chamadas[0]
    assert chamada.args[0] == [exe, os.path.abspath(owl)]
    assert chamada.kwargs.get("shell", False) is False
    assert chamada.kwargs["cwd"] == os.path.dirname(exe)


def test_path_with_spaces_passed_as_one_argument(tmp_path, fake):
    exe, owl = _arquivos(tmp_path, "teste peste negra.owl")
    protege.abrir_no_protege(owl, exe)
    lista = fake.chamadas[0].args[0]
    assert len(lista) == 2
    assert lista[1] == os.path.abspath(owl)


def test_missing_exe_raises(tmp_path, fake):
    _, owl = _arquivos(tmp_path)
    with pytest.raises(FileNotFoundError, match="Protégé"):
        protege.abrir_no_protege(owl, str(tmp_path / "nao_existe.exe"))
    assert fake.chamadas == []


def test_missing_owl_raises(tmp_path, fake):
    exe, _ = _arquivos(tmp_path)
    with pytest.raises(FileNotFoundError, match="Ontologia não encontrada"):
        protege.abrir_no_protege(str(tmp_path / "nada.owl"), exe)
    assert fake.chamadas == []


def test_open_button_starts_disabled(qtbot):
    import ui.main_window as m

    win = m.OntoApp()
    qtbot.addWidget(win)
    assert win.btn_abrir_protege.isEnabled() is False


def test_open_button_shows_warning_on_oserror(qtbot, monkeypatch, tmp_path):
    from types import SimpleNamespace

    import ui.main_window as m

    exe, owl = _arquivos(tmp_path)

    def popen_falso(*a, **k):
        raise OSError(193, "%1 não é um aplicativo Win32 válido")

    monkeypatch.setattr(protege.subprocess, "Popen", popen_falso)
    avisos = []
    monkeypatch.setattr(m.QMessageBox, "warning", lambda *a, **k: avisos.append(a[2]))
    win = m.OntoApp()
    qtbot.addWidget(win)
    win.configuracoes = SimpleNamespace(value=lambda chave, padrao="": exe)
    win.caminho_owl_gerado = owl
    win.abrir_protege_clicado()
    assert len(avisos) == 1 and "193" in avisos[0]
