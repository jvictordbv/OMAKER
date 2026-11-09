"""Qt workers. Heavy imports (torch, transformers, sklearn) are done inside run()
so the application window opens fast."""
from PySide6.QtCore import QThread, Signal

from core.labels import DEFAULT_CHECKPOINT, DEFAULT_CONFIDENCE_THRESHOLD, NO_RELATION


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
            from core.synonym_detector import SynonymDetector

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

        except Exception as e:
            self.erro.emit(f"Synonym clustering failed: {e}")


# =====================================================================
# 2. RELATION WORKER: raw text -> NER -> candidate pairs -> PURE -> OWL
# =====================================================================
class RelationWorker(QThread):
    progresso = Signal(str)
    concluido = Signal(list, str)   # triples, owl path
    erro = Signal(str)

    def __init__(
        self,
        texto: str,
        caminho_modelo: str = DEFAULT_CHECKPOINT,
        caminho_saida_owl: str = "omaker_generated.owl",
        limiar: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ):
        super().__init__()
        self.texto = texto
        self.caminho_modelo = caminho_modelo
        self.caminho_saida_owl = caminho_saida_owl
        self.limiar = limiar

    def run(self):
        try:
            import os
            from core.ner import BiomedicalNER
            from core.ontology_integrator import build_owl_ontology
            from core.pair_generator import generate_pairs
            from core.relation_extractor import RelationExtractorPURE

            if not os.path.exists(self.caminho_modelo):
                self.erro.emit(
                    f"Checkpoint '{self.caminho_modelo}' not found. Train the model first (python -m core.train)."
                )
                return

            self.progresso.emit("Loading biomedical NER...")
            ner = BiomedicalNER()

            self.progresso.emit("Detecting entities...")
            entities = ner.extract(self.texto)
            self.progresso.emit(f"{len(entities)} entities found.")

            pairs = generate_pairs(self.texto, entities)
            if not pairs:
                self.progresso.emit("No candidate entity pairs found.")
                self.concluido.emit([], "")
                return
            self.progresso.emit(f"{len(pairs)} candidate pairs. Loading PURE model...")

            model = RelationExtractorPURE.load(self.caminho_modelo)

            self.progresso.emit("Classifying relations...")
            predictions = model.predict(pairs)

            best = {}  # dedupe (subject, relation, object), keep highest confidence
            for p, (rel, conf) in zip(pairs, predictions):
                if rel == NO_RELATION or conf < self.limiar:
                    continue
                key = (p["sub_name"].lower(), rel, p["obj_name"].lower())
                triple = (p["sub_name"], p["sub_type"], rel, p["obj_name"], p["obj_type"], conf)
                if key not in best or conf > best[key][5]:
                    best[key] = triple
            triples = sorted(best.values(), key=lambda t: -t[5])

            if not triples:
                self.progresso.emit(f"No relation above the {self.limiar:.0%} confidence threshold.")
                self.concluido.emit([], "")
                return

            self.progresso.emit("Writing OWL ontology...")
            build_owl_ontology(triples, self.caminho_saida_owl, log=self.progresso.emit)

            self.progresso.emit("Done.")
            self.concluido.emit(triples, self.caminho_saida_owl)

        except Exception as e:
            self.erro.emit(f"Relation extraction failed: {e}")