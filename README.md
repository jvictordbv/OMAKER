# OMAKER: Ontology Mapping & Knowledge Engineering Resource

> **Ambiente Inteligente para Extração Automática de Axiomas e Engenharia de Ontologias baseada em Large Language Models (LLMs)**

---

## 🏛️ Sobre o Projeto
O OMAKER é um ecossistema computacional projetado para mitigar o gargalo da aquisição de conhecimento na Web Semântica. Utilizando Large Language Models (LLMs) de última geração (Google Gemini) e engenharia de prompt estruturada, o sistema automatiza a conversão de corpus textuais complexos em ontologias formais expressas em **Lógica de Descrição (DL)**, em estrita conformidade com as diretrizes do **W3C**.

### 🛠️ Arquitetura e Tecnologias
- **Core Semântico:** Owlready2 (Manipulação de grafos RDF/XML e Raciocinador Pellet).
- **Processamento de Linguagem Natural:** API Google Generative AI (`gemini-2.5`).
- **Interface Gráfica (GUI):** PySide6 (Qt para Python) com arquitetura modular.

---

## 🚀 Instalação e Configuração

### 1. Pré-requisitos
- [uv](https://docs.astral.sh/uv/) instalado (ele baixa o Python 3.12 indicado em `.python-version`).
- Java 11+, usado pelo raciocinador HermiT. O OMAKER procura em OMAKER_JAVA, JAVA_HOME, PATH, Program Files e no JRE que vem com o Protégé (caminho informado nas Configurações).
- [Ollama](https://ollama.com/) em execução com o modelo configurado: `ollama pull qwen3:8b`.

### 2. Clonar o Repositório e Instalar as Dependências
```bash
git clone https://github.com/seu-usuario/Project_OMAKER.git
cd Project_OMAKER
uv sync --extra dev
```

### 3. Execução
```bash
uv run python OMAKER.py
```

### 4. Testes
```bash
uv run pytest
```

@mastersthesis{barbosa2026omaker,
  author       = {João Victor Ferreira Barbosa},
  title        = {OMAKER: Ontology Mapping \& Knowledge Engineering Resource},
  school       = {Universidade Federal de Pernambuco (UFPE)},
  year         = {2026},
  type         = {Projeto de Mestrado}
}
