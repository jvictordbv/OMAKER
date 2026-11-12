import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_main_window_composes_pages(qtbot):
    from omaker.ui import main_window as m
    from omaker.ui.pages.generator import GeneratorPage
    from omaker.ui.pages.settings import SettingsPage
    from omaker.ui.pages.synonyms import SynonymsPage
    from omaker.ui.pages.updater import UpdaterPage

    win = m.OntoApp()
    qtbot.addWidget(win)
    assert isinstance(win.pagina_gerador, GeneratorPage)
    assert isinstance(win.pagina_atualizador, UpdaterPage)
    assert isinstance(win.pagina_sinonimos, SynonymsPage)
    assert isinstance(win.pagina_configuracoes, SettingsPage)
    assert win.area_conteudo.count() == 7
    assert win.menu_lateral.count() == 7


def test_settings_readers(qtbot, tmp_path):
    # QSettings num .ini temporário: o teste nunca toca nas configurações reais do usuário.
    from PySide6.QtCore import QSettings

    from omaker.ontology.iri import DEFAULT_URI_BASE
    from omaker.ui import main_window as m

    win = m.OntoApp(configuracoes=QSettings(str(tmp_path / "cfg.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    s = win.pagina_configuracoes
    s.slider_temp.setValue(25)
    assert s.temperatura() == 0.25
    s.configuracoes.setValue("uri_base", "")
    assert s.uri_base() == DEFAULT_URI_BASE


def _settings_page(qtbot, tmp_path, **valores):
    from PySide6.QtCore import QSettings

    from omaker.ui.pages.metadata import MetadataPage
    from omaker.ui.pages.settings import SettingsPage

    cfg = QSettings(str(tmp_path / "cfg.ini"), QSettings.IniFormat)
    for chave, valor in valores.items():
        cfg.setValue(chave, valor)
    metadados = MetadataPage()
    qtbot.addWidget(metadados)
    page = SettingsPage(metadados, configuracoes=cfg)
    qtbot.addWidget(page)
    return page, cfg


def test_settings_has_no_api_key_field(qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QLabel, QMessageBox

    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    page, cfg = _settings_page(qtbot, tmp_path, api_key="chave-antiga-do-gemini")
    assert not hasattr(page, "input_api")
    assert not hasattr(page, "api_key")
    assert not any("API" in lbl.text() for lbl in page.findChildren(QLabel))
    page.salvar_configuracoes()
    assert not cfg.contains("api_key")   # a chave antiga gravada no registro é apagada


def test_settings_drops_old_gemini_models(qtbot, tmp_path):
    page, _ = _settings_page(qtbot, tmp_path, modelo="gemini-2.5-flash",
                             lista_modelos_disponiveis=["gemini-2.5-flash", "qwen3:8b", "Gemini-Pro"])
    modelos = [page.combo_modelo.itemText(i) for i in range(page.combo_modelo.count())]
    assert modelos == ["qwen3:8b"]
    assert page.modelo() == "qwen3:8b"


def test_settings_keeps_default_model_when_only_gemini_saved(qtbot, tmp_path):
    page, _ = _settings_page(qtbot, tmp_path, lista_modelos_disponiveis=["gemini-2.5-flash"])
    assert page.modelo() == "qwen3:8b"
