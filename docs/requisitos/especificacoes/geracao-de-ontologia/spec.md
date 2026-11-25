# Geração de ontologia

## Propósito

Transformar as entidades e as triplas extraídas numa ontologia OWL nova, com uma taxonomia proposta pelo LLM e validada pelo próprio OMAKER, IRI absoluto e consistência conferida pelo raciocinador HermiT. O LLM organiza as entidades, mas não cria entidades nem relações. O resultado pode ser aberto no Protégé.

## Requisitos

### Requisito: Pedido da taxonomia (ONT-01)

O sistema DEVE pedir a taxonomia ao LLM enviando a lista de entidades únicas e no máximo os primeiros 6.000 caracteres do texto e, quando o texto for maior, DEVE registrar um aviso "[WARNING]" com o tamanho do texto e o limite; entidades e relações continuam vindo do texto inteiro.

Fonte: `omaker/llm/taxonomy.py` ; Verificado por: `tests/test_hybrid_engine.py::test_taxonomy_text_truncation_is_logged`

#### Cenário: texto curto

- **DADO** um texto com menos de 6.000 caracteres
- **QUANDO** a taxonomia é pedida
- **ENTÃO** o texto inteiro vai no pedido e nenhum aviso é registrado

#### Cenário: texto longo

- **DADO** um texto com mais de 6.000 caracteres
- **QUANDO** a taxonomia é pedida
- **ENTÃO** só os primeiros 6.000 caracteres vão no pedido
- **E** o log tem exatamente um aviso "[WARNING]" com o tamanho do texto e o número 6000

### Requisito: Classes propostas aceitas (ONT-02)

O sistema DEVE converter o nome de cada classe proposta num identificador OWL em CamelCase, DEVE ignorar propostas que redefinem a raiz `BiomedicalEntity`, uma classe-base (`Drug`, `Symptom`, `Disease`, `Gene`) ou uma classe já aceita, e DEVE descartar a classe cujo nome repete o de uma entidade, mandando as instâncias dela para o pai proposto.

Fonte: `omaker/llm/taxonomy.py` ; Verificado por: `tests/test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output`

#### Cenário: classe com o nome de uma entidade

- **DADO** o LLM propõe a classe "Aspirin" sob "Analgesic" e coloca a entidade "Aspirin" nela
- **QUANDO** a taxonomia é validada
- **ENTÃO** a classe "Aspirin" não existe
- **E** a instância "Aspirin" fica em "Analgesic"

#### Cenário: redefinição de classe-base

- **DADO** o LLM propõe a classe "Drug" sob "Thing"
- **QUANDO** a taxonomia é validada
- **ENTÃO** a proposta é ignorada e "Drug" continua sendo a classe-base

### Requisito: Pais e ciclos (ONT-03)

O sistema DEVE pendurar na raiz `BiomedicalEntity` a classe cujo pai não seja uma classe-base, a raiz ou outra classe aceita, e DEVE quebrar todo ciclo de herança ligando uma das classes do ciclo à raiz.

Fonte: `omaker/llm/taxonomy.py` ; Verificado por: `tests/test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output`

#### Cenário: pai desconhecido

- **DADO** o LLM propõe "Weird" sob "DoesNotExist"
- **QUANDO** a taxonomia é validada
- **ENTÃO** o pai de "Weird" é `BiomedicalEntity`

#### Cenário: ciclo

- **DADO** o LLM propõe "LoopA" sob "LoopB" e "LoopB" sob "LoopA"
- **QUANDO** a taxonomia é validada
- **ENTÃO** uma das duas classes passa a ter `BiomedicalEntity` como pai

### Requisito: Tipagem das instâncias (ONT-04)

O sistema DEVE colocar cada entidade única na classe proposta só se essa classe existir e descender da classe-base do tipo da entidade; caso contrário, a entidade fica na sua classe-base. Nomes de instância que não estão entre as entidades detectadas DEVEM ser ignorados.

Fonte: `omaker/llm/taxonomy.py` ; Verificado por: `tests/test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output`

#### Cenário: ramo errado

