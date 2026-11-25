# Avaliação

## Propósito

Medir o OMAKER com números que sustentam conclusões: métricas de classificação com intervalo de confiança, avaliação de ponta a ponta (texto para triplas) contra baselines, com casamento estrito, gabarito do teste oficial do BioRED, retomada após queda e medição isolada do NER. Os resultados no teste do BioRED (100 resumos, 164 pares químico e doença) foram F1 estrito de 0,13 (`pure`), 0,09 (`both+pure`), 0,16 (`ner+llm`) e 0,19 (`llm`). A escolha do gabarito está no [registro de decisão 0006](../../../decisoes/0006-avaliacao-com-teste-do-biored.md).

## Requisitos

### Requisito: Micro-F1 sem no_relation (AVA-01)

O sistema DEVE calcular precisão, revocação e F1 por classe e o micro-F1 somente sobre as relações positivas, sem `no_relation`, e o macro-F1 como a média do F1 das relações positivas presentes no gabarito.

Fonte: `omaker/evaluation/metrics.py` ; Verificado por: `tests/test_metrics.py::test_micro_excludes_no_relation`, `tests/test_metrics.py::test_per_class_and_macro`

#### Cenário: acerto de no_relation não conta

- **DADO** gabarito [treats, no_relation, causes, treats] e previsão [treats, treats, no_relation, causes]
- **QUANDO** o micro-F1 é calculado
- **ENTÃO** há 1 verdadeiro positivo, 2 falsos positivos e 2 falsos negativos

### Requisito: Métricas de conjuntos (AVA-02)

O sistema DEVE comparar conjuntos de triplas com precisão, revocação e F1, devolvendo 0 (e não erro) quando não houver previsões ou gabarito.

Fonte: `omaker/evaluation/metrics.py` ; Verificado por: `tests/test_metrics.py::test_set_prf`, `tests/test_metrics.py::test_empty_predictions`

#### Cenário: nenhuma previsão

- **DADO** um gabarito com uma tripla e nenhuma previsão
- **QUANDO** as métricas são calculadas
- **ENTÃO** precisão, revocação e F1 valem 0,0

### Requisito: Intervalo de confiança reproduzível (AVA-03)

O sistema DEVE estimar o intervalo de confiança de 95% de uma métrica por bootstrap percentil, reamostrando os exemplos com reposição (1.000 reamostras no treino), com semente fixa, de modo que a mesma entrada dê o mesmo intervalo.

Fonte: `omaker/evaluation/metrics.py`, `omaker/relations/train.py` ; Verificado por: `tests/test_metrics.py::test_bootstrap_ci_contains_point_and_is_reproducible`

#### Cenário: mesma semente

- **DADO** os mesmos rótulos e a mesma semente
- **QUANDO** o intervalo é calculado duas vezes
- **ENTÃO** os dois intervalos são iguais e contêm o valor pontual

### Requisito: Sistemas comparados (AVA-04)

O sistema DEVE avaliar os sistemas `llm` (entidades e relações pelo LLM), `ner+llm` (entidades das duas fontes, relações pelo LLM), `pure` (entidades pelo NER, relações pelo PURE) e `both+pure` (entidades das duas fontes, relações pelo PURE), aplicando o ambiente de cada um durante a avaliação e restaurando o anterior depois; nos sistemas de relações pelo LLM, o checkpoint DEVE ser desviado para um caminho inexistente.

Fonte: `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_e2e.py::test_system_environment_is_applied_and_restored`, `tests/test_e2e.py::test_both_pure_system_uses_all_entities`

#### Cenário: baseline do LLM com checkpoint presente

- **DADO** um checkpoint treinado no caminho padrão e `OMAKER_ENTITIES=both` no ambiente
- **QUANDO** o sistema `llm` é avaliado
- **ENTÃO** cada documento roda com `OMAKER_ENTITIES=llm` e sem checkpoint
- **E** depois da avaliação o ambiente volta a ter `both` e o checkpoint original

### Requisito: Casamento estrito e tolerante (AVA-05)

O sistema DEVE contar como acerto estrito a tripla com sujeito e objeto iguais depois de normalizar (minúsculas, espaço e `_` iguais) e a mesma relação, e DEVE relatar à parte, só para comparação, o casamento tolerante, em que um nome contido no outro também vale.

