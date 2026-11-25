# 0003. Entidades do NER e do LLM, juntas

- **Status:** Aceita
- **Data:** 2026-11-09
- **Decidido por:** João Victor (pipeline híbrido, commit `04ddc4b`); mantido como padrão na reestruturação

## Contexto

O pipeline precisa achar fármacos, doenças, sintomas e genes no texto antes de classificar relações. Há duas fontes possíveis, com defeitos opostos:

- o NER biomédico (`d4data/biomedical-ner-all`) é rápido e determinístico, mas fraco: na frase "Aspirin prevents stroke. Chemotherapy treats the tumor but causes nausea.", achou só "Aspirin" e "Chemotherapy" (revisão de 2026-11-09);
- o LLM acha mais termos, mas pode inventar ou deformar nomes.

## Decisão

- A origem das entidades é configurável por `OMAKER_ENTITIES`: `ner`, `llm` ou `both`. O padrão é `both`.
- Toda entidade proposta pelo LLM é procurada no texto, por palavra inteira; o que não está no texto é descartado (`extract_entities_llm` em `omaker/llm/entities.py`).
- No modo `both`, as duas listas são unidas; quando duas menções se sobrepõem, fica a mais longa e, depois, a de maior confiança (`merge_entities`).
- No modo `both`, se o LLM falhar, o pipeline segue com as entidades do NER e registra o aviso (ver [0013](0013-limite-de-tokens-do-llm.md)).

## Alternativas consideradas

- **Só o NER.** Perde entidades em frases curtas e corta nomes compostos. É o sistema `pure` da avaliação.
- **Só o LLM.** Depende inteiramente do Ollama e é mais lento. É o sistema `llm` da avaliação.

As duas continuam disponíveis pela variável, para comparação.

## Consequências

### Positivas

- O LLM não consegue introduzir entidade que não esteja no texto.
- No gabarito pequeno (2 textos, 12 triplas), juntar as fontes ajudou: `ner+llm` teve F1 estrito de 0,71, contra 0,67 do `llm`.

### Negativas e riscos

- No gabarito maior, o teste do BioRED (100 resumos, 164 pares químico e doença), juntar as fontes piorou o resultado. Com o LLM classificando as relações, `ner+llm` fez F1 0,16 contra 0,19 do `llm`. Com o PURE, `both+pure` fez 0,09 contra 0,13 do `pure`: a revocação subiu de 0,20 para 0,34, mas a precisão caiu de 0,10 para 0,05.
- Desde a versão 0.3.0, o checkpoint do PURE é baixado na primeira execução ([0008](0008-executavel-leve-com-download.md)). Com o padrão `both`, a configuração de fábrica corresponde ao sistema `both+pure`, o de menor F1 nessa avaliação. O padrão merece ser revisto junto com a troca do NER ([0014](0014-troca-do-ner-bc5cdr.md)).
- A verificação no texto impede invenção, mas não impede termos genéricos ("symptoms", "patients"), que geram pares errados.

## Referências

- `omaker/config.py` (`entity_source`), `omaker/llm/entities.py` (`extract_entities_llm`, `merge_entities`), `omaker/pipeline/engine.py` (`HybridEngine.extrair`), `omaker/nlp/ner.py`.
- Testes: `tests/test_hybrid_engine.py::test_llm_entities_are_verified_in_text`, `tests/test_hybrid_engine.py::test_merge_both_sources`, `tests/test_hybrid_engine.py::test_llm_entity_loop_falls_back_to_ner_entities`.
- [PR #8](https://github.com/jvictordbv/OMAKER/pull/8) (sistemas de comparação, entre eles `both+pure`), [PR #15](https://github.com/jvictordbv/OMAKER/pull/15) (gabarito do BioRED).
- Notas internas do projeto: revisão do código de 2026-11-09 (item 23) e registro do experimento do PURE com o BioRED (2026-11-12, com a avaliação concluída em 2026-11-24).
