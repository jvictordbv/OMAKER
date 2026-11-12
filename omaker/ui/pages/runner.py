"""Execução do motor em segundo plano, compartilhada pelas páginas Gerador e Atualizador."""
from PySide6.QtWidgets import QMessageBox

from omaker.domain.text import looks_non_english
from omaker.ui.workers import PipelineWorker

AVISO_IDIOMA = "O texto deve estar em inglês: os modelos de entidades e de relações foram treinados em inglês."


class PipelineRunnerMixin:
    """Mixin para QWidget. A página define btn_cancelar, _log_widget(), _run_button(), _ao_concluir(resultado)
    e MSG_CANCELADO.

    Os sinais do worker vão para métodos ligados ao próprio widget, que vive na thread da interface;
    assim os slots rodam nela e nunca tocam widgets a partir da thread do worker.
    """

    worker: PipelineWorker | None = None
    silencioso = False   # True quando a janela está fechando: nenhuma caixa de diálogo
    MSG_CANCELADO = "> [CANCELADO] Interrompido pelo usuário."

    def em_execucao(self) -> bool:
        return self.worker is not None

    def _confirmar_idioma(self, texto: str) -> bool:
        """Se o texto parece não estar em inglês, pergunta se deve seguir mesmo assim."""
        if not looks_non_english(texto):
            return True
        resposta = QMessageBox.question(
            self, "Idioma do texto",
            "O texto parece não estar em inglês. O OMAKER processa textos em inglês; em outro idioma, "
            "as entidades e relações podem sair erradas ou nem ser encontradas.\n\nProcessar mesmo assim?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        return resposta == QMessageBox.StandardButton.Yes

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
        if not self.silencioso:
            QMessageBox.critical(self, "Erro", msg)

    def _ao_cancelar(self) -> None:
        self._log_widget().append(f"\n{self.MSG_CANCELADO}")
        if not self.silencioso:
            QMessageBox.information(self, "Cancelado", "A operação foi cancelada.")

    def _finalizar(self) -> None:
        self._run_button().setEnabled(True)
        self.btn_cancelar.setEnabled(False)
        self.worker = None