Fonte: `omaker/evaluation/e2e.py`, `omaker/ontology/alignment.py` ; Verificado por: `tests/test_e2e.py::test_strict_vs_lenient`, `tests/test_e2e.py::test_evaluate_with_fake_extractor`

#### Cenário: nome mais curto

- **DADO** a previsão (Metformin, treats, diabetes) e o gabarito (metformin, treats, type 2 diabetes)
- **QUANDO** as triplas são comparadas
- **ENTÃO** elas casam no modo tolerante e não casam no modo estrito

### Requisito: Avaliação sem taxonomia (AVA-06)

Na avaliação de triplas, o sistema NÃO DEVE pedir a taxonomia ao LLM; cada entidade DEVE ficar na sua classe-base.

Fonte: `omaker/pipeline/engine.py`, `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_e2e.py::test_extrair_without_taxonomy_skips_llm_call`

#### Cenário: extração para avaliação

- **DADO** `OMAKER_ENTITIES=ner` e nenhum checkpoint
- **QUANDO** o motor extrai as triplas sem taxonomia
- **ENTÃO** o LLM recebe um único pedido (o das relações)
- **E** "Aspirin" fica em `Drug` e "stroke" em `Disease`

### Requisito: LLM determinístico na avaliação (AVA-07)

O sistema DEVE rodar o LLM com temperatura 0 e com a semente de `--seed` (padrão 0) durante a avaliação, restaurando depois o `OMAKER_LLM_SEED` anterior.

Fonte: `omaker/evaluation/e2e.py`, `omaker/llm/client.py` ; Verificado por: `tests/test_e2e.py::test_llm_seed_sent_to_ollama`, `tests/test_e2e.py::test_results_written_after_each_system_with_metadata`

#### Cenário: metadados da execução

- **DADO** uma avaliação iniciada
- **QUANDO** os resultados são gravados
- **ENTÃO** os metadados têm a temperatura e a semente usadas

### Requisito: Pré-condições antes de rodar (AVA-08)

O sistema DEVE conferir, antes de avaliar qualquer sistema, se existe o checkpoint exigido pelos sistemas com PURE, e DEVE falhar com o comando de treino quando ele faltar.

Fonte: `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_e2e.py::test_pure_requires_checkpoint`, `tests/test_e2e.py::test_preconditions_checked_before_running_any_system`

#### Cenário: pedido com llm e pure, sem checkpoint

- **DADO** nenhum checkpoint e os sistemas `llm` e `pure` pedidos
- **QUANDO** a avaliação começa
- **ENTÃO** ela falha antes de rodar o `llm` (que é lento), com uma mensagem que cita "omaker.relations.train"

### Requisito: Resultados gravados com metadados (AVA-09)

O sistema DEVE criar a pasta `runs/<data>-<hora>-e2e/` e gravar `results.json` logo no início e de novo depois de cada sistema, com os metadados (commit, gabarito e seu sha256, limite de documentos, modelo, temperatura, semente, checkpoint e seu sha256), e DEVE gravar `report.md` com a tabela de resultados.

Fonte: `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_e2e.py::test_results_written_after_each_system_with_metadata`

#### Cenário: falha no segundo sistema

- **DADO** os sistemas `llm` e `ner+llm`, e o Ollama cai durante o `ner+llm`
- **QUANDO** a avaliação é interrompida
- **ENTÃO** o `results.json` já tem o resultado do `llm` e todos os metadados

### Requisito: Documento com erro do LLM (AVA-10)

Quando o LLM falhar num documento (por exemplo, por chegar ao limite de tokens), o sistema DEVE contar o documento como sem previsões, registrar o erro no resultado do documento e no total de erros, avisar na saída de erro e NÃO DEVE gravar o documento no arquivo parcial, para que a retomada tente de novo.

Fonte: `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_e2e.py::test_llm_error_counts_as_no_prediction_and_is_recorded`

#### Cenário: laço num resumo

- **DADO** dois documentos, e o LLM falha no primeiro
- **QUANDO** o sistema é avaliado
- **ENTÃO** `llm_errors` vale 1 e o primeiro documento tem `error` e nenhuma previsão
- **E** os pares do primeiro documento contam como falsos negativos
- **E** o primeiro documento não vai para o parcial

### Requisito: Documento sem entidades (AVA-11)

