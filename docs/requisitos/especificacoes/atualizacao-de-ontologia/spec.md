# Atualização de ontologia

## Propósito

Acrescentar a uma ontologia existente as entidades e relações de um texto novo. Quando a ontologia não foi gerada pelo OMAKER (por exemplo, a Symptom Ontology em `omaker/resources/symp.owl`), as entidades são alinhadas às classes que ela já tem, pelo rótulo e pelos sinônimos exatos, sem criar uma hierarquia paralela e sem inventar termos no namespace alheio. A escolha está no [registro de decisão 0012](../../../decisoes/0012-atualizacao-alinhada-a-hierarquia.md).

## Requisitos

### Requisito: Atualização com o mesmo motor (ATU-01)

O sistema DEVE extrair entidades, relações e taxonomia do texto novo com o mesmo motor da geração, usando o modelo e a temperatura escolhidos, DEVE acrescentá-las à ontologia carregada, rodar o raciocinador e gravar o resultado no mesmo arquivo, devolvendo o caminho, o estado do raciocinador e o número de relações novas.

Fonte: `omaker/pipeline/engine.py` ; Verificado por: `tests/test_hybrid_engine.py::test_atualizar_forwards_model_and_temperature`, `tests/test_owl_builder.py::test_atualizar_returns_ontology_result`

#### Cenário: modelo escolhido

- **DADO** o modelo `x:1b` e a temperatura 0,3 nas Configurações
- **QUANDO** o usuário atualiza uma ontologia
- **ENTÃO** a extração usa `x:1b` e 0,3

#### Cenário: resultado da atualização

- **DADO** uma ontologia gerada antes pelo OMAKER
- **QUANDO** ela é atualizada
- **ENTÃO** o resultado aponta o mesmo arquivo e traz o estado do raciocinador e um número inteiro de relações novas

### Requisito: Ontologia externa reconhecida (ATU-02)

O sistema DEVE tratar como externa a ontologia que tem classes e não tem a classe `BiomedicalEntity` no próprio namespace; uma ontologia gerada pelo OMAKER NÃO DEVE ser tratada como externa.

Fonte: `omaker/ontology/alignment.py` ; Verificado por: `tests/test_alignment.py::test_new_ontology_is_not_external`, `tests/test_alignment.py::test_unrelated_external_ontology_gets_omaker_bases`

#### Cenário: ontologia nova do OMAKER

- **DADO** uma ontologia criada pelo OMAKER
- **QUANDO** ela é verificada
- **ENTÃO** ela não é externa e a atualização não registra nenhum "[ALIGN]"

### Requisito: Índice de termos da ontologia externa (ATU-03)

O sistema DEVE indexar as classes da ontologia externa pelo rótulo, depois pelos sinônimos exatos (`oboInOwl:hasExactSynonym`) e por fim pelo nome, comparando os termos em minúsculas e tratando espaço e `_` como iguais, e NÃO DEVE indexar classes obsoletas (`owl:deprecated`) nem as criadas pelo OMAKER.

Fonte: `omaker/ontology/alignment.py` ; Verificado por: `tests/test_alignment.py::test_label_index_has_labels_and_synonyms`, `tests/test_alignment.py::test_obsolete_classes_do_not_win_synonym_collisions`

#### Cenário: sinônimo compartilhado com classe obsoleta

- **DADO** a SYMP, em que "mammitis" é sinônimo de uma classe em uso e de uma obsoleta
- **QUANDO** o índice é montado
- **ENTÃO** "mammitis" aponta para a classe em uso

### Requisito: Classes-base reaproveitadas (ATU-04)

Numa ontologia externa, o sistema DEVE reaproveitar a classe que tem o mesmo termo de uma classe-base do OMAKER (por exemplo, o "symptom" da SYMP para `Symptom`) e DEVE criar as que faltam no namespace `http://www.mestrado.edu/ontologias/omaker#`, sem mexer nas classes alheias.

Fonte: `omaker/ontology/builder.py`, `omaker/ontology/alignment.py` ; Verificado por: `tests/test_alignment.py::test_symp_update_reuses_symptom_and_has_no_parallel_classes`, `tests/test_alignment.py::test_unrelated_external_ontology_gets_omaker_bases`

#### Cenário: Symptom Ontology

- **DADO** uma cópia da `symp.owl`
- **QUANDO** ela é atualizada com "fever" (`SYMPTOM`) e "aspirin" (`DRUG`)
- **ENTÃO** a instância "fever" fica sob a classe "symptom" da SYMP, sem uma classe `Symptom` paralela
- **E** a classe de "aspirin" é criada no namespace do OMAKER

#### Cenário: ontologia sem relação com biomedicina

- **DADO** uma ontologia de carros com a classe "Carro"
- **QUANDO** ela é atualizada com "aspirin"
- **ENTÃO** `BiomedicalEntity`, `Drug`, `Disease` e `Symptom` são criadas no namespace do OMAKER
- **E** "Carro" continua subclasse direta de `Thing`

### Requisito: Instância tipada pela classe existente (ATU-05)

