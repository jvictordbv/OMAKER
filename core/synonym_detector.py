import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
from sentence_transformers import SentenceTransformer

class SynonymDetector:
    """
    Detector de Sinônimos e Conceitos Equivalentes usando Embeddings Semânticos
    e Agrupamento Não Supervisionado (Inspirado no artigo SiMHOMer).
    """
    def __init__(self, model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'):
        # 1. Carrega o modelo de Embeddings (Sentence-BERT)
        # Ele converte qualquer palavra ou frase em um vetor denso de 384 números
        print("Carregando o modelo de Embeddings Semânticos na memória...")
        self.model = SentenceTransformer(model_name)

    def agrupar_sinonimos(self, conceitos: list[str], threshold: float = 0.25) -> dict:
        """
        Recebe uma lista de palavras e agrupa automaticamente as que são sinônimas.
        
        Parâmetros:
          - conceitos: Lista de termos (ex: ["fever", "pyrexia", "headache"])
          - threshold: Limiar de distância (0.25 equivale a exigir 75% de similaridade)
        """
        if not conceitos or len(conceitos) < 2:
            return {}

        # ETAPA A: Vetorização (Embeddings)
        # Converte cada texto em coordenadas multidimensionais
        vetores = self.model.encode(conceitos)

        # ETAPA B: Cálculo da Similaridade de Cosseno
        # Mede a proximidade angular entre os vetores (resultado entre -1 e 1)
        matriz_sim = cosine_similarity(vetores)
        
        # Converte similaridade em distância (Distância = 1 - Similaridade)
        matriz_dist = np.maximum(0, 1 - matriz_sim)

        # ETAPA C: Clustering Aglomerativo (Aprendizado Não Supervisionado)
        # Agrupa os termos de baixo para cima cuja distância é menor que o threshold
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=threshold,
            metric='precomputed',
            linkage='average'
        )
        labels = clustering.fit_predict(matriz_dist)

        # ETAPA D: Organização dos Grupos
        grupos = {}
        for termo, label in zip(conceitos, labels):
            grupos.setdefault(int(label), []).append(termo)

        # Retorna apenas grupos que contêm 2 ou mais termos (equivalências encontradas)
        return {k: v for k, v in grupos.items() if len(v) > 1}

# ==============================================================================
# TESTE ISOLADO DO PASSO 1 (Rode este arquivo diretamente no VS Code)
# ==============================================================================
if __name__ == "__main__":
    print("=== TESTANDO O PASSO 1: DETECTOR DE SINÔNIMOS ===\n")
    
    detector = SynonymDetector()
    
    # Exemplo com termos médicos em inglês (como na Symptom Ontology - symp.owl)
    termos_teste = ["fever", "pyrexia", "headache", "cephalea", "cough"]
    
    print(f"Analisando os termos: {termos_teste}\n")
    
    grupos = detector.agrupar_sinonimos(termos_teste, threshold=0.25)
    
    print("--- RESULTADO DO CLUSTERING ---")
    if grupos:
        for id_grupo, termos in grupos.items():
            print(f"Grupo {id_grupo + 1} (Sinônimos Detectados): {termos}")
    else:
        print("Nenhum grupo de sinônimos encontrado para este limiar.")
