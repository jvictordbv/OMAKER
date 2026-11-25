# Extração de entidades

## Propósito

Encontrar no texto as menções de fármacos (`DRUG`), sintomas (`SYMPTOM`) e doenças (`DISEASE`), com a posição de cada uma. Duas fontes podem ser combinadas: um NER biomédico e o LLM local. O LLM só propõe nomes; cada proposta precisa ser achada no texto, o que impede entidades inventadas. A escolha está no [registro de decisão 0003](../../../decisoes/0003-entidades-ner-e-llm.md).

## Requisitos

### Requisito: Fonte das entidades (ENT-01)

O sistema DEVE extrair entidades só do NER quando `OMAKER_ENTITIES` for `ner`, só do LLM quando for `llm` e das duas fontes, unidas, quando for `both`. O valor padrão e a validação da variável estão em [CFG-03](../configuracao/spec.md).

Fonte: `omaker/pipeline/engine.py`, `omaker/config.py` ; Verificado por: `tests/test_hybrid_engine.py::test_merge_both_sources`, `tests/test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output`

#### Cenário: as duas fontes unidas

- **DADO** `OMAKER_ENTITIES=both`, um NER que só reconhece "Aspirin" e "Chemotherapy" e um LLM que propõe também "stroke", "tumor", "nausea" e "fever"
- **QUANDO** o motor extrai as entidades do texto
- **ENTÃO** o log registra 6 entidades únicas
- **E** a taxonomia tem uma instância para cada uma das seis

#### Cenário: só o NER

- **DADO** `OMAKER_ENTITIES=ner`
- **QUANDO** o motor extrai as entidades
- **ENTÃO** o LLM não recebe pedido de entidades; ele só é chamado para as relações (sem classificador) e para a taxonomia

### Requisito: NER biomédico por frase (ENT-02)

O sistema DEVE rodar o NER `d4data/biomedical-ner-all` frase a frase, com agregação dos subtokens, e DEVE converter as posições de cada menção para posições no texto completo.

Fonte: `omaker/nlp/ner.py`, `omaker/domain/labels.py` ; Verificado por: `tests/test_ner_model.py::test_ner_uses_the_biomedical_model_with_subtoken_aggregation`, `tests/test_ner_model.py::test_ner_runs_sentence_by_sentence_and_offsets_count_from_the_start_of_the_text`

#### Cenário: texto com várias frases

- **DADO** um texto com duas frases e um fármaco na segunda
- **QUANDO** o NER extrai as entidades
- **ENTÃO** a menção do fármaco tem início e fim contados a partir do começo do texto, e não da segunda frase

### Requisito: Rótulos aceitos do NER (ENT-03)

O sistema DEVE aceitar do NER só os rótulos `medication` (vira `DRUG`), `sign_symptom` (vira `SYMPTOM`) e `disease_disorder` (vira `DISEASE`), com pontuação de pelo menos 0,5, e DEVE registrar no log até 10 detecções descartadas, com o rótulo e a pontuação.

Fonte: `omaker/nlp/ner.py`, `omaker/pipeline/engine.py` ; Verificado por: `tests/test_hybrid_engine.py::test_merge_both_sources` (registro das descartadas); o mapeamento e o limite de 0,5 não têm teste automatizado, `tests/test_ner_model.py::test_ner_maps_only_the_three_accepted_labels`, `tests/test_ner_model.py::test_ner_ignores_labels_outside_the_mapping_and_records_them`, `tests/test_ner_model.py::test_ner_keeps_detections_with_score_of_at_least_one_half`, `tests/test_ner_model.py::test_engine_logs_the_ignored_detection_with_label_and_score`, `tests/test_ner_model.py::test_engine_logs_at_most_ten_ignored_detections`

#### Cenário: rótulo fora do mapeamento

- **DADO** o NER marca "tumor" com o rótulo `Coreference` e pontuação 0,92
- **QUANDO** o motor extrai as entidades
- **ENTÃO** "tumor" não vira entidade pelo NER
- **E** o log mostra "[NER] ignored: 'tumor' labelled Coreference (0.92)"

