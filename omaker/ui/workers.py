"""Qt workers (synonym detection and the ontology pipeline). Heavy imports (sentence-transformers, sklearn) are done inside run()
so the application window opens fast."""
import threading

from PySide6.QtCore import QThread, Signal


# =====================================================================
# 1. SYNONYM WORKER (semantic equivalence: owl:equivalentClass)
# =====================================================================
class SynonymWorker(QThread):
    progresso = Signal(str)
    concluido = Signal(dict, str)
    erro = Signal(str)

    def __init__(self, caminho_ontologia: str, conceitos: list, threshold: float = 0.25):
        super().__init__()
        self.caminho_ontologia = caminho_ontologia
        self.conceitos = conceitos
        self.threshold = threshold

    def run(self):
        try:
            from omaker.nlp.synonyms import SynonymDetector

            self.progresso.emit("Loading embedding model (Sentence-BERT)...")
            detector = SynonymDetector()

            self.progresso.emit("Clustering concepts by cosine similarity...")
            grupos = detector.agrupar_sinonimos(self.conceitos, threshold=self.threshold)

            if not grupos:
                self.progresso.emit("No synonym groups found.")
                self.concluido.emit({}, "")
                return

            # Nothing is written to the ontology yet (owl:equivalentClass axioms: phase 3).
            self.progresso.emit("Synonym detection finished.")
            self.concluido.emit(grupos, "")

        except Exception as e:  # noqa: BLE001  worker QThread: qualquer falha vira sinal de erro, sem derrubar a UI
            self.erro.emit(f"Synonym clustering failed: {e}")


# =====================================================================
# 2. PIPELINE WORKER (Gerar / Atualizar fora da thread da interface)
# =====================================================================
class Cancelled(BaseException):
    """Levantada dentro do motor, na próxima mensagem de log, quando o usuário cancela.
    Herda de BaseException para atravessar os "except Exception" do motor (ex.: run_reasoner)."""


class PipelineWorker(QThread):
    """Roda func(**kwargs, log_callback=...) numa thread própria. Só emite sinais: nenhum widget é tocado aqui.

    Exatamente um sinal final é emitido: concluido(resultado), falhou(mensagem) ou cancelado().
    O cancelamento é cooperativo: vale na próxima chamada de log_callback (entre etapas do motor).
    """

    log = Signal(str)
    concluido = Signal(object)
    falhou = Signal(str)
    cancelado = Signal()

    def __init__(self, func, **kwargs):
        super().__init__()
        self.func = func
        self.kwargs = kwargs
        self._cancelar = threading.Event()

    def cancel(self) -> None:
        self._cancelar.set()

    def _log(self, msg: str) -> None:
        self.log.emit(msg)
        if self._cancelar.is_set():
            raise Cancelled()

    def run(self):
        try:
            resultado = self.func(**self.kwargs, log_callback=self._log)
        except Cancelled:
            self.cancelado.emit()
        except Exception as e:  # noqa: BLE001  worker QThread: qualquer falha vira sinal de erro, sem derrubar a UI
            self.falhou.emit(str(e))
        else:
            self.concluido.emit(resultado)
