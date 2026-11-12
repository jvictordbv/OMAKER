"""Execução do motor em segundo plano, compartilhada pelas páginas Gerador e Atualizador."""
from PySide6.QtWidgets import QMessageBox

from omaker.ui.workers import PipelineWorker


class PipelineRunnerMixin:
    """Mixin para QWidget. A página define btn_cancelar, _log_widget(), _run_button(), _ao_concluir(resultado)
    e MSG_CANCELADO.

    Os sinais do worker vão para métodos ligados ao próprio widget, então os slots rodam na thread da
    interface (um lambda solto rodaria na thread do worker e tocaria widgets fora dela).
    """

    worker: PipelineWorker | None = None
    MSG_CANCELADO = "> [CANCELADO] Interrompido pelo usuário."

    def em_execucao(self) -> bool:
        return self.worker is not None

    def cancelar(self) -> None:
        if self.worker is not None:
            self.btn_cancelar.setEnabled(False)
            self._log_widget().append("> [CANCELANDO] O pedido vale ao fim da etapa atual...")
            self.worker.cancel()

    def _rodar(self, func, **kwargs) -> None:
        self.worker = PipelineWorker(func, **kwargs)
        self.worker.log.connect(self._log_widget().append)
        self.worker.concluido.connect(self._ao_concluir)
        self.worker.falhou.connect(self._ao_falhar)
        self.worker.cancelado.connect(self._ao_cancelar)
        self.worker.finished.connect(self._finalizar)
        self._run_button().setEnabled(False)
        self.btn_cancelar.setEnabled(True)
        self.worker.start()

    def _ao_falhar(self, msg: str) -> None:
        self._log_widget().append(f"\n> [CRITICAL ERROR] {msg}")
        QMessageBox.critical(self, "Erro", msg)

    def _ao_cancelar(self) -> None:
        self._log_widget().append(f"\n{self.MSG_CANCELADO}")
        QMessageBox.information(self, "Cancelado", "A operação foi cancelada.")

    def _finalizar(self) -> None:
        self._run_button().setEnabled(True)
        self.btn_cancelar.setEnabled(False)
        self.worker = None