#### Cenário: pontuação baixa

- **DADO** o NER marca "fever" como `sign_symptom` com pontuação 0,40
- **QUANDO** o motor extrai as entidades
- **ENTÃO** "fever" não vira entidade pelo NER e entra na lista de descartadas

### Requisito: Normalização do rótulo do NER (ENT-04)

O sistema DEVE comparar os rótulos do NER em minúsculas e remover apenas um prefixo `B-` ou `I-` no início do rótulo.

Fonte: `omaker/nlp/ner.py` ; Verificado por: `tests/test_ner_labels.py::test_label_prefix_only_stripped_at_start`, `tests/test_ner_labels.py::test_label_prefix_variants`

#### Cenário: "b-" no meio do rótulo

- **DADO** um rótulo que contém "b-" fora do início
- **QUANDO** o rótulo é normalizado
- **ENTÃO** só um prefixo inicial `B-` ou `I-` é removido, e o resto do rótulo fica intacto

### Requisito: Menção estendida à palavra inteira (ENT-05)

O sistema DEVE estender cada menção do NER até os limites da palavra (caracteres alfanuméricos vizinhos), porque o NER às vezes corta pedaços de palavra.

Fonte: `omaker/nlp/ner.py` ; Verificado por: sem teste automatizado em `omaker/nlp/ner.py`; a função equivalente do NER de avaliação é verificada por `tests/test_ner_biored.py::test_snap_expands_to_the_whole_word`, `tests/test_ner_model.py::test_ner_extends_a_cut_mention_to_the_whole_word`

#### Cenário: subtoken cortado

- **DADO** o NER marca "T syndrome" dentro de "QT syndrome"
- **QUANDO** a menção é ajustada
- **ENTÃO** a menção passa a ser "QT syndrome"

### Requisito: Sobreposição no NER (ENT-06)

O sistema DEVE eliminar menções do NER que se sobrepõem, mantendo a de maior pontuação, e DEVE devolver as menções em ordem de posição no texto.

Fonte: `omaker/nlp/ner.py` ; Verificado por: `tests/test_ner_model.py::test_ner_keeps_the_highest_scoring_of_two_overlapping_detections`, `tests/test_ner_model.py::test_ner_returns_mentions_in_text_order`

#### Cenário: duas detecções no mesmo trecho

- **DADO** duas detecções do NER que se sobrepõem, com pontuações 0,95 e 0,60
- **QUANDO** o NER devolve as entidades
- **ENTÃO** só a de 0,95 permanece

### Requisito: Propostas do LLM confirmadas no texto (ENT-07)

O sistema DEVE tratar a resposta do LLM apenas como proposta de nomes e DEVE aceitar uma proposta só se ela aparecer no texto como palavra inteira, sem diferenciar maiúsculas; cada ocorrência encontrada vira uma menção.

Fonte: `omaker/llm/entities.py` ; Verificado por: `tests/test_hybrid_engine.py::test_llm_entities_are_verified_in_text`

#### Cenário: entidade inventada

- **DADO** o LLM propõe "cancer", que não está no texto
- **QUANDO** as propostas são conferidas
- **ENTÃO** "cancer" é descartada

#### Cenário: pedaço de outra palavra

- **DADO** o LLM propõe "ever", que só aparece dentro de "fever"
- **QUANDO** as propostas são conferidas
- **ENTÃO** "ever" é descartada

#### Cenário: várias ocorrências

- **DADO** o LLM propõe "Aspirin", que aparece duas vezes no texto
- **QUANDO** as propostas são conferidas
- **ENTÃO** as duas ocorrências viram menções, cada uma com a sua posição

### Requisito: Tipos aceitos do LLM (ENT-08)

O sistema DEVE pedir ao LLM uma resposta no esquema JSON de entidades, com o tipo restrito a `DRUG`, `SYMPTOM` ou `DISEASE`, e DEVE descartar propostas com nome vazio ou com outro tipo.