O sistema DEVE contar como sem previsões o documento em que o motor não encontrou entidades, em vez de interromper a avaliação.

Fonte: `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_e2e.py::test_no_entities_counts_as_no_prediction`

#### Cenário: resumo sem entidades reconhecidas

- **DADO** o motor levanta o erro "No biomedical entities ..." para um documento
- **QUANDO** o documento é avaliado
- **ENTÃO** a lista de previsões dele é vazia e a avaliação continua

### Requisito: Retomada por sistema (AVA-12)

Com `--resume runs/<pasta>`, o sistema DEVE pular os sistemas já avaliados e DEVE recusar a retomada, citando o campo, quando o sha256 do gabarito, o limite de documentos, o modelo, a temperatura, a semente ou o sha256 do checkpoint forem diferentes dos gravados.

Fonte: `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_e2e.py::test_resume_skips_systems_already_evaluated`, `tests/test_e2e.py::test_resume_refuses_a_different_model`

#### Cenário: outro modelo

- **DADO** uma avaliação interrompida feita com `qwen3:8b`
- **QUANDO** o usuário retoma com outro modelo
- **ENTÃO** a retomada falha com uma mensagem que diz que "model" mudou

### Requisito: Retomada por documento (AVA-13)

O sistema DEVE gravar as previsões de cada documento num arquivo parcial por sistema (`partial-<sistema>.json`), de forma atômica, DEVE reaproveitá-las ao retomar e DEVE apagar o parcial quando o sistema terminar.

Fonte: `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_e2e.py::test_biored_run_resumes_per_document`

#### Cenário: queda no segundo de três documentos

- **DADO** três documentos e uma queda ao processar o segundo
- **QUANDO** a avaliação é retomada
- **ENTÃO** só o segundo e o terceiro são processados de novo
- **E** o resultado final tem os três documentos e o parcial não existe mais

### Requisito: Documentos fora do treino à parte (AVA-14)

No gabarito pequeno (`omaker/evaluation/gold/samples.json`), o sistema DEVE relatar o F1 estrito dos documentos marcados como fora do treino (held-out) separado do total.

Fonte: `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_e2e.py::test_gold_samples_load`, `tests/test_e2e.py::test_heldout_doc_reported_separately`

#### Cenário: um documento held-out

- **DADO** o gabarito pequeno, em que só "amostra-2" é held-out
- **QUANDO** um sistema é avaliado
- **ENTÃO** `heldout_strict` conta só os acertos e erros de "amostra-2"

### Requisito: Armadilhas do gabarito (AVA-15)

No gabarito pequeno, o sistema DEVE registrar cada previsão que cai numa armadilha (par que o texto cita sem afirmar relação, por negação ou mera co-ocorrência), com o motivo.

Fonte: `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_e2e.py::test_evaluate_with_fake_extractor`

#### Cenário: co-ocorrência tomada como relação

- **DADO** a previsão (ibuprofen, treats, headache), que é uma armadilha do gabarito
- **QUANDO** o sistema é avaliado
- **ENTÃO** `traps_hit` tem uma entrada para "ibuprofen"

### Requisito: Contaminação verificada (AVA-16)

Nos sistemas com PURE, o sistema DEVE listar as frases do gabarito que estão entre as frases de treino do checkpoint, comparando pelos sha256 das frases normalizadas (checkpoint publicado) ou pelo próprio texto (checkpoints antigos), e DEVE relatar "não verificável" quando o checkpoint não tiver nenhum dos dois.

Fonte: `omaker/evaluation/e2e.py`, `omaker/relations/data.py` ; Verificado por: `tests/test_e2e.py::test_contamination_with_pure_training_texts`, `tests/test_e2e.py::test_contamination_with_hashed_training_texts`

#### Cenário: checkpoint publicado

- **DADO** um checkpoint que guarda só o hash da frase sobre "Salbutamol"
- **QUANDO** o sistema `pure` é avaliado no gabarito pequeno
- **ENTÃO** a contaminação aponta essa frase, no documento "amostra-2"

### Requisito: Gabarito do teste do BioRED (AVA-17)

Com `--gold-biored`, o sistema DEVE usar como gabarito só o `Test.PubTator` do BioRED (100 resumos que não entram no treino), e com `--limit N` DEVE avaliar só os N primeiros documentos.

