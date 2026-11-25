# 0015. Otimização do prompt de relações com DSPy

- **Status:** Proposta
- **Data:** 2026-11-25
- **Decidido por:** Gustavo (experimento); adotar o prompt otimizado como padrão depende do resultado e do OK do João Victor

## Contexto

Sem o checkpoint do PURE, e nos sistemas `llm` e `ner+llm` da avaliação, as relações são classificadas pelo LLM local com um prompt escrito à mão (`RELATION_SYSTEM`, em `omaker/llm/relations.py`). Esse prompt nunca foi ajustado com dados: na avaliação de ponta a ponta com o teste do BioRED, o melhor sistema (`llm`) teve F1 estrito de 0,19. O BioRED convertido traz exemplos de treino e de validação que podem ser usados para escolher a instrução e os exemplos do prompt, em vez de escrevê-los à mão.

## Decisão

- Oferecer a otimização do prompt de relações com o DSPy como experimento reproduzível: `python -m omaker.llm.optimize`, com o otimizador BootstrapFewShotWithRandomSearch por padrão (MIPROv2 como opção), exemplos de otimização tirados do treino do BioRED, escolha pela validação e o teste usado uma única vez no relatório.
- O DSPy é um extra opcional (`uv sync --extra dspy`): não entra no extra `dev` nem no `.exe`.
- O resultado é exportado em JSON simples (instrução e exemplos), e o pipeline o usa sem depender do DSPy, só com `OMAKER_LLM_PROMPT=optimized`. O padrão continua o prompt escrito à mão.
- O prompt otimizado só vira o padrão se superar o escrito à mão na validação e no teste, também pelo caminho do pipeline (lotes de pares), em um novo registro de decisão.

## Alternativas consideradas

- **Ajustar o prompt à mão, por tentativa.** Barato, mas sem critério reproduzível e com risco de ajustar ao teste.
- **Treinar ou ajustar o próprio LLM.** Fora do alcance da máquina (GPU de 6 GB) e do escopo do projeto.
- **Usar só o PURE.** O PURE já é o classificador principal; o prompt do LLM continua sendo usado quando não há checkpoint e nos sistemas de comparação.

## Consequências

### Positivas

- Um critério com dados para o prompt do LLM, comparável com o prompt escrito à mão nos mesmos exemplos.
- O resultado é um arquivo de texto revisável, versionado e usado sem dependência nova.
- A execução retoma depois de uma queda (cache em disco e etapas gravadas).

### Negativas e riscos

- A otimização faz milhares de chamadas ao LLM local (de 2 a 4 horas nesta máquina).
- O otimizador mede um par por chamada, e o pipeline manda lotes de 15 pares: o ganho pode não se repetir no pipeline (débito DT-28).
- A métrica do otimizador é a acurácia por par; o relatório traz o micro-F1 sem `no_relation`.
- Os rótulos do BioRED vêm do resumo (supervisão distante, [0005](0005-biored-como-dados-de-treino.md)): o prompt pode aprender parte do ruído.
- Uma dependência a mais (o extra `dspy`) para manter no CI.

## Andamento

- 2026-11-25: primeira otimização completa (`bootstrap`, 60 pares de treino, semente 0, `qwen3:8b-q4_K_M`, DSPy 3.5.0, commit `ab33bba`). O prompt otimizado acrescenta 4 exemplos à instrução escrita à mão, sem mudar o texto dela.

| Conjunto | Prompt | P | R | micro-F1 | macro-F1 |
|---|---|---|---|---|---|
| Validação (453 pares) | Escrito à mão | 0,410 | 0,316 | 0,357 | 0,434 |
| Validação (453 pares) | Otimizado | 0,548 | 0,650 | 0,595 | 0,655 |
| Teste (385 pares, uma vez) | Escrito à mão | 0,512 | 0,444 | 0,475 | 0,496 |
| Teste (385 pares, uma vez) | Otimizado | 0,568 | 0,704 | 0,629 | 0,623 |

- O ganho vem da revocação de `causes` e `treats`. Os dois prompts erram `prevents` do mesmo jeito: o gabarito não tem nenhum par `prevents`, e todos os previstos são falsos positivos (94 no teste com o escrito à mão, 75 com o otimizado).
- O prompt foi instalado em `omaker/llm/prompts/relations_optimized.json` e só é usado com `OMAKER_LLM_PROMPT=optimized`. O padrão continua o escrito à mão até a medida pelo caminho em lotes do pipeline (DT-28).

- 2026-11-25: medida pelo caminho do pipeline (`python -m omaker.evaluation.llm_batch`, requisito AVA-24): `classify_pairs`, lotes de 15 pares, saída JSON, temperatura 0, semente 0 (`runs/20261125-055217-llm-lotes`, commit `ef8419d`).

| Conjunto | Prompt | P | R | micro-F1 | macro-F1 |
|---|---|---|---|---|---|
| Validação (453 pares) | Escrito à mão | 0,529 | 0,559 | 0,543 | 0,617 |
| Validação (453 pares) | Otimizado | 0,526 | 0,579 | 0,551 | 0,595 |
| Teste (385 pares) | Escrito à mão | 0,601 | 0,608 | 0,604 | 0,616 |
| Teste (385 pares) | Otimizado | 0,581 | 0,628 | 0,604 | 0,573 |

- O ganho medido com um par por pedido não se repete no pipeline. Em lotes, o prompt escrito à mão já sai bem melhor do que com um par por pedido (teste: 0,475 para 0,604), e o otimizado empata no micro-F1 e perde no macro-F1, por causa de `treats` (0,452 para 0,369 no teste). Nenhum lote falhou.
- Conclusão: o prompt escrito à mão continua o padrão. O otimizado fica disponível (`OMAKER_LLM_PROMPT=optimized`) e a ferramenta continua no repositório, mas otimizar com um par por pedido não serve para escolher o prompt do pipeline. Uma próxima tentativa teria de otimizar já no formato de lote (débito DT-28).

## Referências

- `omaker/llm/optimize.py`, `omaker/llm/relations.py`, `omaker/config.py` (`llm_prompt`), `pyproject.toml` (extra `dspy`), `.github/workflows/ci.yml`.
- Requisitos REL-12, CFG-12, AVA-23 e AVA-24; débitos DT-28 e DT-29.
- Testes: `tests/test_llm_optimize.py`, `tests/test_llm_relations_prompt.py`.