Fonte: `omaker/llm/entities.py` ; Verificado por: `tests/test_llm_entities.py::test_llm_is_asked_for_the_entity_schema_with_the_three_types`, `tests/test_llm_entities.py::test_llm_proposals_with_an_unknown_type_or_an_empty_name_are_discarded`

#### Cenário: tipo desconhecido

- **DADO** o LLM devolve uma proposta com o tipo `GENE`
- **QUANDO** as propostas são lidas
- **ENTÃO** a proposta é descartada

### Requisito: Texto do LLM em blocos de frases (ENT-09)

O sistema DEVE enviar o texto ao LLM em blocos de frases inteiras de até 3.000 caracteres e DEVE manter uma única proposta por nome, sem diferenciar maiúsculas (a primeira recebida vale).

Fonte: `omaker/llm/entities.py` ; Verificado por: `tests/test_llm_entities.py::test_long_text_is_sent_in_blocks_of_whole_sentences_of_at_most_3000_chars`, `tests/test_llm_entities.py::test_a_single_sentence_longer_than_the_limit_is_sent_alone`, `tests/test_llm_entities.py::test_the_first_proposal_of_a_name_wins_regardless_of_case`

#### Cenário: texto longo

- **DADO** um texto de 7.000 caracteres
- **QUANDO** as entidades são pedidas ao LLM
- **ENTÃO** o LLM recebe vários pedidos, cada um com frases inteiras e no máximo 3.000 caracteres, salvo uma frase sozinha maior que isso

### Requisito: Temperatura das entidades pelo LLM (ENT-10)

O sistema DEVE pedir as entidades ao LLM com a temperatura configurada, limitada a no máximo 0,1.

Fonte: `omaker/pipeline/engine.py` ; Verificado por: `tests/test_engine_extraction.py::test_entities_are_asked_with_the_configured_temperature_capped_at_0_1`

#### Cenário: temperatura alta nas configurações

- **DADO** a temperatura 0,8 nas Configurações
- **QUANDO** o motor pede as entidades ao LLM
- **ENTÃO** o pedido usa a temperatura 0,1

### Requisito: União das fontes sem sobreposição (ENT-11)

O sistema DEVE dar às menções do LLM a pontuação fixa 0,75 e, ao unir as fontes, DEVE manter em cada trecho sobreposto a menção mais longa e, no empate, a de maior pontuação.

Fonte: `omaker/llm/entities.py` ; Verificado por: `tests/test_hybrid_engine.py::test_llm_entities_are_verified_in_text`

#### Cenário: menções sobrepostas

- **DADO** as menções do NER e as do LLM para o mesmo texto
- **QUANDO** as duas listas são unidas
- **ENTÃO** nenhum par de menções do resultado se sobrepõe

### Requisito: Entidades únicas (ENT-12)

O sistema DEVE manter uma entidade por forma escrita, sem diferenciar maiúsculas, com o tipo da menção de maior pontuação, e DEVE usar essa lista na taxonomia e no log; todas as menções continuam disponíveis para formar pares.

Fonte: `omaker/pipeline/engine.py` ; Verificado por: `tests/test_hybrid_engine.py::test_merge_both_sources`

#### Cenário: a mesma entidade duas vezes

- **DADO** "Aspirin" aparece duas vezes no texto
- **QUANDO** o motor conta as entidades únicas
- **ENTÃO** "Aspirin" conta uma vez na lista de entidades únicas
- **E** as duas menções podem formar pares com as outras entidades das suas frases

### Requisito: Texto sem entidades (ENT-13)

O sistema DEVE interromper a extração com o erro "No biomedical entities (drug / symptom / disease) were found in the text." quando nenhuma fonte encontrar entidades.

Fonte: `omaker/pipeline/engine.py` ; Verificado por: `tests/test_engine_extraction.py::test_generation_without_entities_fails_with_the_message_and_writes_no_owl`

#### Cenário: texto sem termos biomédicos

- **DADO** um texto que não cita fármacos, sintomas nem doenças
- **QUANDO** o usuário gera a ontologia
- **ENTÃO** a geração falha com essa mensagem e nenhum arquivo `.owl` é gravado