- **DADO** o LLM coloca o fármaco "Chemotherapy" na classe "Cancer", subclasse de `Disease`
- **QUANDO** a taxonomia é validada
- **ENTÃO** "Chemotherapy" fica em `Drug`

#### Cenário: instância inventada

- **DADO** o LLM cita a instância "ghost entity", que não foi detectada
- **QUANDO** a taxonomia é validada
- **ENTÃO** "ghost entity" não entra na taxonomia

### Requisito: Disjunções válidas (ONT-05)

O sistema DEVE aceitar um grupo de disjunção proposto só com as classes aceitas do grupo, só se restarem pelo menos duas e só se nenhuma delas for ancestral de outra do grupo.

Fonte: `omaker/llm/taxonomy.py` ; Verificado por: `tests/test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output`

#### Cenário: grupos válidos e inválidos

- **DADO** o LLM propõe as disjunções ["Analgesic", "Drug"] e ["Analgesic", "Cancer"]
- **QUANDO** a taxonomia é validada
- **ENTÃO** só ["Analgesic", "Cancer"] é aceita (`Drug` é classe-base, não proposta)

### Requisito: Estrutura básica da ontologia (ONT-06)

O sistema DEVE criar a classe raiz `BiomedicalEntity`, as classes-base `Drug`, `Symptom`, `Disease` e `Gene` como subclasses dela, as propriedades de objeto `treats`, `causes` e `prevents` (com domínio `Drug` em `treats` e `prevents`) e um axioma que declara as classes-base disjuntas entre si.

Fonte: `omaker/ontology/builder.py`, `omaker/domain/labels.py` ; Verificado por: `tests/test_alignment.py::test_unrelated_external_ontology_gets_omaker_bases` (criação da raiz e das classes-base); as propriedades e a disjunção das classes-base não têm teste automatizado direto, `tests/test_owl_builder.py::test_new_ontology_has_the_root_and_the_four_base_classes`, `tests/test_owl_builder.py::test_new_ontology_has_the_three_object_properties_with_drug_domain_on_treats_and_prevents`, `tests/test_owl_builder.py::test_new_ontology_declares_the_base_classes_disjoint`

#### Cenário: ontologia nova

- **DADO** uma taxonomia validada e nenhuma tripla
- **QUANDO** a ontologia é montada
- **ENTÃO** ela contém `BiomedicalEntity`, as quatro classes-base, as três propriedades e a disjunção das classes-base

### Requisito: Indivíduos (ONT-07)

O sistema DEVE criar um indivíduo por entidade única, com identificador seguro para OWL e `rdfs:label` igual ao texto original, e DEVE acrescentar o sufixo `_ind` ao identificador que coincidir com o nome de uma classe.

Fonte: `omaker/ontology/builder.py`, `omaker/domain/text.py` ; Verificado por: `tests/test_alignment.py::test_new_ontology_unchanged` (indivíduo localizado pelo rótulo e tipado pela classe-base); o sufixo `_ind` não tem teste automatizado, `tests/test_owl_builder.py::test_individual_gets_a_safe_identifier_and_the_original_text_as_label`, `tests/test_owl_builder.py::test_individual_named_like_a_class_gets_the_ind_suffix`

#### Cenário: entidade com espaço

- **DADO** a entidade "back pain"
- **QUANDO** o indivíduo é criado
- **ENTÃO** o identificador é "back_pain" e o rótulo é "back pain"

### Requisito: Triplas como asserções (ONT-08)

O sistema DEVE gravar cada tripla como asserção da propriedade entre os dois indivíduos, sem repetir asserções que já existem, e DEVE registrar cada asserção nova no log com "[AXIOM]" e a confiança em porcentagem, ou "LLM" quando a relação veio sem confiança.

Fonte: `omaker/ontology/builder.py` ; Verificado por: `tests/test_owl_builder.py::test_construir_reports_reasoner_unavailable` (três relações novas contadas)

#### Cenário: três triplas

- **DADO** as triplas (Aspirin, prevents, stroke), (Chemotherapy, treats, tumor) e (Chemotherapy, causes, nausea), vindas do LLM
- **QUANDO** a ontologia é montada
- **ENTÃO** o resultado informa 3 relações novas

### Requisito: Base do IRI (ONT-09)

