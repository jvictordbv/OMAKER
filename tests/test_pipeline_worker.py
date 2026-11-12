import threading

import pytest

from omaker.ui.workers import Cancelled, PipelineWorker


def test_emits_log_and_result_from_other_thread(qtbot):
    seen = {}

    def func(x, log_callback):
        seen["thread"] = threading.current_thread()
        log_callback("passo 1")
        return x * 2

    w = PipelineWorker(func, x=21)
    logs = []
    w.log.connect(logs.append)
    with qtbot.waitSignal(w.concluido, timeout=5000) as sig:
        w.start()
    w.wait()
    assert sig.args == [42]
    assert logs == ["passo 1"]
    assert seen["thread"] is not threading.main_thread()


def test_exception_becomes_falhou(qtbot):
    def func(log_callback):
        raise RuntimeError("Ollama fora do ar")

    w = PipelineWorker(func)
    with qtbot.waitSignal(w.falhou, timeout=5000) as sig:
        w.start()
    w.wait()
    assert sig.args == ["Ollama fora do ar"]


def test_cancel_stops_at_next_log(qtbot):
    started, release = threading.Event(), threading.Event()
    after_cancel = []

    def func(log_callback):
        log_callback("início")
        started.set()
        release.wait(5)
        log_callback("depois do cancelamento")   # deve levantar Cancelled
        after_cancel.append("chegou aqui")
        return "não deveria"

    w = PipelineWorker(func)
    finished = []
    w.concluido.connect(lambda r: finished.append(r))
    with qtbot.waitSignal(w.cancelado, timeout=5000):
        w.start()
        assert started.wait(5)
        w.cancel()
        release.set()
    w.wait()
    assert after_cancel == [] and finished == []


def test_cancelled_is_an_exception():
    with pytest.raises(Cancelled):
        raise Cancelled()