Fonte: `omaker/evaluation/biored_gold.py`, `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_biored_gold.py::test_load_biored_gold_reads_the_test_part`, `tests/test_biored_gold.py::test_gold_doc_keeps_text_and_mapped_relations`, `tests/test_e2e.py::test_biored_limit_uses_first_documents`, `tests/test_e2e.py::test_evaluate_system_scores_biored_docs`

#### Cenário: avaliação curta

- **DADO** três documentos no teste e `--limit 2`
- **QUANDO** a avaliação roda
- **ENTÃO** o resultado tem dois documentos

### Requisito: Nomes ligados a conceitos (AVA-18)

No gabarito do BioRED, o sistema DEVE ligar cada nome previsto a todos os conceitos do resumo que têm esse nome (normalizado), DEVE aceitar `causes` para `Positive_Correlation` e `treats` ou `prevents` para `Negative_Correlation`, e DEVE contar um único acerto por par do gabarito, ignorando as repetições com outros nomes.

Fonte: `omaker/evaluation/biored_gold.py` ; Verificado por: `tests/test_biored_gold.py::test_any_surface_form_of_the_concept_matches`, `tests/test_biored_gold.py::test_one_hit_per_gold_pair_even_with_several_names`

#### Cenário: dois nomes do mesmo conceito

- **DADO** "nephrotoxicity" e "acute kidney injury" são o mesmo conceito
- **QUANDO** o sistema prevê (Cisplatin, causes, nephrotoxicity) e (Cisplatin, causes, acute kidney injury)
- **ENTÃO** conta 1 acerto, e a segunda previsão é ignorada

### Requisito: Falsos positivos no BioRED (AVA-19)

No gabarito do BioRED, o sistema DEVE contar como falso positivo a relação errada, o par químico e doença sem relação anotada, a direção invertida (doença como sujeito de um químico) e a previsão com uma entidade que o BioRED não anotou.

Fonte: `omaker/evaluation/biored_gold.py` ; Verificado por: `tests/test_biored_gold.py::test_wrong_relation_unrelated_pair_and_unknown_entity_are_false_positives`, `tests/test_biored_gold.py::test_reversed_direction_is_a_false_positive`

#### Cenário: entidade genérica

- **DADO** a previsão (Cisplatin, causes, symptom), e "symptom" não está anotado
- **QUANDO** a previsão é pontuada
- **ENTÃO** ela conta como falso positivo

### Requisito: Previsões fora do escopo ignoradas (AVA-20)

No gabarito do BioRED, o sistema DEVE ignorar, sem contar como acerto nem erro, as previsões sobre pares com relação de rótulo incerto (`Association` e afins) e sobre pares que o BioRED não anota para o OMAKER (doença e doença, químico e químico), e DEVE informar quantas foram ignoradas.

Fonte: `omaker/evaluation/biored_gold.py`, `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_biored_gold.py::test_out_of_scope_predictions_are_ignored`

#### Cenário: par doença e doença

- **DADO** a previsão (diabetes, causes, hypertension)
- **QUANDO** a previsão é pontuada
- **ENTÃO** ela é ignorada e entra na contagem de ignoradas

### Requisito: Medição do NER (AVA-21)

O sistema DEVE medir um NER contra as menções de químicos e doenças do teste do BioRED, contando como acerto só a menção com início e fim exatos depois de estendida à palavra inteira; o total DEVE ignorar o tipo e o resultado por tipo DEVE exigir o tipo certo, com `DRUG` contado como químico e `DISEASE` e `SYMPTOM` como doença.

Fonte: `omaker/evaluation/ner_biored.py` ; Verificado por: `tests/test_ner_biored.py::test_gold_has_only_chemicals_and_diseases`, `tests/test_ner_biored.py::test_exact_span_match_with_per_type_scores`, `tests/test_ner_biored.py::test_snap_expands_to_the_whole_word`

#### Cenário: tipo errado, trecho certo

- **DADO** a previsão "acute kidney injury" como químico
- **QUANDO** o NER é medido
- **ENTÃO** ela conta como acerto no total e não conta como acerto em nenhum tipo

#### Cenário: nome cortado

- **DADO** a previsão "kidney injury" para a menção anotada "acute kidney injury"
- **QUANDO** o NER é medido
- **ENTÃO** ela conta como erro