O sistema DEVE usar a URI base informada só se ela for `http` ou `https`, com host e sem espaço no caminho; uma base terminada em `#` DEVE passar a terminar em `/`, e uma base vazia ou inválida DEVE ser trocada por `http://www.mestrado.edu/ontologias/`, com aviso "[IRI]" no log.

Fonte: `omaker/ontology/iri.py`, `omaker/pipeline/engine.py` ; Verificado por: `tests/test_iri.py::test_empty_base_falls_back_to_default`, `tests/test_iri.py::test_relative_base_falls_back`, `tests/test_iri.py::test_hash_base_becomes_slash`, `tests/test_iri.py::test_slash_base_kept`, `tests/test_iri.py::test_base_with_whitespace_falls_back`

#### Cenário: base vazia

- **DADO** a URI base vazia
- **QUANDO** a ontologia é gerada
- **ENTÃO** o IRI começa com `http://www.mestrado.edu/ontologias/`
- **E** o log tem uma linha "[IRI]"

#### Cenário: base com cerquilha

- **DADO** a URI base `http://a.org/onto#`
- **QUANDO** o IRI é montado
- **ENTÃO** a base usada é `http://a.org/onto/`

### Requisito: Nome no IRI (ONT-10)

O sistema DEVE formar o IRI como base + nome + `.owl`, trocando espaços do nome por `_`, removendo os caracteres reservados `# ? / % " < > { } | ^` e o acento grave, mantendo letras acentuadas, e usando "ontologia" quando não sobrar nada; todos os `rdf:about` gravados DEVEM ser absolutos.

Fonte: `omaker/ontology/iri.py` ; Verificado por: `tests/test_iri.py::test_reserved_chars_removed_accents_kept`, `tests/test_iri.py::test_name_only_reserved_chars`, `tests/test_iri.py::test_construir_writes_absolute_iri`

#### Cenário: nome com espaços

- **DADO** o nome "teste peste negra" e a URI base vazia
- **QUANDO** a ontologia é gravada
- **ENTÃO** o arquivo se chama "teste peste negra.owl"
- **E** o `xml:base` é `http://www.mestrado.edu/ontologias/teste_peste_negra.owl`, sem espaços nos IRIs

### Requisito: Gravação do arquivo (ONT-11)

O sistema DEVE gravar a ontologia em RDF/XML no arquivo `<nome>.owl` dentro da pasta de destino, criando a pasta se ela não existir, e DEVE devolver o caminho, o estado do raciocinador e o número de relações novas.

Fonte: `omaker/pipeline/engine.py`, `omaker/ontology/builder.py` ; Verificado por: `tests/test_owl_builder.py::test_construir_reports_reasoner_unavailable`

#### Cenário: pasta nova

- **DADO** uma pasta de destino que ainda não existe
- **QUANDO** a ontologia é gerada
- **ENTÃO** a pasta é criada e o arquivo `.owl` existe nela

### Requisito: Raciocinador sem Java (ONT-12)

O sistema DEVE gravar a ontologia mesmo sem Java e DEVE devolver o estado `UNAVAILABLE`, com uma linha no log ("Java não encontrado") que diz como resolver; qualquer outra falha do HermiT também DEVE resultar em `UNAVAILABLE`, nunca em "consistente".

Fonte: `omaker/ontology/builder.py` ; Verificado por: `tests/test_owl_builder.py::test_run_reasoner_unavailable_without_java`, `tests/test_owl_builder.py::test_run_reasoner_without_java_explains`, `tests/test_owl_builder.py::test_construir_reports_reasoner_unavailable`

#### Cenário: máquina sem Java

- **DADO** nenhum Java encontrado
- **QUANDO** a ontologia é gerada
- **ENTÃO** o arquivo `.owl` é gravado e o estado é `UNAVAILABLE`
- **E** o log tem "Java não encontrado"

### Requisito: Consistência conferida (ONT-13)

Com Java disponível, o sistema DEVE rodar o HermiT com inferência de valores de propriedade e DEVE devolver `CONSISTENT` quando ele terminar sem erro, ou `INCONSISTENT` quando ele apontar inconsistência, caso em que o arquivo é gravado mesmo assim e o log diz que precisa de revisão.

