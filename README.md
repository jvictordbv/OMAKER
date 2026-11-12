# OMAKER: Ontology Mapping & Knowledge Engineering Resource

> **Ambiente Inteligente para Extração Automática de Axiomas e Engenharia de Ontologias baseada em Large Language Models (LLMs)**

---

## 🏛️ Sobre o Projeto
O OMAKER é um ecossistema computacional projetado para mitigar o gargalo da aquisição de conhecimento na Web Semântica. Combinando reconhecimento de entidades biomédicas (NER), um LLM local (Qwen via Ollama) e extração de relações com PURE/SpanBERT, o sistema automatiza a conversão de corpus textuais complexos em ontologias formais expressas em **Lógica de Descrição (DL)**, em estrita conformidade com as diretrizes do **W3C**.

### 🛠️ Arquitetura e Tecnologias
- **Core Semântico:** Owlready2 (manipulação de grafos RDF/XML) e raciocinador HermiT para validar a consistência lógica.
- **Processamento de Linguagem Natural:** NER biomédico, Qwen local via Ollama e PURE/SpanBERT para relações, tudo executado na máquina do usuário.
- **Interface Gráfica (GUI):** PySide6 (Qt para Python) com arquitetura modular.

---

## 🚀 Instalação e Configuração

### 1. Pré-requisitos
- [uv](https://docs.astral.sh/uv/) instalado (ele baixa o Python 3.12 indicado em `.python-version`).
- Java 11+, usado pelo raciocinador HermiT. O OMAKER procura em OMAKER_JAVA, JAVA_HOME, PATH, Program Files e no JRE que vem com o Protégé (caminho informado nas Configurações).
- [Ollama](https://ollama.com/) em execução com o modelo configurado: `ollama pull qwen3:8b`.

### 2. Clonar o Repositório e Instalar as Dependências
```bash
git clone https://github.com/jvictordbv/OMAKER.git
cd OMAKER
uv sync --extra dev
```

### 3. Execução
```bash
uv run python -m omaker
```

O comando antigo `uv run python OMAKER.py` continua funcionando. Rode os comandos a partir da pasta do repositório.

Treino do classificador de relações (PURE):
```bash
uv run python -m omaker.relations.train
```

### Estrutura

O código fica no pacote `omaker/`:

- `domain/`: rótulos, tipos e utilidades de texto.
- `nlp/`: NER biomédico, pares candidatos e detecção de sinônimos.
- `llm/`: cliente do Ollama e extração de entidades pelo LLM.
- `relations/`: modelo PURE (SpanBERT), treino e dados de treino.
- `ontology/`: construção do OWL, IRI, localização do Java (HermiT) e Protégé.
- `pipeline/`: o motor que liga as etapas, do texto ao arquivo `.owl`.
- `ui/`: interface PySide6.

### 4. Testes
```bash
uv run pytest -m "not slow and not ollama"
```

@mastersthesis{barbosa2026omaker,
  author       = {João Victor Ferreira Barbosa},
  title        = {OMAKER: Ontology Mapping \& Knowledge Engineering Resource},
  school       = {Universidade Federal de Pernambuco (UFPE)},
  year         = {2026},
  type         = {Projeto de Mestrado}
}
