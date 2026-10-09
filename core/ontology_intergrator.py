import os
from owlready2 import get_ontology, Thing

class OntologyIntegrator:
    """
    Classe responsável por conectar as descobertas de Machine Learning (sinônimos)
    com a estrutura lógica da Ontologia usando a biblioteca Owlready2.
    """
    def __init__(self, ontology_path: str = None):
        self.ontology_path = ontology_path

        # Se o arquivo existir, carrega; se não existir, cria uma nova em memória
        if ontology_path and os.path.exists(ontology_path):
            print(f"Carregando ontologia existente: {ontology_path}")
            self.onto = get_ontology(ontology_path).load()
        else:
            if ontology_path:
                print(f"Aviso: O arquivo '{ontology_path}' não foi encontrado na pasta. Criando ontologia em memória...")
            else:
                print("Criando nova ontologia em memória...")
            self.onto = get_ontology("http://exemplo.org/omaker_nova.owl")

    def aplicar_equivalencias_da_ml(self, grupos_sinonimos: dict):
        """
        Recebe os grupos de sinônimos gerados pelo SynonymDetector
        e cria axiomas 'owl:equivalentClass' na ontologia do OMAKER.
        """
        if not self.onto:
            print("Erro: Nenhuma ontologia disponível para aplicar os axiomas.")
            return

        with self.onto:
            for cluster_id, termos in grupos_sinonimos.items():
                if len(termos) < 2:
                    continue  # Precisamos de pelo menos 2 termos

                # CORREÇÃO: Usamos termos para pegar a primeira palavra da lista
                primeiro_termo = termos[0]
                nome_conceito_principal = primeiro_termo.capitalize()

                classe_principal = getattr(self.onto, nome_conceito_principal, None)
                if not classe_principal:
                    classe_principal = type(nome_conceito_principal, (Thing,), {})

                # Para os demais sinônimos da lista (do índice 1 em diante)
                for sinonimo in termos[1:]:
                    nome_sinonimo = sinonimo.capitalize()
                    classe_sinonimo = getattr(self.onto, nome_sinonimo, None)

                    if not classe_sinonimo:
                        classe_sinonimo = type(nome_sinonimo, (Thing,), {})

                    # Injeta o axioma owl:equivalentClass
                    classe_principal.equivalent_to.append(classe_sinonimo)
                    print(f"AXIOMA GERADO: {classe_principal.name} <owl:equivalentClass> {classe_sinonimo.name}")


    def salvar_ontologia(self, output_path: str):
        """Salva o arquivo .owl atualizado no disco."""
        if self.onto:
            self.onto.save(file=output_path, format="rdfxml")
            caminho_abs = os.path.abspath(output_path)
            print(f"\nOntologia salva com sucesso em:")
            print(f"👉 {caminho_abs}")
        else:
            print("Erro: Nenhuma ontologia para salvar.")

# ==============================================================================
# TESTE PRÁTICO DO PASSO 2
# ==============================================================================
if __name__ == "__main__":
    print("=== TESTANDO A INTEGRAÇÃO DE MACHINE LEARNING + OWLREADY2 ===\n")

    # 1. Importamos e executamos o Detector de Sinônimos (Passo 1)
    from synonym_detector import SynonymDetector

    detector = SynonymDetector()
    conceitos = ["doença", "enfermidade", "patologia", "carro", "automóvel"]
    grupos = detector.agrupar_sinonimos(conceitos, threshold=0.25)

    print(f"Grupos identificados pela ML: {grupos}\n")

    # 2. Inicializamos o integrador
    integrador = OntologyIntegrator("symp.owl")

    # 3. Aplicamos as regras de equivalência
    integrador.aplicar_equivalencias_da_ml(grupos)

    # 4. Salvamos o arquivo resultante
    caminho_saida = "omaker_teste_com_ml.owl"
    integrador.salvar_ontologia(caminho_saida)
