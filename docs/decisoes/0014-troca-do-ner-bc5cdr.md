# 0014. Troca do NER por um modelo treinado no BC5CDR

- **Status:** Proposta
- **Data:** 2026-11-12
- **Decidido por:** proposta do Gustavo; a decisão é do João Victor e ainda não foi tomada

## Contexto

Na avaliação de ponta a ponta com o teste do BioRED ([0006](0006-avaliacao-com-teste-do-biored.md)), o sistema `pure` (entidades só do NER, relações pelo PURE) teve F1 estrito de 0,13. A análise dos erros mostrou que cerca de 84% vinham das entidades, e não do classificador:

| Tipo de erro do `pure` | Quantos |
|---|---|
| Entidade com nome cortado ("QT syndrome" em vez de "long QT syndrome") | 158 |
| Termo que não é entidade ("mutations", "symptoms", "current") | 125 |
| Par fora do escopo do BioRED (doença e doença, gene) | 52 |
| Relação errada ou par sem relação (erro do PURE) | 18 |

O NER atual, `d4data/biomedical-ner-all`, foi treinado em relatos de casos clínicos e erra muito em resumos científicos. Medido contra as 1.671 menções de químicos e doenças do teste do BioRED, com início e fim exatos:

| Modelo | Licença | P | R | F1 |
|---|---|---|---|---|
| `d4data/biomedical-ner-all` (atual) | Apache-2.0 | 0,455 | 0,372 | 0,409 |
| `judithrosell/BC5CDR_PubMedBERT_NER` (candidato) | MIT | 0,781 | 0,841 | 0,810 |

## Decisão

Proposta, ainda não aplicada ao código:

- Trocar o NER padrão por `judithrosell/BC5CDR_PubMedBERT_NER`, tornando o modelo configurável.
- Como o BC5CDR só anota químicos e doenças, tipar como `SYMPTOM` as doenças que casam com rótulos ou sinônimos exatos da Symptom Ontology (`omaker/resources/symp.owl`), com o mesmo índice usado no alinhamento ([0012](0012-atualizacao-alinhada-a-hierarquia.md)).
- Refazer a avaliação de ponta a ponta antes de aceitar.

A proposta depende desse teste e do OK do João.

## Alternativas consideradas

- **Manter o NER atual com pós-processamento** (juntar modificadores, tratar parênteses, lista de termos genéricos). Medido: F1 de 0,409 para 0,430. Rende pouco.
- **Outros modelos treinados no BC5CDR.** `ghadeermobasher/BC5CDR-Chemical-Disease-balanced-BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext` teve F1 0,803, mas sem licença declarada. `Francesco-A/BiomedNLP-PubMedBERT-base-uncased-abstract-bc5cdr-ner-v1` (MIT) teve 0,777.
- **Manter o NER atual só para sintomas**, ao lado do novo. Preserva o tipo `SYMPTOM` como hoje, mas mantém dois modelos na memória e no download.

## Consequências

Esperadas, se a proposta for aceita.

### Positivas

- O F1 do NER dobra (0,409 para 0,810): químico 0,846 e doença 0,779, contra 0,480 e 0,335.
- O `pure` e o `both+pure`, hoje os piores sistemas (0,13 e 0,09), devem subir, já que o NER é a principal fonte de erro.

### Negativas e riscos

- **Viés da comparação.** O BC5CDR e o BioRED são do NCBI e seguem critérios de anotação parecidos. Parte do ganho pode ser concordância de estilo de anotação, e não qualidade em texto de outra origem.
- **Tipo SYMPTOM.** A tipagem pela Symptom Ontology só reconhece sintomas com rótulo ou sinônimo exato nela; os demais viram `DISEASE`. Isso muda quais pares são classificados (`ALLOWED_TYPE_PAIRS`).
- **Tipo GENE.** O modelo não reconhece genes; o tipo deixaria de vir do NER e passaria a depender só do LLM.
- A troca exige refazer a avaliação de ponta a ponta, que é longa.

## Referências

- `omaker/nlp/ner.py` (`BiomedicalNER`), `omaker/domain/labels.py` (`NER_MODEL_NAME`, `ALLOWED_TYPE_PAIRS`), `omaker/evaluation/ner_biored.py`, `omaker/ontology/alignment.py`.
- Testes da medição: `tests/test_ner_biored.py::test_gold_has_only_chemicals_and_diseases`, `tests/test_ner_biored.py::test_exact_span_match_with_per_type_scores`, `tests/test_ner_biored.py::test_hf_labels_map_to_gold_types`.
- [PR #15](https://github.com/jvictordbv/OMAKER/pull/15) (gabarito do BioRED), [PR #18](https://github.com/jvictordbv/OMAKER/pull/18) (medição do NER no repositório, integrada em 2026-11-24). Para reproduzir: `uv run python -m omaker.evaluation.ner_biored [--model judithrosell/BC5CDR_PubMedBERT_NER]`.
- Notas internas do projeto: registro do experimento do NER contra as menções do BioRED (2026-11-12).