### Requisito: Outro NER medido (AVA-22)

Com `--model`, o sistema DEVE medir um NER do Hugging Face com rótulos `Chemical` e `Disease` (com ou sem prefixo `B-`/`I-`, sem diferenciar maiúsculas), frase a frase e com o mesmo ajuste à palavra inteira, ignorando outros rótulos.

Fonte: `omaker/evaluation/ner_biored.py` ; Verificado por: `tests/test_ner_biored.py::test_hf_labels_map_to_gold_types`

#### Cenário: rótulo de gene

- **DADO** um NER que devolve o rótulo `Gene`
- **QUANDO** o rótulo é convertido
- **ENTÃO** ele não tem tipo e não conta como químico nem como doença

### Requisito: Otimização reproduzível do prompt de relações (AVA-23)

O sistema DEVE oferecer um comando (`python -m omaker.llm.optimize`, com o extra opcional `dspy`) que compare o prompt escrito à mão com um prompt otimizado nos mesmos dados do BioRED: exemplos de otimização tirados do treino, escolha pela validação e teste usado uma única vez no relatório final. Cada etapa DEVE ser gravada para a execução poder ser retomada com `--resume`, e a retomada DEVE recusar configurações diferentes. O prompt otimizado DEVE ser exportado em JSON simples (instrução e exemplos), e só instalado com `--install`.

Fonte: `omaker/llm/optimize.py` ; Verificado por: `tests/test_llm_optimize.py::test_baseline_program_uses_the_handwritten_instruction_without_examples`, `tests/test_llm_optimize.py::test_evaluate_scores_with_micro_f1_without_no_relation`, `tests/test_llm_optimize.py::test_full_run_writes_metrics_report_and_plain_prompt`, `tests/test_llm_optimize.py::test_resume_skips_finished_steps`, `tests/test_llm_optimize.py::test_resume_redoes_only_the_missing_step`, `tests/test_llm_optimize.py::test_resume_refuses_changed_settings`, `tests/test_llm_optimize.py::test_install_copies_the_prompt`, `tests/test_llm_optimize.py::test_export_prompt_is_plain_json_and_round_trips` (no CI, com o extra `dspy`)

#### Cenário: otimização interrompida

- **DADO** uma otimização que caiu depois da avaliação do prompt escrito à mão
- **QUANDO** o usuário roda `--resume runs/<pasta>`
- **ENTÃO** só as etapas que faltam são refeitas

### Requisito: Prompt de relações medido em lotes, como no pipeline (AVA-24)

O sistema DEVE oferecer um comando (`python -m omaker.evaluation.llm_batch`, sem o extra `dspy`) que meça o prompt escrito à mão e o prompt otimizado instalado pelo mesmo caminho do pipeline: `classify_pairs`, em lotes de 15 pares consecutivos, com a saída em JSON, nos pares de validação e de teste do BioRED, com temperatura e semente fixas. Um lote que falhe DEVE contar todo como `no_relation` e entrar na contagem de lotes com falha. Cada lote respondido DEVE ser gravado, para a execução poder ser retomada com `--resume`, e a retomada DEVE recusar configurações ou textos de prompt diferentes.

Fonte: `omaker/evaluation/llm_batch.py`, `omaker/llm/relations.py` (`classify_pairs`, parâmetro `system`) ; Verificado por: `tests/test_llm_batch_eval.py::test_batches_have_at_most_15_consecutive_pairs_in_pipeline_format`, `tests/test_llm_batch_eval.py::test_systems_are_the_handwritten_and_the_optimized_pipeline_prompts`, `tests/test_llm_batch_eval.py::test_systems_require_the_installed_optimized_prompt`, `tests/test_llm_batch_eval.py::test_full_run_scores_both_prompts_on_dev_and_test_in_batches`, `tests/test_llm_batch_eval.py::test_failed_batch_counts_as_no_relation_and_is_reported`, `tests/test_llm_batch_eval.py::test_resume_continues_from_the_next_batch`, `tests/test_llm_batch_eval.py::test_resume_refuses_changed_settings_or_prompt`

#### Cenário: medida interrompida

- **DADO** uma medida que caiu no meio dos lotes do prompt otimizado
- **QUANDO** o usuário roda `--resume runs/<pasta>`
- **ENTÃO** só os lotes que faltam são pedidos ao LLM
