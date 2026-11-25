# Registros de decisão

Esta pasta guarda os registros de decisão do OMAKER. Cada registro descreve uma escolha que muda a forma do sistema: o problema, o que foi decidido, as alternativas que ficaram de fora e o preço da escolha. O objetivo é que alguém que chegue ao projeto daqui a um ano entenda por que o código é como é, sem precisar reconstruir a conversa que levou a ele.

## Quando escrever um registro

Escreva um registro quando a decisão:

- muda a arquitetura, o modelo, os dados de treino ou a forma de avaliar;
- muda o que o usuário instala, baixa ou aceita (distribuição, licença, idioma);
- muda o fluxo de trabalho da equipe;
- teria de ser explicada de novo a cada pessoa que perguntasse "por que não fizeram de outro jeito?".

Correções de defeito, refatorações e ajustes de interface não precisam de registro: o pull request basta.

## Como numerar

- O nome do arquivo é `NNNN-slug.md`: quatro dígitos, em sequência, e um slug curto em minúsculas, com hífens.
- O número nunca é reaproveitado, nem quando o registro é descartado.
- O título do arquivo segue o modelo `# NNNN. Título`.

## Estrutura de um registro

Cada registro tem, nesta ordem: Status, Data, Decidido por, Contexto, Decisão, Alternativas consideradas, Consequências (positivas; negativas e riscos) e Referências. A data é a da decisão ou, quando ela só ficou firme no código, a do pull request que a integrou.

## Ciclo de status

| Status | Significado |
|---|---|
| Proposta | Escrita e em discussão. O código ainda não segue a decisão. |
| Aceita | Decidida por quem tem a palavra sobre o assunto e refletida no código ou no processo. |
| Substituída por NNNN | Valeu por um tempo e foi trocada por outra decisão, registrada em NNNN. O texto antigo fica como está, para o histórico. |
| Descartada | Proposta que não foi aceita. Fica na pasta, com o motivo. |

Um registro aceito não é reescrito. Se a decisão muda, escreve-se um registro novo, e o antigo passa a "Substituída por NNNN".

## Índice

| Id | Título | Status | Data |
|---|---|---|---|
| [0001](0001-pipeline-em-ingles.md) | Pipeline em inglês, com aviso na interface | Aceita | 2026-11-12 |
| [0002](0002-llm-local-ollama.md) | LLM local pelo Ollama | Aceita | 2026-11-09 |
| [0003](0003-entidades-ner-e-llm.md) | Entidades do NER e do LLM, juntas | Aceita | 2026-11-09 |
| [0004](0004-classificador-pure-marcadores-tipados.md) | Classificador de relações PURE com marcadores tipados | Aceita | 2026-10-20 |
| [0005](0005-biored-como-dados-de-treino.md) | BioRED como dados de treino do classificador de relações | Aceita | 2026-11-12 |
| [0006](0006-avaliacao-com-teste-do-biored.md) | Avaliação com o conjunto de teste do BioRED | Aceita | 2026-11-12 |
| [0007](0007-calibracao-por-temperatura.md) | Calibração da confiança por temperatura | Aceita | 2026-11-24 |
| [0008](0008-executavel-leve-com-download.md) | Executável leve, com download dos modelos | Aceita | 2026-11-12 |
| [0009](0009-checkpoint-publicado-sem-texto.md) | Checkpoint publicado sem as frases de treino | Aceita | 2026-11-24 |
| [0010](0010-licenca-agpl.md) | Licença AGPL-3.0-only | Aceita | 2026-11-24 |
| [0011](0011-fluxo-de-branches-e-ci.md) | Só a main, branches curtos, CI e tags de versão | Aceita | 2026-11-09 |
| [0012](0012-atualizacao-alinhada-a-hierarquia.md) | Atualização alinhada à hierarquia da ontologia externa | Aceita | 2026-11-12 |
| [0013](0013-limite-de-tokens-do-llm.md) | Limite de tokens na resposta do LLM | Aceita | 2026-11-12 |
| [0014](0014-troca-do-ner-bc5cdr.md) | Troca do NER por um modelo treinado no BC5CDR | Proposta | 2026-11-12 |
| [0015](0015-otimizacao-do-prompt-com-dspy.md) | Otimização do prompt de relações com DSPy | Proposta | 2026-11-25 |

A visão de conjunto das decisões, ligada à arquitetura, está em [seção 09 da documentação de arquitetura](../arquitetura/09-decisoes.md).