Fonte: `omaker/ontology/builder.py` ; Verificado por: `tests/test_owl_builder.py::test_run_reasoner_consistent`, `tests/test_owl_builder.py::test_run_reasoner_inconsistent`

#### Cenário: ontologia inconsistente

- **DADO** o HermiT detecta uma inconsistência
- **QUANDO** a ontologia é gerada
- **ENTÃO** o estado é `INCONSISTENT` e o arquivo é gravado

### Requisito: Localização do Java (ONT-14)

O sistema DEVE procurar o Java nesta ordem: `OMAKER_JAVA` (se o arquivo existir), `JAVA_HOME\bin\java.exe`, o `java` do `PATH`, a versão mais nova em `C:\Program Files\Java`, `Eclipse Adoptium` e `Microsoft`, e por fim o JRE que vem ao lado do `Protege.exe` configurado.

Fonte: `omaker/ontology/java.py` ; Verificado por: `tests/test_java_locator.py::test_omaker_java_wins`, `tests/test_java_locator.py::test_java_home_used`, `tests/test_java_locator.py::test_path_used_before_program_files`, `tests/test_java_locator.py::test_newest_jdk_in_roots`, `tests/test_java_locator.py::test_protege_bundled_jre`, `tests/test_java_locator.py::test_none_when_nothing`, `tests/test_java_locator.py::test_missing_omaker_java_falls_through`, `tests/test_java_locator.py::test_java_home_without_java_falls_through`

#### Cenário: só o Protégé instalado

- **DADO** nenhum Java no ambiente, no `PATH` ou em Program Files, e o caminho do `Protege.exe` nas Configurações
- **QUANDO** o Java é procurado
- **ENTÃO** o resultado é o `jre\bin\java.exe` da pasta do Protégé

#### Cenário: OMAKER_JAVA aponta para um arquivo que não existe

- **DADO** `OMAKER_JAVA` com um caminho inexistente e `JAVA_HOME` válido
- **QUANDO** o Java é procurado
- **ENTÃO** o resultado é o Java de `JAVA_HOME`

### Requisito: Caminho do Protégé repassado (ONT-15)

O sistema DEVE repassar o caminho do `Protege.exe` das Configurações à busca do Java, tanto ao gerar quanto ao atualizar, e, se o Java encontrado não existir mais na hora de rodar, DEVE tentar o `java` do `PATH`.

Fonte: `omaker/pipeline/engine.py`, `omaker/ontology/builder.py` ; Verificado por: `tests/test_owl_builder.py::test_gerar_ontologia_passes_protege_exe_to_find_java`, `tests/test_owl_builder.py::test_atualizar_ontologia_passes_protege_exe_to_find_java`

#### Cenário: gerar com o Protégé configurado

- **DADO** o caminho `X\Protege.exe` nas Configurações
- **QUANDO** a ontologia é gerada
- **ENTÃO** a busca do Java recebe `X\Protege.exe`

### Requisito: Abrir no Protégé (ONT-16)

O sistema DEVE abrir a ontologia iniciando o `Protege.exe` com uma lista de argumentos (o caminho absoluto do `.owl` como um argumento só, mesmo com espaços) e com a pasta do Protégé como pasta de trabalho, e DEVE falhar com `FileNotFoundError` se o executável ou o arquivo `.owl` não existir.

Fonte: `omaker/ontology/protege.py` ; Verificado por: `tests/test_protege.py::test_opens_with_argument_list`, `tests/test_protege.py::test_path_with_spaces_passed_as_one_argument`, `tests/test_protege.py::test_missing_exe_raises`, `tests/test_protege.py::test_missing_owl_raises`

#### Cenário: caminho com espaços

- **DADO** a ontologia em "C:\Minhas Ontologias\teste.owl"
- **QUANDO** o Protégé é aberto
- **ENTÃO** o caminho chega ao Protégé como um único argumento

#### Cenário: Protégé não configurado

- **DADO** o caminho do Protégé vazio
- **QUANDO** o usuário pede para abrir a ontologia
- **ENTÃO** a abertura falha com uma mensagem que manda informar o `Protege.exe` nas Configurações
