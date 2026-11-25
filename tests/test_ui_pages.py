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


def test_about_page_shows_the_package_version(qtbot):
    from PySide6.QtWidgets import QLabel

    import omaker
    from omaker.ui.pages.about import AboutPage

    page = AboutPage()
    qtbot.addWidget(page)
    texts = [label.text() for label in page.findChildren(QLabel)]
    assert f"OMAKER v{omaker.__version__}" in texts


def test_default_export_folder_does_not_depend_on_the_current_folder(qtbot, tmp_path, monkeypatch):
    """Sem preferência salva, a pasta de destino é Documentos/OMAKER, e não a pasta de onde o programa abriu."""
    from pathlib import Path

    from PySide6.QtCore import QSettings

    from omaker.ui import main_window as m
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "casa"))
    monkeypatch.chdir(tmp_path)
    win = m.OntoApp(configuracoes=QSettings(str(tmp_path / "cfg.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    assert win.pagina_configuracoes.pasta_exportacao() == str(tmp_path / "casa" / "Documents" / "OMAKER")


# ---- CFG-09: valores padrão das preferências
def test_first_run_uses_the_default_model_temperature_uri_and_protege_path(qtbot, tmp_path):
    from omaker.ontology.iri import DEFAULT_URI_BASE

    page, _cfg = _settings_page(qtbot, tmp_path)
    assert [page.combo_modelo.itemText(i) for i in range(page.combo_modelo.count())] == ["qwen3:8b"]
    assert page.modelo() == "qwen3:8b"
    assert page.temperatura() == 0.10 and page.lbl_valor_temp.text() == "0.10"
    assert page.uri_base() == DEFAULT_URI_BASE == "http://www.mestrado.edu/ontologias/"
    assert page.metadados.input_uri.text() == DEFAULT_URI_BASE
    assert page.caminho_protege() == "" and page.input_protege.text() == ""


# ---- CFG-11: modelo informado pelo usuário
def _add_model_button(page):
    from PySide6.QtWidgets import QPushButton

    (btn,) = [b for b in page.findChildren(QPushButton) if b.text() == "➕"]
    return btn


def test_typed_model_is_added_to_the_list_and_selected(qtbot, tmp_path):
    page, _cfg = _settings_page(qtbot, tmp_path)
    page.input_novo_modelo.setText("  qwen3:8b-q4_K_M ")
    _add_model_button(page).click()
    assert [page.combo_modelo.itemText(i) for i in range(page.combo_modelo.count())] == ["qwen3:8b", "qwen3:8b-q4_K_M"]
    assert page.modelo() == "qwen3:8b-q4_K_M"


def test_typed_model_already_in_the_list_is_not_duplicated(qtbot, tmp_path):
    page, _cfg = _settings_page(qtbot, tmp_path, lista_modelos_disponiveis=["qwen3:8b", "llama3:8b"],
                                modelo="llama3:8b")
    page.input_novo_modelo.setText("qwen3:8b")
    _add_model_button(page).click()
    assert [page.combo_modelo.itemText(i) for i in range(page.combo_modelo.count())] == ["qwen3:8b", "llama3:8b"]


def test_typed_model_already_in_the_list_is_selected(qtbot, tmp_path):
    page, _cfg = _settings_page(qtbot, tmp_path, lista_modelos_disponiveis=["qwen3:8b", "llama3:8b"],
                                modelo="llama3:8b")
    page.input_novo_modelo.setText("qwen3:8b")
    _add_model_button(page).click()
    assert page.modelo() == "qwen3:8b"


def test_blank_model_name_is_not_added(qtbot, tmp_path):
    page, _cfg = _settings_page(qtbot, tmp_path)
    page.input_novo_modelo.setText("   ")
    _add_model_button(page).click()
    assert page.combo_modelo.count() == 1 and page.modelo() == "qwen3:8b"


def test_added_model_is_saved_with_the_list(qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    page, cfg = _settings_page(qtbot, tmp_path)
    page.input_novo_modelo.setText("qwen3:8b-q4_K_M")
    _add_model_button(page).click()
    page.salvar_configuracoes()
    assert cfg.value("modelo") == "qwen3:8b-q4_K_M"
    assert list(cfg.value("lista_modelos_disponiveis")) == ["qwen3:8b", "qwen3:8b-q4_K_M"]
