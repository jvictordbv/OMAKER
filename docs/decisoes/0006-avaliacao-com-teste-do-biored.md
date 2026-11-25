# 0006. Avaliação com o conjunto de teste do BioRED

- **Status:** Aceita
- **Data:** 2026-11-12
- **Decidido por:** João Victor (avaliar com o teste oficial, na decisão D5) e Gustavo (protocolo e implementação)

## Contexto

Até a reestruturação, a avaliação não sustentava conclusões: o classificador era escolhido pelo macro-F1 em 8 exemplos de validação, não havia conjunto de teste, e a avaliação de ponta a ponta usava 2 textos com casamento por substring. O gabarito de ponta a ponta, mesmo corrigido, tem só 12 triplas, e uma frase do texto reservado estava, palavra por palavra, nos dados de treino.

O sistema tem duas perguntas a responder, que pedem medidas diferentes: quão bom é o classificador de relações sozinho, e quão bom é o pipeline inteiro, a partir do texto cru.

## Decisão

- **Classificador.** O treino usa a divisão oficial do BioRED. A época é escolhida pela validação, e o teste é avaliado uma única vez, no fim. A métrica é o micro-F1 sem `no_relation`, com intervalo de confiança por bootstrap.
- **Ponta a ponta.** O gabarito principal é o teste oficial do BioRED: 100 resumos que nunca entram no treino, com 164 pares químico e doença (104 `causes`, 60 `treats` ou `prevents`). O protocolo está em `omaker/evaluation/biored_gold.py`:
  - cada nome previsto é ligado aos conceitos anotados no resumo, e cada par conta um acerto só;
  - `Positive_Correlation` aceita `causes`; `Negative_Correlation` aceita `treats` e `prevents`;
  - relação errada, direção invertida e entidade não anotada contam como erro;
  - pares de rótulo incerto (`Association`) e pares que o BioRED não anota (doença e doença) são ignorados.
- Quatro sistemas são comparados nas mesmas condições: `llm`, `ner+llm`, `pure` e `both+pure`, com LLM em temperatura 0 e semente 0.
- A avaliação grava o resultado de cada documento e pode ser retomada de onde parou.

## Alternativas consideradas

- **Só o gabarito pequeno.** Mantido, mas não basta: com 12 triplas, a comparação entre sistemas não tem poder estatístico.
- **Comparar com os resultados publicados do BioRED.** Não é possível: a tarefa publicada é por documento e com outros rótulos.
- **SemRep gold standard como teste externo.** Previsto na proposta, se o orientador concordar; ainda não foi feito.

## Consequências

### Positivas

- O número do classificador tem intervalo estreito: micro-F1 0,739 (IC 95% 0,694 a 0,785).
- A avaliação de ponta a ponta mostrou onde está o gargalo. F1 estrito: `pure` 0,13; `both+pure` 0,09; `ner+llm` 0,16; `llm` 0,19. Cerca de 84% dos erros do `pure` vêm das entidades, não do classificador ([0014](0014-troca-do-ner-bc5cdr.md)).

### Negativas e riscos

- O gabarito é exigente e parcial: só químico e doença, nomes exatos, e qualquer entidade não anotada conta como erro. Os F1 absolutos ficam baixos e não medem `prevents`, sintomas nem genes.
- Com 164 pares e F1 entre 0,09 e 0,19, as diferenças entre sistemas são pequenas; falta o intervalo por bootstrap antes de afirmar a ordem.
- Os rótulos do BioRED vêm do resumo: parte do erro medido é ruído do gabarito.
- A avaliação completa é longa e pesada: foi interrompida várias vezes por falta de memória e só terminou em 2026-11-24.

## Referências

- `omaker/evaluation/biored_gold.py`, `omaker/evaluation/e2e.py` (`SYSTEMS`, `--gold-biored`, `--resume`), `omaker/evaluation/metrics.py`, `omaker/relations/train.py`.
- Testes: `tests/test_training.py::test_test_set_evaluated_once`, `tests/test_e2e.py::test_evaluate_system_scores_biored_docs`, `tests/test_e2e.py::test_biored_run_resumes_per_document`, `tests/test_e2e.py::test_contamination_with_pure_training_texts`.
- [PR #8](https://github.com/jvictordbv/OMAKER/pull/8) (divisão fixa, teste avaliado uma vez, métricas com intervalo, avaliação de ponta a ponta), [PR #15](https://github.com/jvictordbv/OMAKER/pull/15) (gabarito do BioRED).
- Notas internas do projeto: revisão do código de 2026-11-09 (item 8) e registro do experimento do PURE com o BioRED.
