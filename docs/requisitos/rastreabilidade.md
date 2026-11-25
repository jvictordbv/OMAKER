# Rastreabilidade

Liga cada requisito ao código que o implementa e aos testes que o verificam. Os testes ficam em `tests/` (o caminho na tabela omite essa pasta); os marcados (slow) baixam modelos e não rodam no CI. Ao mudar um comportamento, atualize o requisito e esta tabela no mesmo pull request.

## Sumário

- [Extração de entidades](#extração-de-entidades) (13 requisitos)
- [Extração de relações](#extração-de-relações) (11 requisitos)
- [Geração de ontologia](#geração-de-ontologia) (16 requisitos)
- [Atualização de ontologia](#atualização-de-ontologia) (9 requisitos)
- [Sinônimos](#sinônimos) (9 requisitos)
- [Integração com LLM](#integração-com-llm) (10 requisitos)
- [Modelo de relações](#modelo-de-relações) (26 requisitos)
- [Avaliação](#avaliação) (22 requisitos)
- [Interface](#interface) (11 requisitos)
- [Distribuição](#distribuição) (9 requisitos)
- [Configuração](#configuração) (11 requisitos)
- [Requisitos não funcionais](#requisitos-não-funcionais) (23 requisitos)
- [Requisitos sem teste automatizado](#requisitos-sem-teste-automatizado)
- [Requisitos com cobertura parcial](#requisitos-com-cobertura-parcial)

Total: 173 requisitos (150 funcionais e 23 não funcionais); 152 com pelo menos um teste automatizado.

## Extração de entidades

| Requisito | Módulo(s) | Teste(s) |
|---|---|---|
| [ENT-01](especificacoes/extracao-de-entidades/spec.md#requisito-fonte-das-entidades-ent-01) Fonte das entidades | `omaker/pipeline/engine.py`, `omaker/config.py` | `test_hybrid_engine.py::test_merge_both_sources`<br>`test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output` |
| [ENT-02](especificacoes/extracao-de-entidades/spec.md#requisito-ner-biomédico-por-frase-ent-02) NER biomédico por frase | `omaker/nlp/ner.py`, `omaker/domain/labels.py` | Sem teste automatizado (o modelo real é exercitado à mão por `scripts/ner_smoke.py`) |
| [ENT-03](especificacoes/extracao-de-entidades/spec.md#requisito-rótulos-aceitos-do-ner-ent-03) Rótulos aceitos do NER | `omaker/nlp/ner.py`, `omaker/pipeline/engine.py` | `test_hybrid_engine.py::test_merge_both_sources` |
| [ENT-04](especificacoes/extracao-de-entidades/spec.md#requisito-normalização-do-rótulo-do-ner-ent-04) Normalização do rótulo do NER | `omaker/nlp/ner.py` | `test_ner_labels.py::test_label_prefix_only_stripped_at_start`<br>`test_ner_labels.py::test_label_prefix_variants` |
| [ENT-05](especificacoes/extracao-de-entidades/spec.md#requisito-menção-estendida-à-palavra-inteira-ent-05) Menção estendida à palavra inteira | `omaker/nlp/ner.py` | `test_ner_biored.py::test_snap_expands_to_the_whole_word` |
| [ENT-06](especificacoes/extracao-de-entidades/spec.md#requisito-sobreposição-no-ner-ent-06) Sobreposição no NER | `omaker/nlp/ner.py` | Sem teste automatizado |
| [ENT-07](especificacoes/extracao-de-entidades/spec.md#requisito-propostas-do-llm-confirmadas-no-texto-ent-07) Propostas do LLM confirmadas no texto | `omaker/llm/entities.py` | `test_hybrid_engine.py::test_llm_entities_are_verified_in_text` |
| [ENT-08](especificacoes/extracao-de-entidades/spec.md#requisito-tipos-aceitos-do-llm-ent-08) Tipos aceitos do LLM | `omaker/llm/entities.py` | Sem teste automatizado |
| [ENT-09](especificacoes/extracao-de-entidades/spec.md#requisito-texto-do-llm-em-blocos-de-frases-ent-09) Texto do LLM em blocos de frases | `omaker/llm/entities.py` | Sem teste automatizado |
| [ENT-10](especificacoes/extracao-de-entidades/spec.md#requisito-temperatura-das-entidades-pelo-llm-ent-10) Temperatura das entidades pelo LLM | `omaker/pipeline/engine.py` | Sem teste automatizado |
| [ENT-11](especificacoes/extracao-de-entidades/spec.md#requisito-união-das-fontes-sem-sobreposição-ent-11) União das fontes sem sobreposição | `omaker/llm/entities.py` | `test_hybrid_engine.py::test_llm_entities_are_verified_in_text` |
| [ENT-12](especificacoes/extracao-de-entidades/spec.md#requisito-entidades-únicas-ent-12) Entidades únicas | `omaker/pipeline/engine.py` | `test_hybrid_engine.py::test_merge_both_sources` |
| [ENT-13](especificacoes/extracao-de-entidades/spec.md#requisito-texto-sem-entidades-ent-13) Texto sem entidades | `omaker/pipeline/engine.py` | Sem teste automatizado do motor; o tratamento desse erro na avaliação é verificado em [AVA-11](especificacoes/avaliacao/spec.md) |

## Extração de relações

| Requisito | Módulo(s) | Teste(s) |
|---|---|---|
| [REL-01](especificacoes/extracao-de-relacoes/spec.md#requisito-divisão-em-frases-rel-01) Divisão em frases | `omaker/domain/text.py` | `test_text_utils.py::test_split_keeps_title_abbreviations`<br>`test_text_utils.py::test_split_keeps_latin_and_figure_abbreviations`<br>`test_text_utils.py::test_split_still_splits_real_boundaries` |
| [REL-02](especificacoes/extracao-de-relacoes/spec.md#requisito-pares-candidatos-na-mesma-frase-rel-02) Pares candidatos na mesma frase | `omaker/nlp/pairs.py`, `omaker/domain/labels.py` | `test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output` |
| [REL-03](especificacoes/extracao-de-relacoes/spec.md#requisito-texto-sem-pares-rel-03) Texto sem pares | `omaker/pipeline/engine.py` | Sem teste automatizado |
| [REL-04](especificacoes/extracao-de-relacoes/spec.md#requisito-classificador-pure-com-marcadores-tipados-rel-04) Classificador PURE com marcadores tipados | `omaker/relations/model.py`, `omaker/domain/labels.py` | `test_relation_extractor.py::test_load_fp16_base_model_predicts`<br>`test_relation_extractor.py::test_spanbert_roundtrip` (slow)<br>`test_calibration.py::test_confidences_divide_logits_by_temperature` |
| [REL-05](especificacoes/extracao-de-relacoes/spec.md#requisito-par-com-marcador-cortado-rel-05) Par com marcador cortado | `omaker/relations/model.py` | Sem teste automatizado |
| [REL-06](especificacoes/extracao-de-relacoes/spec.md#requisito-checkpoint-incompatível-recusado-rel-06) Checkpoint incompatível recusado | `omaker/relations/model.py` | `test_relation_extractor.py::test_load_rejects_incompatible_labels` |
| [REL-07](especificacoes/extracao-de-relacoes/spec.md#requisito-escolha-do-classificador-rel-07) Escolha do classificador | `omaker/pipeline/engine.py` | `test_hybrid_engine.py::test_missing_checkpoint_is_downloaded_before_falling_back_to_the_llm` |
| [REL-08](especificacoes/extracao-de-relacoes/spec.md#requisito-limite-de-confiança-rel-08) Limite de confiança | `omaker/pipeline/engine.py`, `omaker/relations/model.py`, `omaker/domain/labels.py` | `test_hybrid_engine.py::test_pure_uses_the_calibrated_threshold` |
| [REL-09](especificacoes/extracao-de-relacoes/spec.md#requisito-classificação-pelo-llm-rel-09) Classificação pelo LLM | `omaker/llm/relations.py` | `test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output` |
| [REL-10](especificacoes/extracao-de-relacoes/spec.md#requisito-uma-tripla-por-fato-rel-10) Uma tripla por fato | `omaker/pipeline/engine.py` | Sem teste automatizado |
| [REL-11](especificacoes/extracao-de-relacoes/spec.md#requisito-domínio-das-relações-rel-11) Domínio das relações | `omaker/pipeline/engine.py`, `omaker/domain/labels.py` | `test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output` |

## Geração de ontologia

| Requisito | Módulo(s) | Teste(s) |
|---|---|---|
| [ONT-01](especificacoes/geracao-de-ontologia/spec.md#requisito-pedido-da-taxonomia-ont-01) Pedido da taxonomia | `omaker/llm/taxonomy.py` | `test_hybrid_engine.py::test_taxonomy_text_truncation_is_logged` |
| [ONT-02](especificacoes/geracao-de-ontologia/spec.md#requisito-classes-propostas-aceitas-ont-02) Classes propostas aceitas | `omaker/llm/taxonomy.py` | `test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output` |
| [ONT-03](especificacoes/geracao-de-ontologia/spec.md#requisito-pais-e-ciclos-ont-03) Pais e ciclos | `omaker/llm/taxonomy.py` | `test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output` |
| [ONT-04](especificacoes/geracao-de-ontologia/spec.md#requisito-tipagem-das-instâncias-ont-04) Tipagem das instâncias | `omaker/llm/taxonomy.py` | `test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output` |
| [ONT-05](especificacoes/geracao-de-ontologia/spec.md#requisito-disjunções-válidas-ont-05) Disjunções válidas | `omaker/llm/taxonomy.py` | `test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output` |
| [ONT-06](especificacoes/geracao-de-ontologia/spec.md#requisito-estrutura-básica-da-ontologia-ont-06) Estrutura básica da ontologia | `omaker/ontology/builder.py`, `omaker/domain/labels.py` | `test_alignment.py::test_unrelated_external_ontology_gets_omaker_bases` |
| [ONT-07](especificacoes/geracao-de-ontologia/spec.md#requisito-indivíduos-ont-07) Indivíduos | `omaker/ontology/builder.py`, `omaker/domain/text.py` | `test_alignment.py::test_new_ontology_unchanged` |
| [ONT-08](especificacoes/geracao-de-ontologia/spec.md#requisito-triplas-como-asserções-ont-08) Triplas como asserções | `omaker/ontology/builder.py` | `test_owl_builder.py::test_construir_reports_reasoner_unavailable` |
| [ONT-09](especificacoes/geracao-de-ontologia/spec.md#requisito-base-do-iri-ont-09) Base do IRI | `omaker/ontology/iri.py`, `omaker/pipeline/engine.py` | `test_iri.py::test_empty_base_falls_back_to_default`<br>`test_iri.py::test_relative_base_falls_back`<br>`test_iri.py::test_hash_base_becomes_slash`<br>`test_iri.py::test_slash_base_kept`<br>`test_iri.py::test_base_with_whitespace_falls_back` |
| [ONT-10](especificacoes/geracao-de-ontologia/spec.md#requisito-nome-no-iri-ont-10) Nome no IRI | `omaker/ontology/iri.py` | `test_iri.py::test_reserved_chars_removed_accents_kept`<br>`test_iri.py::test_name_only_reserved_chars`<br>`test_iri.py::test_construir_writes_absolute_iri` |
| [ONT-11](especificacoes/geracao-de-ontologia/spec.md#requisito-gravação-do-arquivo-ont-11) Gravação do arquivo | `omaker/pipeline/engine.py`, `omaker/ontology/builder.py` | `test_owl_builder.py::test_construir_reports_reasoner_unavailable` |
| [ONT-12](especificacoes/geracao-de-ontologia/spec.md#requisito-raciocinador-sem-java-ont-12) Raciocinador sem Java | `omaker/ontology/builder.py` | `test_owl_builder.py::test_run_reasoner_unavailable_without_java`<br>`test_owl_builder.py::test_run_reasoner_without_java_explains`<br>`test_owl_builder.py::test_construir_reports_reasoner_unavailable` |
| [ONT-13](especificacoes/geracao-de-ontologia/spec.md#requisito-consistência-conferida-ont-13) Consistência conferida | `omaker/ontology/builder.py` | `test_owl_builder.py::test_run_reasoner_consistent`<br>`test_owl_builder.py::test_run_reasoner_inconsistent` |
| [ONT-14](especificacoes/geracao-de-ontologia/spec.md#requisito-localização-do-java-ont-14) Localização do Java | `omaker/ontology/java.py` | `test_java_locator.py::test_omaker_java_wins`<br>`test_java_locator.py::test_java_home_used`<br>`test_java_locator.py::test_path_used_before_program_files`<br>`test_java_locator.py::test_newest_jdk_in_roots`<br>`test_java_locator.py::test_protege_bundled_jre`<br>`test_java_locator.py::test_none_when_nothing`<br>`test_java_locator.py::test_missing_omaker_java_falls_through`<br>`test_java_locator.py::test_java_home_without_java_falls_through` |
| [ONT-15](especificacoes/geracao-de-ontologia/spec.md#requisito-caminho-do-protégé-repassado-ont-15) Caminho do Protégé repassado | `omaker/pipeline/engine.py`, `omaker/ontology/builder.py` | `test_owl_builder.py::test_gerar_ontologia_passes_protege_exe_to_find_java`<br>`test_owl_builder.py::test_atualizar_ontologia_passes_protege_exe_to_find_java` |
| [ONT-16](especificacoes/geracao-de-ontologia/spec.md#requisito-abrir-no-protégé-ont-16) Abrir no Protégé | `omaker/ontology/protege.py` | `test_protege.py::test_opens_with_argument_list`<br>`test_protege.py::test_path_with_spaces_passed_as_one_argument`<br>`test_protege.py::test_missing_exe_raises`<br>`test_protege.py::test_missing_owl_raises` |

## Atualização de ontologia

| Requisito | Módulo(s) | Teste(s) |
|---|---|---|
| [ATU-01](especificacoes/atualizacao-de-ontologia/spec.md#requisito-atualização-com-o-mesmo-motor-atu-01) Atualização com o mesmo motor | `omaker/pipeline/engine.py` | `test_hybrid_engine.py::test_atualizar_forwards_model_and_temperature`<br>`test_owl_builder.py::test_atualizar_returns_ontology_result` |
| [ATU-02](especificacoes/atualizacao-de-ontologia/spec.md#requisito-ontologia-externa-reconhecida-atu-02) Ontologia externa reconhecida | `omaker/ontology/alignment.py` | `test_alignment.py::test_new_ontology_is_not_external`<br>`test_alignment.py::test_unrelated_external_ontology_gets_omaker_bases` |
| [ATU-03](especificacoes/atualizacao-de-ontologia/spec.md#requisito-índice-de-termos-da-ontologia-externa-atu-03) Índice de termos da ontologia externa | `omaker/ontology/alignment.py` | `test_alignment.py::test_label_index_has_labels_and_synonyms`<br>`test_alignment.py::test_obsolete_classes_do_not_win_synonym_collisions` |
| [ATU-04](especificacoes/atualizacao-de-ontologia/spec.md#requisito-classes-base-reaproveitadas-atu-04) Classes-base reaproveitadas | `omaker/ontology/builder.py`, `omaker/ontology/alignment.py` | `test_alignment.py::test_symp_update_reuses_symptom_and_has_no_parallel_classes`<br>`test_alignment.py::test_unrelated_external_ontology_gets_omaker_bases` |
| [ATU-05](especificacoes/atualizacao-de-ontologia/spec.md#requisito-instância-tipada-pela-classe-existente-atu-05) Instância tipada pela classe existente | `omaker/ontology/alignment.py`, `omaker/ontology/builder.py` | `test_alignment.py::test_instance_typed_by_label`<br>`test_alignment.py::test_instance_typed_by_exact_synonym`<br>`test_alignment.py::test_match_outside_entity_branch_is_ignored` |
| [ATU-06](especificacoes/atualizacao-de-ontologia/spec.md#requisito-subclasse-proposta-reaproveitada-atu-06) Subclasse proposta reaproveitada | `omaker/ontology/builder.py`, `omaker/ontology/alignment.py` | `test_alignment.py::test_taxonomy_subclass_reuses_existing_class` |
| [ATU-07](especificacoes/atualizacao-de-ontologia/spec.md#requisito-disjunções-só-entre-classes-do-omaker-atu-07) Disjunções só entre classes do OMAKER | `omaker/ontology/builder.py` | `test_alignment.py::test_reused_class_not_in_alldisjoint`<br>`test_alignment.py::test_alldisjoint_not_repeated_on_second_update` |
| [ATU-08](especificacoes/atualizacao-de-ontologia/spec.md#requisito-atualização-idempotente-atu-08) Atualização idempotente | `omaker/ontology/builder.py` | `test_alignment.py::test_second_update_is_idempotent`<br>`test_alignment.py::test_idempotent_after_save_and_reload` |
| [ATU-09](especificacoes/atualizacao-de-ontologia/spec.md#requisito-ontologia-do-omaker-sem-alinhamento-atu-09) Ontologia do OMAKER sem alinhamento | `omaker/ontology/builder.py` | `test_alignment.py::test_new_ontology_unchanged` |
| [ATU-10](especificacoes/atualizacao-de-ontologia/spec.md#requisito-cópia-de-segurança-antes-de-sobrescrever-atu-10) Cópia de segurança antes de sobrescrever | `omaker/ontology/builder.py`, `omaker/pipeline/engine.py` | `tests/test_hybrid_engine.py::test_updater_keeps_a_backup_of_the_original_owl` |

## Sinônimos

| Requisito | Módulo(s) | Teste(s) |
|---|---|---|
| [SIN-01](especificacoes/sinonimos/spec.md#requisito-agrupamento-por-similaridade-sin-01) Agrupamento por similaridade | `omaker/nlp/synonyms.py`, `omaker/ui/workers.py` | Sem teste automatizado (o modelo real é exercitado à mão por `scripts/synonyms_gui.py` e pelo bloco principal de `omaker/nlp/synonyms.py`) |
| [SIN-02](especificacoes/sinonimos/spec.md#requisito-poucos-termos-sin-02) Poucos termos | `omaker/nlp/synonyms.py`, `omaker/ui/pages/synonyms.py` | Sem teste automatizado |
| [SIN-03](especificacoes/sinonimos/spec.md#requisito-gravação-só-com-confirmação-sin-03) Gravação só com confirmação | `omaker/ui/pages/synonyms.py` | `test_ui_synonyms.py::test_synonyms_not_written_without_confirmation`<br>`test_ui_synonyms.py::test_synonyms_written_after_confirmation` |
| [SIN-04](especificacoes/sinonimos/spec.md#requisito-cópia-na-pasta-de-destino-sin-04) Cópia na pasta de destino | `omaker/ui/pages/synonyms.py`, `omaker/ontology/builder.py` | `test_equivalences.py::test_equivalence_written_to_copy`<br>`test_ui_synonyms.py::test_existing_copy_is_announced_in_question` |
| [SIN-05](especificacoes/sinonimos/spec.md#requisito-termo-casado-com-classe-sin-05) Termo casado com classe | `omaker/ontology/builder.py`, `omaker/ontology/alignment.py` | `test_equivalences.py::test_match_ignores_case_and_underscores` |
| [SIN-06](especificacoes/sinonimos/spec.md#requisito-grupo-sem-duas-classes-sin-06) Grupo sem duas classes | `omaker/ontology/builder.py`, `omaker/ui/pages/synonyms.py` | `test_equivalences.py::test_group_with_one_match_is_skipped` |
| [SIN-07](especificacoes/sinonimos/spec.md#requisito-nada-a-gravar-sin-07) Nada a gravar | `omaker/ontology/builder.py`, `omaker/ui/pages/synonyms.py` | `test_equivalences.py::test_no_file_when_nothing_added`<br>`test_ui_synonyms.py::test_no_success_message_when_nothing_added` |
| [SIN-08](especificacoes/sinonimos/spec.md#requisito-ontologia-padrão-sin-08) Ontologia padrão | `omaker/ui/pages/synonyms.py`, `omaker/paths.py` | `test_ui_synonyms.py::test_synonyms_default_independent_of_cwd` |
| [SIN-09](especificacoes/sinonimos/spec.md#requisito-detecção-em-segundo-plano-sin-09) Detecção em segundo plano | `omaker/ui/workers.py`, `omaker/ui/pages/synonyms.py` | `test_ui_synonyms.py::test_button_reenabled_after_synonym_error`<br>`test_ui_generation.py::test_close_during_synonyms_waits_for_worker` |

## Integração com LLM

| Requisito | Módulo(s) | Teste(s) |
|---|---|---|
| [LLM-01](especificacoes/integracao-com-llm/spec.md#requisito-ollama-local-sem-chave-llm-01) Ollama local, sem chave | `omaker/llm/client.py`, `omaker/pipeline/engine.py` | `test_hybrid_engine.py::test_engine_entry_points_take_no_api_key`<br>`test_ui_pages.py::test_settings_has_no_api_key_field` |
| [LLM-02](especificacoes/integracao-com-llm/spec.md#requisito-verificação-antes-de-extrair-llm-02) Verificação antes de extrair | `omaker/llm/client.py`, `omaker/pipeline/engine.py` | `test_llm_client.py::test_check_missing_model_suggests_pull`<br>`test_llm_client.py::test_check_lists_installed_models`<br>`test_hybrid_engine.py::test_ollama_is_not_required_when_no_step_uses_the_llm`<br>`test_hybrid_engine.py::test_llm_client_is_created_once_when_needed` |
| [LLM-03](especificacoes/integracao-com-llm/spec.md#requisito-nome-exato-do-modelo-llm-03) Nome exato do modelo | `omaker/llm/client.py` | `test_llm_client.py::test_check_requires_the_exact_name_ollama_will_use` |
| [LLM-04](especificacoes/integracao-com-llm/spec.md#requisito-saída-estruturada-llm-04) Saída estruturada | `omaker/llm/client.py` | `test_llm_client.py::test_parses_think_block_and_fenced_json` |
| [LLM-05](especificacoes/integracao-com-llm/spec.md#requisito-nova-tentativa-com-o-erro-llm-05) Nova tentativa com o erro | `omaker/llm/client.py` | `test_llm_client.py::test_retries_with_parse_error_feedback`<br>`test_llm_client.py::test_raises_after_retries` |
| [LLM-06](especificacoes/integracao-com-llm/spec.md#requisito-limite-de-tokens-e-falha-rápida-em-laço-llm-06) Limite de tokens e falha rápida em laço | `omaker/llm/client.py` | `test_llm_client.py::test_output_limit_stops_a_looping_model_without_retrying` |
| [LLM-07](especificacoes/integracao-com-llm/spec.md#requisito-contexto-e-tempo-limite-llm-07) Contexto e tempo limite | `omaker/llm/client.py` | `test_llm_client.py::test_parses_think_block_and_fenced_json` |
| [LLM-08](especificacoes/integracao-com-llm/spec.md#requisito-semente-do-llm-llm-08) Semente do LLM | `omaker/llm/client.py`, `omaker/config.py` | `test_e2e.py::test_llm_seed_sent_to_ollama` |
| [LLM-09](especificacoes/integracao-com-llm/spec.md#requisito-queda-para-o-ner-llm-09) Queda para o NER | `omaker/pipeline/engine.py` | `test_hybrid_engine.py::test_llm_entity_loop_falls_back_to_ner_entities`<br>`test_hybrid_engine.py::test_llm_entity_loop_is_an_error_when_the_llm_is_the_only_source` |
| [LLM-10](especificacoes/integracao-com-llm/spec.md#requisito-cliente-substituível-llm-10) Cliente substituível | `omaker/llm/client.py`, `omaker/pipeline/engine.py` | `test_llm_protocol.py::test_clients_follow_protocol`<br>`test_llm_protocol.py::test_engine_runs_with_any_llm_client` |

## Modelo de relações

| Requisito | Módulo(s) | Teste(s) |
|---|---|---|
| [MOD-01](especificacoes/modelo-de-relacoes/spec.md#requisito-configuração-do-treino-mod-01) Configuração do treino | `omaker/relations/config.py`, `configs/pure_biored.toml` | `test_training.py::test_load_config_reads_toml_and_rejects_unknown_key`<br>`test_training.py::test_biored_config_is_valid` |
| [MOD-02](especificacoes/modelo-de-relacoes/spec.md#requisito-artefatos-de-cada-treino-mod-02) Artefatos de cada treino | `omaker/relations/train.py` | `test_training.py::test_run_writes_artifacts` |
| [MOD-03](especificacoes/modelo-de-relacoes/spec.md#requisito-exemplos-validados-mod-03) Exemplos validados | `omaker/relations/data.py` | `test_relation_data.py::test_load_current_dataset`<br>`test_relation_data.py::test_unknown_relation_is_reported_with_index`<br>`test_relation_data.py::test_unknown_type_is_reported_with_index` |
| [MOD-04](especificacoes/modelo-de-relacoes/spec.md#requisito-divisão-fixa-e-agrupada-por-texto-mod-04) Divisão fixa e agrupada por texto | `omaker/relations/data.py` | `test_relation_data.py::test_split_is_deterministic_and_disjoint_by_text`<br>`test_relation_data.py::test_split_falls_back_when_class_too_small`<br>`test_relation_data.py::test_save_and_load_roundtrip` |
| [MOD-05](especificacoes/modelo-de-relacoes/spec.md#requisito-divisão-gravada-reaproveitada-mod-05) Divisão gravada reaproveitada | `omaker/relations/train.py` | `test_training.py::test_existing_splits_are_reused` |
| [MOD-06](especificacoes/modelo-de-relacoes/spec.md#requisito-treino-reproduzível-mod-06) Treino reproduzível | `omaker/relations/train.py` | `test_training.py::test_training_is_reproducible` |
| [MOD-07](especificacoes/modelo-de-relacoes/spec.md#requisito-teste-avaliado-uma-única-vez-mod-07) Teste avaliado uma única vez | `omaker/relations/train.py` | `test_training.py::test_test_set_evaluated_once` |
| [MOD-08](especificacoes/modelo-de-relacoes/spec.md#requisito-ponto-de-retomada-mod-08) Ponto de retomada | `omaker/relations/train.py`, `omaker/relations/config.py` | `test_training.py::test_resume_after_crash_matches_uninterrupted_run` |
| [MOD-09](especificacoes/modelo-de-relacoes/spec.md#requisito-retomada-equivalente-mod-09) Retomada equivalente | `omaker/relations/train.py` | `test_training.py::test_resume_after_crash_matches_uninterrupted_run` |
| [MOD-10](especificacoes/modelo-de-relacoes/spec.md#requisito-retomada-sem-o-que-retomar-mod-10) Retomada sem o que retomar | `omaker/relations/train.py` | `test_training.py::test_resume_of_finished_run_does_nothing`<br>`test_training.py::test_resume_without_checkpoint_fails_clearly` |
| [MOD-11](especificacoes/modelo-de-relacoes/spec.md#requisito-divisão-ausente-mod-11) Divisão ausente | `omaker/relations/train.py` | `test_training.py::test_missing_splits_dir_fails_clearly` |
| [MOD-12](especificacoes/modelo-de-relacoes/spec.md#requisito-instalação-explícita-do-checkpoint-mod-12) Instalação explícita do checkpoint | `omaker/relations/train.py` | `test_training.py::test_gui_checkpoint_untouched_without_install`<br>`test_training.py::test_install_removes_a_stale_calibration` |
| [MOD-13](especificacoes/modelo-de-relacoes/spec.md#requisito-leitura-do-formato-pubtator-mod-13) Leitura do formato PubTator | `omaker/relations/biored.py` | `test_biored.py::test_parse_pubtator_reads_text_mentions_and_relations`<br>`test_biored.py::test_parse_pubtator_rejects_offsets_that_do_not_match_the_text` |
| [MOD-14](especificacoes/modelo-de-relacoes/spec.md#requisito-download-do-biored-mod-14) Download do BioRED | `omaker/relations/biored.py` | `test_biored.py::test_download_extracts_only_pubtator_and_skips_when_done`<br>`test_biored.py::test_download_interrupted_leaves_no_zip_and_retries`<br>`test_biored.py::test_download_reuses_existing_zip`<br>`test_biored.py::test_load_biored_missing_file_says_how_to_get_it` |
| [MOD-15](especificacoes/modelo-de-relacoes/spec.md#requisito-conversão-do-biored-mod-15) Conversão do BioRED | `omaker/relations/biored.py` | `test_biored.py::test_document_examples_maps_labels_per_sentence`<br>`test_biored.py::test_document_examples_use_sentence_relative_spans_and_omaker_types`<br>`test_biored.py::test_pair_split_across_sentences_gives_no_example`<br>`test_biored.py::test_load_biored_uses_official_parts`<br>`test_biored.py::test_cli_writes_splits` |
| [MOD-16](especificacoes/modelo-de-relacoes/spec.md#requisito-amostra-para-conferência-manual-mod-16) Amostra para conferência manual | `omaker/relations/biored.py` | `test_biored.py::test_review_sample_is_balanced_csv` |
| [MOD-17](especificacoes/modelo-de-relacoes/spec.md#requisito-temperatura-ajustada-na-validação-mod-17) Temperatura ajustada na validação | `omaker/relations/calibration.py` | `test_calibration.py::test_fit_temperature_recovers_overconfident_scale`<br>`test_calibration.py::test_confidences_divide_logits_by_temperature` |
| [MOD-18](especificacoes/modelo-de-relacoes/spec.md#requisito-erro-de-calibração-medido-mod-18) Erro de calibração medido | `omaker/relations/calibration.py` | `test_calibration.py::test_ece_is_zero_when_confidence_matches_accuracy`<br>`test_calibration.py::test_ece_measures_overconfidence` |
| [MOD-19](especificacoes/modelo-de-relacoes/spec.md#requisito-limite-escolhido-na-validação-mod-19) Limite escolhido na validação | `omaker/relations/calibration.py` | `test_calibration.py::test_apply_threshold_turns_low_confidence_relations_into_no_relation`<br>`test_calibration.py::test_best_threshold_drops_wrong_low_confidence_predictions` |
| [MOD-20](especificacoes/modelo-de-relacoes/spec.md#requisito-arquivo-de-calibração-ao-lado-do-checkpoint-mod-20) Arquivo de calibração ao lado do checkpoint | `omaker/relations/calibration.py`, `omaker/relations/model.py` | `test_calibration.py::test_sidecar_is_read_next_to_the_checkpoint`<br>`test_calibration.py::test_loaded_model_uses_calibration_sidecar` |
| [MOD-21](especificacoes/modelo-de-relacoes/spec.md#requisito-calibração-instalada-só-no-mesmo-modelo-mod-21) Calibração instalada só no mesmo modelo | `omaker/relations/calibration.py` | `test_calibration.py::test_install_copies_calibration_only_to_the_same_model` |
| [MOD-22](especificacoes/modelo-de-relacoes/spec.md#requisito-publicação-sem-texto-de-treino-mod-22) Publicação sem texto de treino | `omaker/relations/release.py`, `omaker/relations/data.py` | `test_download.py::test_export_strips_training_texts` |
| [MOD-23](especificacoes/modelo-de-relacoes/spec.md#requisito-download-retomável-e-conferido-mod-23) Download retomável e conferido | `omaker/relations/download.py` | `test_download.py::test_download_verifies_and_renames`<br>`test_download.py::test_download_resumes_after_a_drop`<br>`test_download.py::test_download_rejects_a_wrong_hash` |
| [MOD-24](especificacoes/modelo-de-relacoes/spec.md#requisito-garantia-do-checkpoint-na-primeira-execução-mod-24) Garantia do checkpoint na primeira execução | `omaker/relations/download.py`, `omaker/pipeline/engine.py` | `test_download.py::test_ensure_skips_when_disabled_or_present`<br>`test_download.py::test_ensure_downloads_model_and_calibration`<br>`test_download.py::test_ensure_reports_failure_without_raising` |
| [MOD-25](especificacoes/modelo-de-relacoes/spec.md#requisito-hashes-publicados-preenchidos-mod-25) Hashes publicados preenchidos | `omaker/relations/download.py` | `test_download.py::test_published_hashes_are_filled_in` |
| [MOD-26](especificacoes/modelo-de-relacoes/spec.md#requisito-download-explícito-mod-26) Download explícito | `omaker/relations/download.py` | Sem teste automatizado |
| [MOD-27](especificacoes/modelo-de-relacoes/spec.md#requisito-calibração-do-modelo-publicado-mod-27) Calibração do modelo publicado | `omaker/relations/download.py` | `tests/test_download.py::test_missing_calibration_of_the_published_model_is_downloaded_again`, `tests/test_download.py::test_calibration_is_not_downloaded_for_another_model`, `tests/test_download.py::test_calibration_failure_keeps_the_model_and_says_so` |

## Avaliação

| Requisito | Módulo(s) | Teste(s) |
|---|---|---|
| [AVA-01](especificacoes/avaliacao/spec.md#requisito-micro-f1-sem-no_relation-ava-01) Micro-F1 sem no_relation | `omaker/evaluation/metrics.py` | `test_metrics.py::test_micro_excludes_no_relation`<br>`test_metrics.py::test_per_class_and_macro` |
| [AVA-02](especificacoes/avaliacao/spec.md#requisito-métricas-de-conjuntos-ava-02) Métricas de conjuntos | `omaker/evaluation/metrics.py` | `test_metrics.py::test_set_prf`<br>`test_metrics.py::test_empty_predictions` |
| [AVA-03](especificacoes/avaliacao/spec.md#requisito-intervalo-de-confiança-reproduzível-ava-03) Intervalo de confiança reproduzível | `omaker/evaluation/metrics.py`, `omaker/relations/train.py` | `test_metrics.py::test_bootstrap_ci_contains_point_and_is_reproducible` |
| [AVA-04](especificacoes/avaliacao/spec.md#requisito-sistemas-comparados-ava-04) Sistemas comparados | `omaker/evaluation/e2e.py` | `test_e2e.py::test_system_environment_is_applied_and_restored`<br>`test_e2e.py::test_both_pure_system_uses_all_entities` |
| [AVA-05](especificacoes/avaliacao/spec.md#requisito-casamento-estrito-e-tolerante-ava-05) Casamento estrito e tolerante | `omaker/evaluation/e2e.py`, `omaker/ontology/alignment.py` | `test_e2e.py::test_strict_vs_lenient`<br>`test_e2e.py::test_evaluate_with_fake_extractor` |
| [AVA-06](especificacoes/avaliacao/spec.md#requisito-avaliação-sem-taxonomia-ava-06) Avaliação sem taxonomia | `omaker/pipeline/engine.py`, `omaker/evaluation/e2e.py` | `test_e2e.py::test_extrair_without_taxonomy_skips_llm_call` |
| [AVA-07](especificacoes/avaliacao/spec.md#requisito-llm-determinístico-na-avaliação-ava-07) LLM determinístico na avaliação | `omaker/evaluation/e2e.py`, `omaker/llm/client.py` | `test_e2e.py::test_llm_seed_sent_to_ollama`<br>`test_e2e.py::test_results_written_after_each_system_with_metadata` |
| [AVA-08](especificacoes/avaliacao/spec.md#requisito-pré-condições-antes-de-rodar-ava-08) Pré-condições antes de rodar | `omaker/evaluation/e2e.py` | `test_e2e.py::test_pure_requires_checkpoint`<br>`test_e2e.py::test_preconditions_checked_before_running_any_system` |
| [AVA-09](especificacoes/avaliacao/spec.md#requisito-resultados-gravados-com-metadados-ava-09) Resultados gravados com metadados | `omaker/evaluation/e2e.py` | `test_e2e.py::test_results_written_after_each_system_with_metadata` |
| [AVA-10](especificacoes/avaliacao/spec.md#requisito-documento-com-erro-do-llm-ava-10) Documento com erro do LLM | `omaker/evaluation/e2e.py` | `test_e2e.py::test_llm_error_counts_as_no_prediction_and_is_recorded` |
| [AVA-11](especificacoes/avaliacao/spec.md#requisito-documento-sem-entidades-ava-11) Documento sem entidades | `omaker/evaluation/e2e.py` | `test_e2e.py::test_no_entities_counts_as_no_prediction` |
| [AVA-12](especificacoes/avaliacao/spec.md#requisito-retomada-por-sistema-ava-12) Retomada por sistema | `omaker/evaluation/e2e.py` | `test_e2e.py::test_resume_skips_systems_already_evaluated`<br>`test_e2e.py::test_resume_refuses_a_different_model` |
| [AVA-13](especificacoes/avaliacao/spec.md#requisito-retomada-por-documento-ava-13) Retomada por documento | `omaker/evaluation/e2e.py` | `test_e2e.py::test_biored_run_resumes_per_document` |
| [AVA-14](especificacoes/avaliacao/spec.md#requisito-documentos-fora-do-treino-à-parte-ava-14) Documentos fora do treino à parte | `omaker/evaluation/e2e.py` | `test_e2e.py::test_gold_samples_load`<br>`test_e2e.py::test_heldout_doc_reported_separately` |
| [AVA-15](especificacoes/avaliacao/spec.md#requisito-armadilhas-do-gabarito-ava-15) Armadilhas do gabarito | `omaker/evaluation/e2e.py` | `test_e2e.py::test_evaluate_with_fake_extractor` |
| [AVA-16](especificacoes/avaliacao/spec.md#requisito-contaminação-verificada-ava-16) Contaminação verificada | `omaker/evaluation/e2e.py`, `omaker/relations/data.py` | `test_e2e.py::test_contamination_with_pure_training_texts`<br>`test_e2e.py::test_contamination_with_hashed_training_texts` |
| [AVA-17](especificacoes/avaliacao/spec.md#requisito-gabarito-do-teste-do-biored-ava-17) Gabarito do teste do BioRED | `omaker/evaluation/biored_gold.py`, `omaker/evaluation/e2e.py` | `test_biored_gold.py::test_load_biored_gold_reads_the_test_part`<br>`test_biored_gold.py::test_gold_doc_keeps_text_and_mapped_relations`<br>`test_e2e.py::test_biored_limit_uses_first_documents`<br>`test_e2e.py::test_evaluate_system_scores_biored_docs` |
| [AVA-18](especificacoes/avaliacao/spec.md#requisito-nomes-ligados-a-conceitos-ava-18) Nomes ligados a conceitos | `omaker/evaluation/biored_gold.py` | `test_biored_gold.py::test_any_surface_form_of_the_concept_matches`<br>`test_biored_gold.py::test_one_hit_per_gold_pair_even_with_several_names` |
| [AVA-19](especificacoes/avaliacao/spec.md#requisito-falsos-positivos-no-biored-ava-19) Falsos positivos no BioRED | `omaker/evaluation/biored_gold.py` | `test_biored_gold.py::test_wrong_relation_unrelated_pair_and_unknown_entity_are_false_positives`<br>`test_biored_gold.py::test_reversed_direction_is_a_false_positive` |
| [AVA-20](especificacoes/avaliacao/spec.md#requisito-previsões-fora-do-escopo-ignoradas-ava-20) Previsões fora do escopo ignoradas | `omaker/evaluation/biored_gold.py`, `omaker/evaluation/e2e.py` | `test_biored_gold.py::test_out_of_scope_predictions_are_ignored` |
| [AVA-21](especificacoes/avaliacao/spec.md#requisito-medição-do-ner-ava-21) Medição do NER | `omaker/evaluation/ner_biored.py` | `test_ner_biored.py::test_gold_has_only_chemicals_and_diseases`<br>`test_ner_biored.py::test_exact_span_match_with_per_type_scores`<br>`test_ner_biored.py::test_snap_expands_to_the_whole_word` |
| [AVA-22](especificacoes/avaliacao/spec.md#requisito-outro-ner-medido-ava-22) Outro NER medido | `omaker/evaluation/ner_biored.py` | `test_ner_biored.py::test_hf_labels_map_to_gold_types` |

## Interface

| Requisito | Módulo(s) | Teste(s) |
|---|---|---|
| [INT-01](especificacoes/interface/spec.md#requisito-páginas-da-janela-int-01) Páginas da janela | `omaker/ui/main_window.py`, `omaker/ui/pages/` | `test_ui_pages.py::test_main_window_composes_pages` |
| [INT-02](especificacoes/interface/spec.md#requisito-execução-em-segundo-plano-int-02) Execução em segundo plano | `omaker/ui/workers.py`, `omaker/ui/pages/runner.py` | `test_ui_generation.py::test_generation_runs_off_gui_thread`<br>`test_ui_generation.py::test_update_runs_off_gui_thread`<br>`test_pipeline_worker.py::test_emits_log_and_result_from_other_thread` |
| [INT-03](especificacoes/interface/spec.md#requisito-uma-execução-por-vez-int-03) Uma execução por vez | `omaker/ui/pages/runner.py` | `test_ui_generation.py::test_generate_button_disabled_while_running`<br>`test_ui_generation.py::test_generate_failure_reenables_button` |
| [INT-04](especificacoes/interface/spec.md#requisito-cancelar-int-04) Cancelar | `omaker/ui/workers.py`, `omaker/ui/pages/runner.py`, `omaker/ui/pages/generator.py`, `omaker/ui/pages/updater.py` | `test_ui_generation.py::test_cancel_generation`<br>`test_pipeline_worker.py::test_cancel_stops_at_next_log`<br>`test_pipeline_worker.py::test_cancelled_is_an_exception`<br>`test_pipeline_worker.py::test_cancel_not_swallowed_by_broad_except` |
| [INT-05](especificacoes/interface/spec.md#requisito-um-único-desfecho-int-05) Um único desfecho | `omaker/ui/workers.py` | `test_pipeline_worker.py::test_exception_becomes_falhou`<br>`test_pipeline_worker.py::test_emits_log_and_result_from_other_thread` |
| [INT-06](especificacoes/interface/spec.md#requisito-fechar-durante-uma-execução-int-06) Fechar durante uma execução | `omaker/ui/main_window.py` | `test_ui_generation.py::test_close_during_run_waits_for_worker`<br>`test_ui_generation.py::test_close_during_silent_step_does_not_block_and_closes_later`<br>`test_ui_generation.py::test_close_during_synonyms_waits_for_worker` |
| [INT-07](especificacoes/interface/spec.md#requisito-aviso-fixo-de-idioma-int-07) Aviso fixo de idioma | `omaker/ui/pages/runner.py`, `omaker/ui/pages/generator.py`, `omaker/ui/pages/updater.py` | `test_ui_generation.py::test_pages_say_the_text_must_be_in_english` |
| [INT-08](especificacoes/interface/spec.md#requisito-pergunta-quando-o-texto-não-parece-inglês-int-08) Pergunta quando o texto não parece inglês | `omaker/ui/pages/runner.py`, `omaker/domain/text.py` | `test_ui_generation.py::test_non_english_text_asks_before_generating`<br>`test_ui_generation.py::test_non_english_text_asks_before_updating`<br>`test_ui_generation.py::test_english_text_is_not_questioned`<br>`test_text_utils.py::test_english_medical_text_is_not_flagged`<br>`test_text_utils.py::test_portuguese_and_spanish_texts_are_flagged`<br>`test_text_utils.py::test_short_text_is_never_flagged` |
| [INT-09](especificacoes/interface/spec.md#requisito-mensagens-honestas-int-09) Mensagens honestas | `omaker/ui/messages.py`, `omaker/ui/pages/generator.py`, `omaker/ui/pages/updater.py` | `test_ui_messages.py::test_completion_message_never_claims_validation_when_unavailable`<br>`test_ui_messages.py::test_completion_message_consistent`<br>`test_ui_messages.py::test_completion_message_inconsistent` |
| [INT-10](especificacoes/interface/spec.md#requisito-campos-obrigatórios-int-10) Campos obrigatórios | `omaker/ui/pages/generator.py`, `omaker/ui/pages/updater.py` | Sem teste automatizado |
| [INT-11](especificacoes/interface/spec.md#requisito-botão-abrir-no-protégé-int-11) Botão Abrir no Protégé | `omaker/ui/pages/generator.py`, `omaker/ontology/protege.py` | `test_protege.py::test_open_button_starts_disabled`<br>`test_protege.py::test_open_button_shows_warning_on_oserror`<br>`test_ui_generation.py::test_generation_runs_off_gui_thread` |
| [INT-12](especificacoes/interface/spec.md#requisito-versão-na-página-sobre-int-12) Versão na página Sobre | `omaker/ui/pages/about.py` | `tests/test_ui_pages.py::test_about_page_shows_the_package_version` |

## Distribuição

| Requisito | Módulo(s) | Teste(s) |
|---|---|---|
| [DIS-01](especificacoes/distribuicao/spec.md#requisito-pontos-de-entrada-dis-01) Pontos de entrada | `omaker/__main__.py`, `OMAKER.py` | `test_entrypoint.py::test_main_returns_exec_code`<br>`test_entrypoint.py::test_legacy_entrypoint_runs_main` |
| [DIS-02](especificacoes/distribuicao/spec.md#requisito-executável-leve-dis-02) Executável leve | `OMAKER.spec`, `.github/workflows/exe.yml` | `test_packaging.py::test_spec_is_valid_python` |
| [DIS-03](especificacoes/distribuicao/spec.md#requisito-dados-do-pacote-no-executável-dis-03) Dados do pacote no executável | `OMAKER.spec` | `test_packaging.py::test_spec_lists_all_package_data` |
| [DIS-04](especificacoes/distribuicao/spec.md#requisito-licença-junto-do-executável-dis-04) Licença junto do executável | `OMAKER.spec`, `pyproject.toml`, `LICENSE` | `test_packaging.py::test_license_ships_with_the_executable` |
| [DIS-05](especificacoes/distribuicao/spec.md#requisito-verificação-do-executável-dis-05) Verificação do executável | `omaker/self_check.py`, `omaker/__main__.py` | `test_self_check.py::test_self_check_passes_from_source`<br>`test_self_check.py::test_self_check_reports_a_missing_module`<br>`test_self_check.py::test_entrypoint_runs_the_self_check_without_opening_the_window` |
| [DIS-06](especificacoes/distribuicao/spec.md#requisito-publicação-do-executável-dis-06) Publicação do executável | `.github/workflows/exe.yml` | Sem teste automatizado (o próprio fluxo do CI é a verificação) |
| [DIS-07](especificacoes/distribuicao/spec.md#requisito-modelo-na-pasta-do-usuário-dis-07) Modelo na pasta do usuário | `omaker/paths.py` | `test_paths.py::test_frozen_app_keeps_the_checkpoint_in_the_user_folder` |
| [DIS-08](especificacoes/distribuicao/spec.md#requisito-caminhos-independentes-da-pasta-corrente-dis-08) Caminhos independentes da pasta corrente | `omaker/paths.py` | `test_paths.py::test_checkpoint_path_independent_of_cwd`<br>`test_paths.py::test_project_root_holds_entrypoint_and_resource_path`<br>`test_paths.py::test_package_resource_symp_owl` |
| [DIS-09](especificacoes/distribuicao/spec.md#requisito-versão-única-dis-09) Versão única | `omaker/__init__.py`, `pyproject.toml` | `test_packaging.py::test_version_matches_pyproject` |

## Configuração

| Requisito | Módulo(s) | Teste(s) |
|---|---|---|
| [CFG-01](especificacoes/configuracao/spec.md#requisito-leitura-na-hora-do-uso-cfg-01) Leitura na hora do uso | `omaker/config.py` | `test_config.py::test_env_change_after_import_is_seen` |
| [CFG-02](especificacoes/configuracao/spec.md#requisito-endereço-do-ollama-cfg-02) Endereço do Ollama | `omaker/config.py` | `test_config.py::test_defaults`<br>`test_config.py::test_host_without_scheme_gets_http` |
| [CFG-03](especificacoes/configuracao/spec.md#requisito-fonte-das-entidades-cfg-03) Fonte das entidades | `omaker/config.py`, `omaker/pipeline/engine.py` | `test_config.py::test_entity_source_is_normalized`<br>`test_config.py::test_empty_entity_source_defaults_to_both`<br>`test_config.py::test_invalid_entity_source_raises`<br>`test_config.py::test_bad_entity_source_does_not_break_checkpoint_or_client`<br>`test_config.py::test_bad_entity_source_reported_when_generating` |
| [CFG-04](especificacoes/configuracao/spec.md#requisito-caminho-do-checkpoint-cfg-04) Caminho do checkpoint | `omaker/config.py`, `omaker/paths.py` | `test_config.py::test_checkpoint_from_env`<br>`test_paths.py::test_checkpoint_env_override`<br>`test_paths.py::test_checkpoint_path_independent_of_cwd` |
| [CFG-05](especificacoes/configuracao/spec.md#requisito-semente-do-llm-cfg-05) Semente do LLM | `omaker/config.py` | `test_e2e.py::test_llm_seed_sent_to_ollama` |
| [CFG-06](especificacoes/configuracao/spec.md#requisito-download-automático-desligável-cfg-06) Download automático desligável | `omaker/relations/download.py`, `tests/conftest.py` | `test_download.py::test_ensure_skips_when_disabled_or_present` |
| [CFG-07](especificacoes/configuracao/spec.md#requisito-java-do-hermit-cfg-07) Java do HermiT | `omaker/ontology/java.py` | `test_java_locator.py::test_omaker_java_wins`<br>`test_java_locator.py::test_missing_omaker_java_falls_through` |
| [CFG-08](especificacoes/configuracao/spec.md#requisito-preferências-gravadas-cfg-08) Preferências gravadas | `omaker/ui/pages/settings.py`, `omaker/ui/pages/metadata.py` | `test_ui_pages.py::test_settings_readers` |
| [CFG-09](especificacoes/configuracao/spec.md#requisito-valores-padrão-das-preferências-cfg-09) Valores padrão das preferências | `omaker/ui/pages/settings.py`, `omaker/llm/client.py` | `test_ui_pages.py::test_settings_keeps_default_model_when_only_gemini_saved` |
| [CFG-10](especificacoes/configuracao/spec.md#requisito-restos-de-versões-antigas-cfg-10) Restos de versões antigas | `omaker/ui/pages/settings.py` | `test_ui_pages.py::test_settings_drops_old_gemini_models`<br>`test_ui_pages.py::test_settings_keeps_default_model_when_only_gemini_saved`<br>`test_ui_pages.py::test_settings_has_no_api_key_field` |
| [CFG-11](especificacoes/configuracao/spec.md#requisito-modelo-informado-pelo-usuário-cfg-11) Modelo informado pelo usuário | `omaker/ui/pages/settings.py` | Sem teste automatizado |

## Requisitos não funcionais

| Requisito | Módulo(s) | Teste(s) |
|---|---|---|
| [RNF-01](nao-funcionais.md#requisito-texto-processado-só-na-máquina-rnf-01) Texto processado só na máquina | `omaker/llm/client.py`, `omaker/relations/download.py`, `omaker/relations/biored.py`, `omaker/config.py` | `test_llm_protocol.py::test_engine_runs_with_any_llm_client` |
| [RNF-02](nao-funcionais.md#requisito-nenhum-serviço-de-nuvem-nem-chave-de-api-rnf-02) Nenhum serviço de nuvem nem chave de API | `omaker/pipeline/engine.py`, `omaker/ui/pages/settings.py` | `test_hybrid_engine.py::test_engine_entry_points_take_no_api_key`<br>`test_ui_pages.py::test_settings_has_no_api_key_field` |
| [RNF-03](nao-funcionais.md#requisito-modelo-publicado-sem-texto-de-terceiros-rnf-03) Modelo publicado sem texto de terceiros | `omaker/relations/release.py`, `omaker/evaluation/e2e.py` | `test_download.py::test_export_strips_training_texts`<br>`test_e2e.py::test_contamination_with_hashed_training_texts` |
| [RNF-04](nao-funcionais.md#requisito-treino-reproduzível-rnf-04) Treino reproduzível | `omaker/relations/train.py`, `omaker/relations/data.py` | `test_training.py::test_training_is_reproducible`<br>`test_relation_data.py::test_split_is_deterministic_and_disjoint_by_text`<br>`test_training.py::test_existing_splits_are_reused` |
| [RNF-05](nao-funcionais.md#requisito-avaliação-reproduzível-e-rastreável-rnf-05) Avaliação reproduzível e rastreável | `omaker/evaluation/e2e.py` | `test_e2e.py::test_results_written_after_each_system_with_metadata`<br>`test_e2e.py::test_llm_seed_sent_to_ollama`<br>`test_e2e.py::test_resume_refuses_a_different_model` |
| [RNF-06](nao-funcionais.md#requisito-experimentos-registrados-rnf-06) Experimentos registrados | `omaker/relations/train.py` | `test_training.py::test_run_writes_artifacts`<br>`test_training.py::test_test_set_evaluated_once` |
| [RNF-07](nao-funcionais.md#requisito-windows-e-python-312-rnf-07) Windows e Python 3.12 | `pyproject.toml`, `.python-version`, `.github/workflows/ci.yml`, `.github/workflows/exe.yml` | Fluxos do CI (`runs-on: windows-latest`) |
| [RNF-08](nao-funcionais.md#requisito-independência-da-pasta-corrente-rnf-08) Independência da pasta corrente | `omaker/paths.py`, `omaker/relations/train.py` | `test_paths.py::test_checkpoint_path_independent_of_cwd`<br>`test_ui_synonyms.py::test_synonyms_default_independent_of_cwd` |
| [RNF-09](nao-funcionais.md#requisito-caminhos-com-acento-rnf-09) Caminhos com acento | `pyproject.toml` | Sem teste automatizado (o repositório é desenvolvido numa pasta com acento) |
| [RNF-10](nao-funcionais.md#requisito-retomada-de-treino-avaliação-e-downloads-rnf-10) Retomada de treino, avaliação e downloads | `omaker/relations/train.py`, `omaker/evaluation/e2e.py`, `omaker/relations/download.py`, `omaker/relations/biored.py` | `test_training.py::test_resume_after_crash_matches_uninterrupted_run`<br>`test_e2e.py::test_biored_run_resumes_per_document`<br>`test_e2e.py::test_resume_skips_systems_already_evaluated`<br>`test_download.py::test_download_resumes_after_a_drop`<br>`test_biored.py::test_download_interrupted_leaves_no_zip_and_retries` |
| [RNF-11](nao-funcionais.md#requisito-gravações-atômicas-rnf-11) Gravações atômicas | `omaker/relations/train.py`, `omaker/evaluation/e2e.py`, `omaker/relations/download.py`, `omaker/relations/biored.py` | `test_download.py::test_download_verifies_and_renames`<br>`test_biored.py::test_download_interrupted_leaves_no_zip_and_retries` |
| [RNF-12](nao-funcionais.md#requisito-falha-rápida-do-llm-em-laço-rnf-12) Falha rápida do LLM em laço | `omaker/llm/client.py` | `test_llm_client.py::test_output_limit_stops_a_looping_model_without_retrying` |
| [RNF-13](nao-funcionais.md#requisito-degradação-sem-internet-ou-sem-java-rnf-13) Degradação sem internet ou sem Java | `omaker/relations/download.py`, `omaker/pipeline/engine.py`, `omaker/ontology/builder.py`, `omaker/ui/messages.py` | `test_download.py::test_ensure_reports_failure_without_raising`<br>`test_hybrid_engine.py::test_missing_checkpoint_is_downloaded_before_falling_back_to_the_llm`<br>`test_owl_builder.py::test_construir_reports_reasoner_unavailable`<br>`test_ui_messages.py::test_completion_message_never_claims_validation_when_unavailable` |
| [RNF-14](nao-funcionais.md#requisito-interface-responsiva-rnf-14) Interface responsiva | `omaker/ui/workers.py`, `omaker/ui/main_window.py` | `test_ui_generation.py::test_close_during_silent_step_does_not_block_and_closes_later`<br>`test_ui_generation.py::test_generation_runs_off_gui_thread` |
| [RNF-15](nao-funcionais.md#requisito-tamanho-do-executável-e-dos-modelos-rnf-15) Tamanho do executável e dos modelos | `OMAKER.spec`, `.github/workflows/exe.yml`, `omaker/relations/download.py` | Fluxo `.github/workflows/exe.yml` (passo "Tamanho"); sem teste automatizado de limite de tamanho |
| [RNF-16](nao-funcionais.md#requisito-memória-e-tempo-de-treino-observados-rnf-16) Memória e tempo de treino observados | nota `06-experimentos/2026-11-12-pure-biored.md` | Sem teste automatizado (medição manual) |
| [RNF-17](nao-funcionais.md#requisito-suíte-rápida-isolada-e-sem-rede-rnf-17) Suíte rápida, isolada e sem rede | `tests/conftest.py`, `pyproject.toml` | `test_ui_synonyms.py::test_default_settings_are_isolated_in_tests` |
| [RNF-18](nao-funcionais.md#requisito-ci-com-lint-e-testes-em-todo-push-rnf-18) CI com lint e testes em todo push | `.github/workflows/ci.yml`, `pyproject.toml`, `.pre-commit-config.yaml`, `CONTRIBUTING.md` | Fluxo `.github/workflows/ci.yml` |
| [RNF-19](nao-funcionais.md#requisito-rótulos-num-só-lugar-rnf-19) Rótulos num só lugar | `omaker/domain/labels.py`, `omaker/relations/model.py` | `test_relation_extractor.py::test_load_rejects_incompatible_labels` |
| [RNF-20](nao-funcionais.md#requisito-downloads-conferidos-e-extração-segura-rnf-20) Downloads conferidos e extração segura | `omaker/relations/download.py`, `omaker/relations/biored.py` | `test_download.py::test_download_rejects_a_wrong_hash`<br>`test_download.py::test_published_hashes_are_filled_in`<br>`test_biored.py::test_download_extracts_only_pubtator_and_skips_when_done` |
| [RNF-21](nao-funcionais.md#requisito-fluxos-do-ci-com-permissões-mínimas-rnf-21) Fluxos do CI com permissões mínimas | `.github/workflows/ci.yml`, `.github/workflows/exe.yml` | Inspeção dos fluxos (sem teste automatizado) |
| [RNF-22](nao-funcionais.md#requisito-agpl-30-only-no-código-e-no-executável-rnf-22) AGPL-3.0-only no código e no executável | `LICENSE`, `pyproject.toml`, `OMAKER.spec`, `omaker/self_check.py` | `test_packaging.py::test_license_ships_with_the_executable`<br>`test_self_check.py::test_self_check_passes_from_source` |
| [RNF-23](nao-funcionais.md#requisito-entrada-em-inglês-interface-em-português-rnf-23) Entrada em inglês, interface em português | `omaker/domain/text.py`, `omaker/ui/pages/runner.py` | `test_ui_generation.py::test_pages_say_the_text_must_be_in_english`<br>`test_ui_generation.py::test_non_english_text_asks_before_generating`<br>`test_text_utils.py::test_portuguese_and_spanish_texts_are_flagged` |

## Requisitos sem teste automatizado

Estes requisitos são verificados por inspeção do código, por um fluxo do CI ou à mão. São os primeiros candidatos a ganhar teste.

| Requisito | Como é verificado hoje |
|---|---|
| [ENT-02](especificacoes/extracao-de-entidades/spec.md) NER biomédico por frase | sem teste automatizado (o modelo real é exercitado à mão por `scripts/ner_smoke.py`) |
| [ENT-06](especificacoes/extracao-de-entidades/spec.md) Sobreposição no NER | sem teste automatizado |
| [ENT-08](especificacoes/extracao-de-entidades/spec.md) Tipos aceitos do LLM | sem teste automatizado |
| [ENT-09](especificacoes/extracao-de-entidades/spec.md) Texto do LLM em blocos de frases | sem teste automatizado |
| [ENT-10](especificacoes/extracao-de-entidades/spec.md) Temperatura das entidades pelo LLM | sem teste automatizado |
| [ENT-13](especificacoes/extracao-de-entidades/spec.md) Texto sem entidades | sem teste automatizado do motor; o tratamento desse erro na avaliação é verificado em [AVA-11](especificacoes/avaliacao/spec.md) |
| [REL-03](especificacoes/extracao-de-relacoes/spec.md) Texto sem pares | sem teste automatizado |
| [REL-05](especificacoes/extracao-de-relacoes/spec.md) Par com marcador cortado | sem teste automatizado |
| [REL-10](especificacoes/extracao-de-relacoes/spec.md) Uma tripla por fato | sem teste automatizado |
| [SIN-01](especificacoes/sinonimos/spec.md) Agrupamento por similaridade | sem teste automatizado (o modelo real é exercitado à mão por `scripts/synonyms_gui.py` e pelo bloco principal de `omaker/nlp/synonyms.py`) |
| [SIN-02](especificacoes/sinonimos/spec.md) Poucos termos | sem teste automatizado |
| [MOD-26](especificacoes/modelo-de-relacoes/spec.md) Download explícito | sem teste automatizado |
| [INT-10](especificacoes/interface/spec.md) Campos obrigatórios | sem teste automatizado |
| [DIS-06](especificacoes/distribuicao/spec.md) Publicação do executável | sem teste automatizado (o próprio fluxo do CI é a verificação) |
| [CFG-11](especificacoes/configuracao/spec.md) Modelo informado pelo usuário | sem teste automatizado |
| [RNF-07](nao-funcionais.md) Windows e Python 3.12 | fluxos do CI (`runs-on: windows-latest`) |
| [RNF-09](nao-funcionais.md) Caminhos com acento | sem teste automatizado (o repositório é desenvolvido numa pasta com acento) |
| [RNF-15](nao-funcionais.md) Tamanho do executável e dos modelos | fluxo `.github/workflows/exe.yml` (passo "Tamanho"); sem teste automatizado de limite de tamanho |
| [RNF-16](nao-funcionais.md) Memória e tempo de treino observados | sem teste automatizado (medição manual) |
| [RNF-18](nao-funcionais.md) CI com lint e testes em todo push | fluxo `.github/workflows/ci.yml` |
| [RNF-21](nao-funcionais.md) Fluxos do CI com permissões mínimas | inspeção dos fluxos (sem teste automatizado) |

## Requisitos com cobertura parcial

Estes requisitos têm teste, mas parte do comportamento descrito não é exercitada por ele.

| Requisito | O que falta testar |
|---|---|
| [ENT-03](especificacoes/extracao-de-entidades/spec.md) Rótulos aceitos do NER | `tests/test_hybrid_engine.py::test_merge_both_sources` (registro das descartadas); o mapeamento e o limite de 0,5 não têm teste automatizado |
| [ENT-05](especificacoes/extracao-de-entidades/spec.md) Menção estendida à palavra inteira | sem teste automatizado em `omaker/nlp/ner.py`; a função equivalente do NER de avaliação é verificada por `tests/test_ner_biored.py::test_snap_expands_to_the_whole_word` |
| [ONT-06](especificacoes/geracao-de-ontologia/spec.md) Estrutura básica da ontologia | `tests/test_alignment.py::test_unrelated_external_ontology_gets_omaker_bases` (criação da raiz e das classes-base); as propriedades e a disjunção das classes-base não têm teste automatizado direto |
| [ONT-07](especificacoes/geracao-de-ontologia/spec.md) Indivíduos | `tests/test_alignment.py::test_new_ontology_unchanged` (indivíduo localizado pelo rótulo e tipado pela classe-base); o sufixo `_ind` não tem teste automatizado |
| [LLM-04](especificacoes/integracao-com-llm/spec.md) Saída estruturada | `tests/test_llm_client.py::test_parses_think_block_and_fenced_json`; a repetição sem `think` não tem teste automatizado |
| [LLM-07](especificacoes/integracao-com-llm/spec.md) Contexto e tempo limite | `tests/test_llm_client.py::test_parses_think_block_and_fenced_json` (`num_ctx`); o tempo limite de 600 s não tem teste automatizado |
| [CFG-09](especificacoes/configuracao/spec.md) Valores padrão das preferências | `tests/test_ui_pages.py::test_settings_keeps_default_model_when_only_gemini_saved` (modelo padrão); os demais padrões não têm teste automatizado |
| [RNF-01](nao-funcionais.md) Texto processado só na máquina | inspeção (busca por `requests` em `omaker/`); a substituição do cliente por um sem rede é verificada por `tests/test_llm_protocol.py::test_engine_runs_with_any_llm_client` |
