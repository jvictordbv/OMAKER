from PySide6.QtCore import QThread, Signal
from core.synonym_detector import SynonymDetector
from core.ontology_intergrator import OntologyIntegrator

class SynonymWorker(QThread):
    """
    Thread em segundo plano para executar o agrupamento por Machine Learning
    sem congelar a interface gráfica do OMAKER.
    """
    # Sinais para comunicar o progresso e o resultado para a tela
    progresso = Signal(str)
    concluido = Signal(dict, str) # Retorna (grupos_sinonimos, caminho_ontologia_salva)
    erro = Signal(str)

    def __init__(self, caminho_ontologia: str, conceitos: list, threshold: float = 0.25):
        super().__init__()
        self.caminho_ontologia = caminho_ontologia
        self.conceitos = conceitos
        self.threshold = threshold

    def run(self):
        try:
            # 1. Avisa a interface que está carregando a IA
            self.progresso.emit("Carregando o modelo de Embeddings (Sentence-BERT)...")
            detector = SynonymDetector()

            # 2. Executa o agrupamento semântico (Passo 1)
            self.progresso.emit("Agrupando conceitos por similaridade de cosseno...")
            grupos = detector.agrupar_sinonimos(self.conceitos, threshold=self.threshold)

            if not grupos:
                self.progresso.emit("Nenhum grupo de sinônimos foi encontrado para o limiar selecionado.")
                self.concluido.emit({}, "")
                return

            # 3. Executa a integração com o Owlready2 (Passo 2)
            self.progresso.emit("Injetando axiomas owl:equivalentClass na ontologia...")
            integrador = OntologyIntegrator(self.caminho_ontologia)
            integrador.aplicar_equivalencias_da_ml(grupos)

            # 4. Salva o resultado final
            caminho_saida = "omaker_ontologia_enriquecida.owl"
            integrador.salvar_ontologia(caminho_saida)

            self.progresso.emit("Processo concluído com sucesso!")
            self.concluido.emit(grupos, caminho_saida)

        except Exception as e:
            self.erro.emit(f"Erro durante o processamento: {str(e)}")
