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