Numa ontologia externa, o sistema DEVE tipar cada nova instância pela classe já existente cujo rótulo, sinônimo exato ou nome coincide com a entidade, desde que essa classe esteja no ramo do tipo da entidade, e DEVE registrar o alinhamento no log com "[ALIGN]".

Fonte: `omaker/ontology/alignment.py`, `omaker/ontology/builder.py` ; Verificado por: `tests/test_alignment.py::test_instance_typed_by_label`, `tests/test_alignment.py::test_instance_typed_by_exact_synonym`, `tests/test_alignment.py::test_match_outside_entity_branch_is_ignored`

#### Cenário: pelo sinônimo exato

- **DADO** a entidade "back pain" (`SYMPTOM`), sinônimo exato de "backache" na SYMP
- **QUANDO** a ontologia é atualizada
- **ENTÃO** a instância "back pain" é do tipo "backache"

#### Cenário: fora do ramo

- **DADO** a entidade "nausea" marcada como `DRUG`
- **QUANDO** a ontologia é atualizada
- **ENTÃO** a instância fica em `Drug` do namespace do OMAKER, e não na classe "nausea" da SYMP

### Requisito: Subclasse proposta reaproveitada (ATU-06)

Numa ontologia externa, o sistema DEVE reaproveitar a classe existente que corresponde a uma subclasse proposta pelo LLM, convertendo o nome CamelCase em palavras ("BackPain" vira "Back Pain") e exigindo o mesmo ramo, em vez de criar uma cópia no namespace do OMAKER.

Fonte: `omaker/ontology/builder.py`, `omaker/ontology/alignment.py` ; Verificado por: `tests/test_alignment.py::test_taxonomy_subclass_reuses_existing_class`

#### Cenário: "Pain" sob "Symptom"

- **DADO** a taxonomia propõe "Pain" sob `Symptom` e "BackPain" sob "Pain"
- **QUANDO** a SYMP é atualizada
- **ENTÃO** não existem `omaker#Pain` nem `omaker#BackPain`; valem as classes "pain" e "backache" da SYMP

### Requisito: Disjunções só entre classes do OMAKER (ATU-07)

O sistema NÃO DEVE incluir classes reaproveitadas de uma ontologia externa em axiomas de disjunção e NÃO DEVE repetir um axioma de disjunção que já existe na ontologia.

Fonte: `omaker/ontology/builder.py` ; Verificado por: `tests/test_alignment.py::test_reused_class_not_in_alldisjoint`, `tests/test_alignment.py::test_alldisjoint_not_repeated_on_second_update`

#### Cenário: segunda atualização

- **DADO** uma ontologia já atualizada com a disjunção entre "Analgesic" e "Antibiotic"
- **QUANDO** ela é atualizada de novo com a mesma taxonomia
- **ENTÃO** o número de axiomas de disjunção não muda

### Requisito: Atualização idempotente (ATU-08)

O sistema DEVE reaproveitar classes e indivíduos que já existem, de modo que atualizar duas vezes com o mesmo conteúdo, com ou sem gravar e recarregar o arquivo entre as duas vezes, não crie classes, indivíduos nem disjunções novos.

Fonte: `omaker/ontology/builder.py` ; Verificado por: `tests/test_alignment.py::test_second_update_is_idempotent`, `tests/test_alignment.py::test_idempotent_after_save_and_reload`

#### Cenário: gravar, recarregar e atualizar de novo

- **DADO** a SYMP atualizada com "aspirin" e "fever", gravada e recarregada
- **QUANDO** ela é atualizada outra vez com as mesmas entidades
- **ENTÃO** as contagens de classes, indivíduos e disjunções são as mesmas de antes

### Requisito: Ontologia do OMAKER sem alinhamento (ATU-09)

Numa ontologia gerada pelo OMAKER, o sistema DEVE usar as classes do próprio namespace da ontologia e NÃO DEVE fazer alinhamento.

Fonte: `omaker/ontology/builder.py` ; Verificado por: `tests/test_alignment.py::test_new_ontology_unchanged`

#### Cenário: atualizar uma ontologia do OMAKER

- **DADO** uma ontologia nova do OMAKER
- **QUANDO** ela recebe "nausea" (`SYMPTOM`) e "aspirin" (`DRUG`)
- **ENTÃO** "nausea" fica na classe `Symptom` e o log não tem "[ALIGN]"

### Requisito: Cópia de segurança antes de sobrescrever (ATU-10)

Antes de gravar a ontologia atualizada por cima do arquivo escolhido, o sistema DEVE copiar o original para `<nome>.backup-AAAAMMDD-HHMMSS.owl`, na mesma pasta, e registrar no log onde a cópia ficou.

Fonte: `omaker/ontology/builder.py` (`backup_copy`), `omaker/pipeline/engine.py` ; Verificado por: `tests/test_hybrid_engine.py::test_updater_keeps_a_backup_of_the_original_owl`

#### Cenário: atualizar uma ontologia existente

- **DADO** um arquivo `a.owl` escolhido no Atualizador
- **QUANDO** a atualização termina
- **ENTÃO** `a.owl` tem a ontologia atualizada
- **E** `a.backup-<data>-<hora>.owl` guarda o conteúdo original, e o log mostra o nome da cópia
