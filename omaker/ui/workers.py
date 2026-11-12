"""Qt worker for synonym detection. Heavy imports (sentence-transformers, sklearn) are done inside run()
so the application window opens fast."""
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
