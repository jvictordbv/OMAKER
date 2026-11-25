# 9. Decisões

As decisões de arquitetura do OMAKER estão registradas, uma por arquivo, na pasta [../decisoes/](../decisoes/README.md). Cada registro traz o contexto, a decisão, as alternativas descartadas e as consequências. Esta seção é o índice deles; o motivo resumido de cada escolha está na [seção 4](04-estrategia-de-solucao.md), e o ciclo de status, no [README dos registros](../decisoes/README.md).

## 9.1 Registros

| Id | Título | Status | Data | Link |
|---|---|---|---|---|
| 0001 | Pipeline em inglês, com aviso na interface | Aceita | 2026-11-12 | [0001-pipeline-em-ingles.md](../decisoes/0001-pipeline-em-ingles.md) |
| 0002 | LLM local pelo Ollama | Aceita | 2026-11-09 | [0002-llm-local-ollama.md](../decisoes/0002-llm-local-ollama.md) |
| 0003 | Entidades do NER e do LLM, juntas | Aceita | 2026-11-09 | [0003-entidades-ner-e-llm.md](../decisoes/0003-entidades-ner-e-llm.md) |
| 0004 | Classificador de relações PURE com marcadores tipados | Aceita | 2026-10-20 | [0004-classificador-pure-marcadores-tipados.md](../decisoes/0004-classificador-pure-marcadores-tipados.md) |
| 0005 | BioRED como dados de treino do classificador de relações | Aceita | 2026-11-12 | [0005-biored-como-dados-de-treino.md](../decisoes/0005-biored-como-dados-de-treino.md) |
| 0006 | Avaliação com o conjunto de teste do BioRED | Aceita | 2026-11-12 | [0006-avaliacao-com-teste-do-biored.md](../decisoes/0006-avaliacao-com-teste-do-biored.md) |
| 0007 | Calibração da confiança por temperatura | Aceita | 2026-11-24 | [0007-calibracao-por-temperatura.md](../decisoes/0007-calibracao-por-temperatura.md) |
| 0008 | Executável leve, com download dos modelos | Aceita | 2026-11-12 | [0008-executavel-leve-com-download.md](../decisoes/0008-executavel-leve-com-download.md) |
| 0009 | Checkpoint publicado sem as frases de treino | Aceita | 2026-11-24 | [0009-checkpoint-publicado-sem-texto.md](../decisoes/0009-checkpoint-publicado-sem-texto.md) |
| 0010 | Licença AGPL-3.0-only | Aceita | 2026-11-24 | [0010-licenca-agpl.md](../decisoes/0010-licenca-agpl.md) |
| 0011 | Só a main, branches curtos, CI e tags de versão | Aceita | 2026-11-09 | [0011-fluxo-de-branches-e-ci.md](../decisoes/0011-fluxo-de-branches-e-ci.md) |
| 0012 | Atualização alinhada à hierarquia da ontologia externa | Aceita | 2026-11-12 | [0012-atualizacao-alinhada-a-hierarquia.md](../decisoes/0012-atualizacao-alinhada-a-hierarquia.md) |
| 0013 | Limite de tokens na resposta do LLM | Aceita | 2026-11-12 | [0013-limite-de-tokens-do-llm.md](../decisoes/0013-limite-de-tokens-do-llm.md) |
| 0014 | Troca do NER por um modelo treinado no BC5CDR | Proposta | 2026-11-12 | [0014-troca-do-ner-bc5cdr.md](../decisoes/0014-troca-do-ner-bc5cdr.md) |
| 0015 | Otimização do prompt de relações com DSPy | Proposta | 2026-11-25 | [0015-otimizacao-do-prompt-com-dspy.md](../decisoes/0015-otimizacao-do-prompt-com-dspy.md) |

Treze registros estão aceitos e um está proposto. A ordem dos números é a ordem em que os registros foram escritos, não a das datas: a data é a da decisão ou do pull request que a integrou ao código, por isso o 0004 (2026-10-20) é a decisão mais antiga.

## 9.2 Decisões por tema

| Tema | Registros | Onde a decisão aparece nesta documentação |
|---|---|---|
| Pipeline e modelos | [0001](../decisoes/0001-pipeline-em-ingles.md), [0002](../decisoes/0002-llm-local-ollama.md), [0003](../decisoes/0003-entidades-ner-e-llm.md), [0004](../decisoes/0004-classificador-pure-marcadores-tipados.md), [0013](../decisoes/0013-limite-de-tokens-do-llm.md), [0014](../decisoes/0014-troca-do-ner-bc5cdr.md) | [Seção 5](05-visao-de-blocos.md), [seção 8.5](08-conceitos-transversais.md#85-tratamento-de-erros), [seção 8.7](08-conceitos-transversais.md#87-idioma), [seção 8.8](08-conceitos-transversais.md#88-verificação-das-propostas-do-llm-no-texto) |
| Dados, treino e avaliação | [0005](../decisoes/0005-biored-como-dados-de-treino.md), [0006](../decisoes/0006-avaliacao-com-teste-do-biored.md), [0007](../decisoes/0007-calibracao-por-temperatura.md) | [Seção 8.4](08-conceitos-transversais.md#84-reprodutibilidade), [seção 10](10-requisitos-de-qualidade.md), riscos R-01 a R-05 da [seção 11](11-riscos-e-debito-tecnico.md) |
| Ontologia | [0012](../decisoes/0012-atualizacao-alinhada-a-hierarquia.md) | [Seção 6](06-visao-de-execucao.md), débito DT-16 da [seção 11](11-riscos-e-debito-tecnico.md) |
| Distribuição e publicação | [0008](../decisoes/0008-executavel-leve-com-download.md), [0009](../decisoes/0009-checkpoint-publicado-sem-texto.md), [0010](../decisoes/0010-licenca-agpl.md) | [Seção 7](07-visao-de-implantacao.md), [seção 8.9](08-conceitos-transversais.md#89-segurança-e-privacidade) |
| Processo da equipe | [0011](../decisoes/0011-fluxo-de-branches-e-ci.md) | [Seção 7.4](07-visao-de-implantacao.md#74-pipeline-de-integração-contínua), [seção 8.10](08-conceitos-transversais.md#810-testes-e-qualidade-de-código) |

## 9.3 Decisão em aberto

O registro [0014](../decisoes/0014-troca-do-ner-bc5cdr.md) propõe trocar o NER atual (`d4data/biomedical-ner-all`, F1 0,409 nas menções do teste do BioRED) pelo `judithrosell/BC5CDR_PubMedBERT_NER` (F1 0,810, licença MIT). O código ainda não segue a proposta: `NER_MODEL_NAME` em `omaker/domain/labels.py` continua apontando para o modelo atual. A decisão é do João Victor. O custo principal é que o BC5CDR não separa sintoma de doença, e o OMAKER tem o tipo `SYMPTOM`.
