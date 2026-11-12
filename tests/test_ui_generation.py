import inspect
import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402
from PySide6.QtCore import QSettings  # noqa: E402

from omaker.ontology.builder import ReasonerStatus  # noqa: E402
from omaker.pipeline.engine import HybridEngine, OntologyResult  # noqa: E402


@pytest.fixture
def boxes(monkeypatch):
    """Troca as caixas de diálogo por registradores: {'information': [...], 'warning': [...], 'critical': [...]}."""
    shown = {"information": [], "warning": [], "critical": []}
    for kind in shown:
        monkeypatch.setattr(QtWidgets.QMessageBox, kind, lambda *a, _k=kind, **kw: shown[_k].append(a[1:]))
    return shown


@pytest.fixture
def win(qtbot, tmp_path):
    from omaker.ui import main_window as m

    w = m.OntoApp(configuracoes=QSettings(str(tmp_path / "cfg.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.pagina_configuracoes.input_diretorio.setText(str(tmp_path))
    return w


def _fill_generator(page):
    page.input_nome_arquivo.setText("teste")
    page.texto_entrada.setPlainText("Aspirin prevents stroke.")


def _result(tmp_path):
    path = tmp_path / "x.owl"
    path.write_text("<rdf/>", encoding="utf-8")
    return OntologyResult(str(path), ReasonerStatus.CONSISTENT, 1)


def test_generation_runs_off_gui_thread(win, qtbot, monkeypatch, tmp_path, boxes):
    seen = {}

    real = HybridEngine.gerar_ontologia

    def fake(**kw):
        inspect.signature(real).bind(**kw)   # a página chama com argumentos que o motor aceita
        seen["thread"] = threading.current_thread()
        kw["log_callback"]("> passo")
        return _result(tmp_path)

    monkeypatch.setattr(HybridEngine, "gerar_ontologia", fake)
    page = win.pagina_gerador
    _fill_generator(page)
    page.btn_gerar.click()
    qtbot.waitUntil(lambda: not page.em_execucao(), timeout=5000)
    assert seen["thread"] is not threading.main_thread()
    assert "> passo" in page.texto_log.toPlainText()
    assert page.btn_abrir_protege.isEnabled()
    assert len(boxes["information"]) == 1


def test_generate_button_disabled_while_running(win, qtbot, monkeypatch, tmp_path, boxes):
    release, calls = threading.Event(), []

    def fake(**kw):
        calls.append(1)
        release.wait(5)
        return _result(tmp_path)

    monkeypatch.setattr(HybridEngine, "gerar_ontologia", fake)
    page = win.pagina_gerador
    _fill_generator(page)
    page.btn_gerar.click()
    qtbot.waitUntil(lambda: len(calls) == 1, timeout=5000)
    assert not page.btn_gerar.isEnabled()
    assert page.btn_cancelar.isEnabled()
    page.processar_ontologia()          # segundo pedido enquanto roda: ignorado
    release.set()
    qtbot.waitUntil(lambda: not page.em_execucao(), timeout=5000)
    assert calls == [1]
    assert page.btn_gerar.isEnabled() and not page.btn_cancelar.isEnabled()


def test_generate_failure_reenables_button(win, qtbot, monkeypatch, boxes):
    def fake(**kw):
        raise RuntimeError("Ollama fora do ar")

    monkeypatch.setattr(HybridEngine, "gerar_ontologia", fake)
    page = win.pagina_gerador
    _fill_generator(page)
    page.btn_gerar.click()
    qtbot.waitUntil(lambda: not page.em_execucao(), timeout=5000)
    assert page.btn_gerar.isEnabled()
    assert not page.btn_abrir_protege.isEnabled()
    assert "Ollama fora do ar" in page.texto_log.toPlainText()
    assert len(boxes["critical"]) == 1


def _looping(**kw):
    end = time.monotonic() + 5
    while time.monotonic() < end:
        kw["log_callback"]("> trabalhando")
        time.sleep(0.01)
    raise AssertionError("o cancelamento não chegou")


def test_cancel_generation(win, qtbot, monkeypatch, boxes):
    monkeypatch.setattr(HybridEngine, "gerar_ontologia", _looping)
    page = win.pagina_gerador
    _fill_generator(page)
    page.btn_gerar.click()
    qtbot.waitUntil(lambda: "> trabalhando" in page.texto_log.toPlainText(), timeout=5000)
    page.btn_cancelar.click()
    qtbot.waitUntil(lambda: not page.em_execucao(), timeout=5000)
    assert "[CANCELADO]" in page.texto_log.toPlainText()
    assert boxes["critical"] == [] and boxes["warning"] == []
    assert page.btn_gerar.isEnabled()
    assert not page.btn_abrir_protege.isEnabled()


def test_close_during_run_waits_for_worker(win, qtbot, monkeypatch, boxes):
    monkeypatch.setattr(HybridEngine, "gerar_ontologia", _looping)
    page = win.pagina_gerador
    _fill_generator(page)
    win.show()
    page.btn_gerar.click()
    qtbot.waitUntil(lambda: "> trabalhando" in page.texto_log.toPlainText(), timeout=5000)
    worker = page.worker
    win.close()
    qtbot.waitUntil(lambda: worker.isFinished() and not win.isVisible(), timeout=5000)
    assert boxes == {"information": [], "warning": [], "critical": []}


def test_close_during_silent_step_does_not_block_and_closes_later(win, qtbot, monkeypatch, boxes):
    """Uma chamada ao Ollama ou ao HermiT não loga nada por muito tempo: fechar não pode travar a
    janela, nem encerrar com a thread rodando, nem deixar uma caixa "Cancelado" aberta."""
    started = threading.Event()

    def silent(**kw):
        kw["log_callback"]("> chamando o LLM")
        started.set()
        time.sleep(1.5)                       # etapa longa, sem log
        kw["log_callback"]("> resposta")       # aqui o cancelamento é atendido
        raise AssertionError("o cancelamento não chegou")

    monkeypatch.setattr(HybridEngine, "gerar_ontologia", silent)
    page = win.pagina_gerador
    _fill_generator(page)
    win.show()
    page.btn_gerar.click()
    assert started.wait(5)
    worker = page.worker
    t0 = time.monotonic()
    win.close()
    assert time.monotonic() - t0 < 0.5        # não bloqueia a interface
    assert win.isVisible()                     # fecha só quando a etapa terminar
    qtbot.waitUntil(lambda: worker.isFinished() and not win.isVisible(), timeout=5000)
    assert boxes == {"information": [], "warning": [], "critical": []}


def test_update_runs_off_gui_thread(win, qtbot, monkeypatch, tmp_path, boxes):
    seen = {}

    real = HybridEngine.atualizar_ontologia

    def fake(**kw):
        inspect.signature(real).bind(**kw)
        seen["thread"] = threading.current_thread()
        kw["log_callback"]("> mesclando")
        return _result(tmp_path)

    monkeypatch.setattr(HybridEngine, "atualizar_ontologia", fake)
    page = win.pagina_atualizador
    page.caminho_owl_atual = str(tmp_path / "base.owl")
    page.texto_entrada_atualizador.setPlainText("Aspirin prevents stroke.")
    page.btn_atualizar.click()
    qtbot.waitUntil(lambda: not page.em_execucao(), timeout=5000)
    assert seen["thread"] is not threading.main_thread()
    assert "> mesclando" in page.log_atualizador.toPlainText()
    assert page.btn_atualizar.isEnabled()
    assert len(boxes["information"]) == 1


def test_close_during_synonyms_waits_for_worker(win, qtbot, monkeypatch, boxes):
    from omaker.ui import workers

    monkeypatch.setattr(workers.SynonymWorker, "run", lambda self: time.sleep(1.0))
    page = win.pagina_sinonimos
    win.show()
    page.executar_worker_sinonimos()
    worker = page.worker
    t0 = time.monotonic()
    win.close()
    assert time.monotonic() - t0 < 0.5
    assert win.isVisible()
    qtbot.waitUntil(lambda: worker.isFinished() and not win.isVisible(), timeout=5000)
