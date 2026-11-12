# OMAKER: Ontology Mapping & Knowledge Engineering Resource

[![CI](https://github.com/jvictordbv/OMAKER/actions/workflows/ci.yml/badge.svg)](https://github.com/jvictordbv/OMAKER/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Ruff](https://img.shields.io/badge/lint-ruff-261230)

Aplicação desktop que transforma texto biomédico em uma ontologia OWL validada logicamente, combinando reconhecimento de entidades, um LLM local e um classificador de relações treinável (PURE/SpanBERT).

Projeto de mestrado de João Victor Ferreira Barbosa, na Universidade Federal de Pernambuco (UFPE).

## Sumário

- [Sobre](#sobre)
- [Funcionalidades](#funcionalidades)
- [Como funciona](#como-funciona)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Uso](#uso)
- [Configuração](#configuração)
- [Treino e avaliação do modelo](#treino-e-avaliação-do-modelo)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Testes e qualidade](#testes-e-qualidade)
- [Contribuindo](#contribuindo)
- [Como citar](#como-citar)
- [Licença](#licença)

## Sobre

Construir ontologias formais (OWL, Lógica de Descrição) a partir de texto livre exige muito trabalho manual de engenheiros do conhecimento: é o gargalo de aquisição de conhecimento da Web Semântica. O OMAKER automatiza parte desse trabalho no domínio biomédico (fármacos, sintomas, doenças e genes). Tudo roda na máquina do usuário, sem enviar o texto a serviços externos.

## Funcionalidades

- **Gerar uma ontologia** a partir de um texto:
  - entidades e relações (`treats`, `causes`, `prevents`) extraídas;
  - taxonomia proposta pelo LLM e validada;
  - consistência conferida pelo raciocinador HermiT.
- **Atualizar uma ontologia existente** com novas evidências. Em ontologias externas, como a Symptom Ontology, as entidades são alinhadas às classes que já existem, pelo rótulo e pelos sinônimos exatos, sem criar uma hierarquia paralela.
- **Detectar sinônimos** com Sentence-BERT e gravá-los como `owl:equivalentClass` numa cópia da ontologia, depois da confirmação do usuário.
- **Abrir o resultado no Protégé** direto da interface.
- **Treinar e avaliar** o classificador de relações com divisão fixa dos dados, métricas com intervalo de confiança e avaliação de ponta a ponta contra baselines.
- **Interface responsiva:** a geração roda em segundo plano e pode ser cancelada.

## Como funciona

1. **Entidades:** um NER biomédico (`d4data/biomedical-ner-all`) e o LLM local (Qwen3 via Ollama) propõem as menções. Cada menção do LLM precisa ser achada no texto.
2. **Pares candidatos:** pares de entidades na mesma frase, com tipos compatíveis.
3. **Relações:**
   - Com um checkpoint treinado, o PURE/SpanBERT classifica cada par, e só ficam as triplas com confiança de pelo menos 0,70.
   - Sem checkpoint, o LLM classifica.
   - Triplas que violam o domínio da relação são descartadas.
4. **Taxonomia:** o LLM organiza as entidades em subclasses, e a resposta é validada (sem ciclos, sem classes duplicando entidades, sem instância fora do ramo do seu tipo).
5. **OWL:** o owlready2 monta a ontologia, sempre com IRI absoluto.
6. **Validação lógica:** o HermiT confere a consistência. A interface só diz "validado" se o raciocinador de fato rodou.

## Requisitos

- [uv](https://docs.astral.sh/uv/). Ele instala o Python 3.12 indicado em `.python-version`.
- [Ollama](https://ollama.com/) em execução, com o modelo configurado: `ollama pull qwen3:8b`.
- Java 11 ou mais novo, para o HermiT. Se não houver Java no `PATH`, o OMAKER procura em `OMAKER_JAVA`, `JAVA_HOME`, Program Files e no JRE que vem com o Protégé (caminho informado nas Configurações).
- [Protégé](https://protege.stanford.edu/), opcional, para abrir as ontologias geradas.

Na primeira execução, os modelos do Hugging Face são baixados: SpanBERT (cerca de 410 MB), NER (cerca de 250 MB) e Sentence-BERT.

## Instalação

```bash
git clone https://github.com/jvictordbv/OMAKER.git
cd OMAKER
uv sync --extra dev
```

## Uso

A partir da pasta do repositório:

```bash
uv run python -m omaker
```

O comando `uv run python OMAKER.py` também funciona.

Na interface:
1. Em **Configurações**, escolha o modelo do LLM (o nome exato que aparece em `ollama list`, por exemplo `qwen3:8b-q4_K_M`), a pasta de destino e, opcionalmente, o caminho do `Protege.exe`.
2. Em **Gerador de Ontologia**, informe o nome do arquivo, cole o texto (em inglês) e clique em processar.
3. O log mostra cada etapa. Ao final, a mensagem diz se a ontologia foi validada, e o botão **Abrir no Protégé** fica disponível.

## Configuração

Variáveis de ambiente opcionais, lidas na hora do uso:

| Variável | Padrão | Para quê |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Endereço do Ollama |
| `OMAKER_ENTITIES` | `both` | De onde vêm as entidades: `ner`, `llm` ou `both` |
| `OMAKER_CHECKPOINT` | `omaker_pure.pt` na raiz | Checkpoint do classificador PURE |
| `OMAKER_LLM_SEED` | (nenhuma) | Semente enviada ao Ollama |
| `OMAKER_JAVA` | (procura automática) | `java.exe` usado pelo HermiT |

As preferências da interface (modelo, temperatura, pastas, Protégé) ficam salvas pelo próprio programa.

## Treino e avaliação do modelo

Treino do classificador de relações (PURE):

```bash
uv run python -m omaker.relations.train --config configs/pure_base.toml
```

Cada treino grava em `runs/<data>-<nome>/`:
- a configuração usada;
- a divisão fixa em treino, validação e teste, com manifesto e hash dos dados;
- as métricas: micro-F1 sem `no_relation`, com intervalo de confiança de 95% (o teste é avaliado uma única vez);
- um relatório;
- o checkpoint.

O checkpoint usado pela interface só é substituído com `--install`.

Se o treino cair (falta de energia, Ctrl+C), retome de onde parou:

```bash
uv run python -m omaker.relations.train --resume runs/<pasta-do-treino>
```

O treino grava um ponto de retomada (`last.pt`) a cada 50 passos (`save_every_steps` na configuração) e no fim de cada época. A retomada refaz a mesma ordem dos lotes e chega ao mesmo resultado de um treino sem queda. O `last.pt` é apagado quando o treino termina.

### Treino com o BioRED

O [BioRED](https://ftp.ncbi.nlm.nih.gov/pub/lu/BioRED/) (600 resumos do PubMed, com a divisão oficial em treino, validação e teste) é convertido para o esquema do OMAKER:

- químico vira `DRUG`, doença vira `DISEASE`;
- `Positive_Correlation` vira `causes`, `Negative_Correlation` vira `treats`;
- cada par químico e doença na mesma frase vira um exemplo; pares com outro tipo de relação (como `Association`) ficam de fora, e pares sem relação viram `no_relation`.

O BioRED anota as relações por resumo, não por frase, então parte dos rótulos é ruído. Para medir isso, o comando grava uma amostra para conferência manual (`revisao_mapeamento.csv`).

```bash
uv run python -m omaker.relations.biored --download --review-sample 100
uv run python -m omaker.relations.train --config configs/pure_biored.toml
```

O download vai para `data/biored/` (fora do git) e não é refeito se os arquivos já existirem.

Avaliação de ponta a ponta, com casamento estrito, contra os baselines:

```bash
uv run python -m omaker.evaluation.e2e --systems llm ner+llm pure both+pure
```

Se a avaliação cair no meio, `--resume runs/<pasta>` avalia só os sistemas que faltam, desde que o modelo, o gabarito e o checkpoint sejam os mesmos.

O gabarito fica em `omaker/evaluation/gold/samples.json`. O LLM roda com temperatura 0 e semente fixa, e o relatório aponta frases do gabarito que estejam nos dados de treino do PURE.

> O dataset de treino atual (`omaker/relations/train_relations.json`, 31 frases) serve para verificar o pipeline, não para tirar conclusões. A escolha do dataset de avaliação está em aberto.

## Estrutura do projeto

```text
omaker/
  domain/       rótulos, tipos de entidade, utilidades de texto
  nlp/          NER biomédico, pares candidatos, sinônimos
  llm/          cliente do Ollama, entidades, relações e taxonomia pelo LLM
  relations/    modelo PURE, dados, configuração e treino
  evaluation/   métricas e avaliação de ponta a ponta
  ontology/     construção do OWL, alinhamento, IRI, Java/HermiT, Protégé
  pipeline/     o motor que liga as etapas
  ui/           interface PySide6 (uma página por arquivo em ui/pages/)
  resources/    symp.owl (Symptom Ontology)
  config.py     variáveis de ambiente
configs/        configurações de treino
scripts/        utilitários (pipeline real num texto, janela de sinônimos, teste do NER)
tests/          suíte pytest
```

## Testes e qualidade

```bash
uv run pytest -q -m "not slow and not ollama"   # suíte rápida (a mesma do CI)
uv run ruff check .
```

- Os testes marcados `slow` baixam modelos.
- Os marcados `ollama` precisam do Ollama real.
- O CI (GitHub Actions) roda o lint e a suíte rápida no Windows a cada push e pull request.

## Contribuindo

Contribuições são bem-vindas. Leia o [guia de contribuição](CONTRIBUTING.md): ele cobre o ambiente, o fluxo de branches e pull requests, o padrão de commits e o que um PR precisa ter. As pessoas que contribuíram estão em [CONTRIBUTORS.md](CONTRIBUTORS.md).

## Como citar

Se usar o OMAKER num trabalho acadêmico, cite:

```bibtex
@mastersthesis{barbosa2026omaker,
  author = {João Victor Ferreira Barbosa},
  title  = {OMAKER: Ontology Mapping \& Knowledge Engineering Resource},
  school = {Universidade Federal de Pernambuco (UFPE)},
  year   = {2026},
  type   = {Projeto de Mestrado}
}
```

O arquivo [`CITATION.cff`](CITATION.cff) traz os mesmos dados no formato lido pelo GitHub ("Cite this repository").

## Licença

O repositório ainda não tem uma licença definida. Até que uma seja escolhida pelo autor, os direitos de uso, cópia e distribuição do código não estão concedidos.
