# Sinônimos

## Propósito

Agrupar termos que significam a mesma coisa (por exemplo "fever" e "pyrexia") com um modelo de embeddings Sentence-BERT e, depois da confirmação do usuário, gravar os grupos como `owl:equivalentClass` numa cópia da ontologia. O arquivo original nunca é alterado. A página da interface que usa esta capacidade está descrita em [Interface](../interface/spec.md).

## Requisitos

### Requisito: Agrupamento por similaridade (SIN-01)

O sistema DEVE calcular os embeddings dos termos com `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, agrupá-los por agrupamento aglomerativo com ligação média sobre a distância de cosseno (1 menos a similaridade), com limiar de distância 0,25, e DEVE devolver só os grupos com dois ou mais termos.

Fonte: `omaker/nlp/synonyms.py`, `omaker/ui/workers.py` ; Verificado por: sem teste automatizado (o modelo real é exercitado à mão por `scripts/synonyms_gui.py` e pelo bloco principal de `omaker/nlp/synonyms.py`)

#### Cenário: termos sinônimos e um termo isolado

- **DADO** os termos "fever", "pyrexia" e "cough"
- **QUANDO** os sinônimos são detectados
- **ENTÃO** cada grupo devolvido tem pelo menos dois termos
- **E** um termo sem par próximo não aparece em nenhum grupo

### Requisito: Poucos termos (SIN-02)

O sistema DEVE devolver nenhum grupo quando receber menos de dois termos e DEVE pedir, na interface, que o usuário informe os termos quando a lista estiver vazia.

Fonte: `omaker/nlp/synonyms.py`, `omaker/ui/pages/synonyms.py` ; Verificado por: sem teste automatizado

#### Cenário: campo vazio

- **DADO** o campo de conceitos vazio
- **QUANDO** o usuário clica em "Detectar Sinônimos"
- **ENTÃO** um aviso pede pelo menos dois conceitos e nada é processado

### Requisito: Gravação só com confirmação (SIN-03)

O sistema DEVE mostrar os grupos detectados e o arquivo de destino e DEVE gravar as equivalências só se o usuário responder "Sim"; com "Não", o log registra que as equivalências não foram gravadas.

Fonte: `omaker/ui/pages/synonyms.py` ; Verificado por: `tests/test_ui_synonyms.py::test_synonyms_not_written_without_confirmation`, `tests/test_ui_synonyms.py::test_synonyms_written_after_confirmation`

#### Cenário: usuário recusa

- **DADO** grupos de sinônimos detectados
- **QUANDO** o usuário responde "Não" à pergunta "Gravar equivalências?"
- **ENTÃO** nenhum arquivo é gravado

#### Cenário: usuário confirma

- **DADO** grupos de sinônimos detectados
- **QUANDO** o usuário responde "Sim"
- **ENTÃO** a cópia com as equivalências é gravada e o número de equivalências é informado

### Requisito: Cópia na pasta de destino (SIN-04)

O sistema DEVE gravar as equivalências em `<nome da ontologia>_sinonimos.owl` na pasta de destino das Configurações, NÃO DEVE alterar o arquivo de origem e DEVE avisar, na pergunta de confirmação, quando a cópia já existir e for ser substituída.

Fonte: `omaker/ui/pages/synonyms.py`, `omaker/ontology/builder.py` ; Verificado por: `tests/test_equivalences.py::test_equivalence_written_to_copy`, `tests/test_ui_synonyms.py::test_existing_copy_is_announced_in_question`

#### Cenário: cópia já existe

- **DADO** o arquivo `symp_sinonimos.owl` já existe na pasta de destino
- **QUANDO** a pergunta de confirmação aparece
- **ENTÃO** ela diz que o arquivo será substituído

#### Cenário: origem intacta

- **DADO** uma ontologia com as classes "Doenca" e "Enfermidade"
- **QUANDO** o grupo ["doença", "enfermidade"] é gravado
- **ENTÃO** a cópia tem a equivalência entre as duas classes
- **E** os bytes do arquivo de origem não mudam

### Requisito: Termo casado com classe (SIN-05)

O sistema DEVE ligar cada termo à classe cujo `rdfs:label` ou nome seja igual a ele, sem diferenciar maiúsculas e tratando espaço e `_` como iguais.

Fonte: `omaker/ontology/builder.py`, `omaker/ontology/alignment.py` ; Verificado por: `tests/test_equivalences.py::test_match_ignores_case_and_underscores`

#### Cenário: maiúsculas diferentes

- **DADO** o grupo ["DOENÇA", "Enfermidade"]
- **QUANDO** as equivalências são gravadas
- **ENTÃO** a equivalência entre "Doenca" e "Enfermidade" é gravada

### Requisito: Grupo sem duas classes (SIN-06)

O sistema DEVE ignorar o grupo em que menos de duas classes diferentes foram encontradas, registrando "[SKIP]" no log, e DEVE informar ao usuário os termos sem classe correspondente.

Fonte: `omaker/ontology/builder.py`, `omaker/ui/pages/synonyms.py` ; Verificado por: `tests/test_equivalences.py::test_group_with_one_match_is_skipped`

#### Cenário: só um termo existe na ontologia

- **DADO** o grupo ["carro", "automóvel"] e uma ontologia que só tem "carro"
- **QUANDO** as equivalências são gravadas
- **ENTÃO** nenhuma equivalência é gravada
- **E** "automóvel" aparece entre os termos não encontrados

### Requisito: Nada a gravar (SIN-07)

Quando nenhuma equivalência nova for gravada, o sistema NÃO DEVE criar o arquivo de destino e NÃO DEVE mostrar mensagem de sucesso; a mensagem DEVE dizer que nenhum arquivo foi criado.

Fonte: `omaker/ontology/builder.py`, `omaker/ui/pages/synonyms.py` ; Verificado por: `tests/test_equivalences.py::test_no_file_when_nothing_added`, `tests/test_ui_synonyms.py::test_no_success_message_when_nothing_added`

#### Cenário: grupo sem classes

- **DADO** um grupo em que nenhum par de termos tem classe na ontologia
- **QUANDO** o usuário confirma a gravação
- **ENTÃO** o arquivo de destino não existe
- **E** a mensagem diz "Nenhuma equivalência gravada"

### Requisito: Ontologia padrão (SIN-08)

O sistema DEVE começar com a `symp.owl` empacotada em `omaker/resources/` como ontologia selecionada, encontrada pelo caminho do pacote e não pela pasta corrente, e PODE trocar por outro `.owl` escolhido pelo usuário.

Fonte: `omaker/ui/pages/synonyms.py`, `omaker/paths.py` ; Verificado por: `tests/test_ui_synonyms.py::test_synonyms_default_independent_of_cwd`

#### Cenário: programa iniciado de outra pasta

- **DADO** o programa iniciado com uma pasta corrente qualquer
- **QUANDO** a página de sinônimos abre
- **ENTÃO** a ontologia selecionada é a `symp.owl` do pacote

### Requisito: Detecção em segundo plano (SIN-09)

O sistema DEVE detectar os sinônimos numa thread própria, com o botão desabilitado durante a execução, e DEVE reabilitar o botão e mostrar o erro quando a detecção falhar.

Fonte: `omaker/ui/workers.py`, `omaker/ui/pages/synonyms.py` ; Verificado por: `tests/test_ui_synonyms.py::test_button_reenabled_after_synonym_error`, `tests/test_ui_generation.py::test_close_during_synonyms_waits_for_worker`

#### Cenário: falha ao carregar o modelo

- **DADO** o modelo de embeddings não carrega
- **QUANDO** o usuário clica em "Detectar Sinônimos"
- **ENTÃO** uma caixa de erro mostra "Synonym clustering failed" e o botão volta a ficar habilitado
