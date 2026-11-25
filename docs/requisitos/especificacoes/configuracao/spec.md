# Configuração

## Propósito

Concentrar num só lugar o que muda o comportamento do OMAKER sem mudar o código: variáveis de ambiente para o motor, o treino e a avaliação (`omaker/config.py`), e preferências da interface gravadas pelo próprio programa. As variáveis são lidas na hora do uso, e um valor errado só falha onde é usado.

## Requisitos

### Requisito: Leitura na hora do uso (CFG-01)

O sistema DEVE ler as variáveis de ambiente no momento em que cada valor é usado, e não na importação dos módulos, de modo que uma mudança feita depois de importar o programa seja vista.

Fonte: `omaker/config.py` ; Verificado por: `tests/test_config.py::test_env_change_after_import_is_seen`

#### Cenário: endereço mudado depois da importação

- **DADO** o programa já importado
- **QUANDO** `OLLAMA_HOST` passa a ser `http://outra-maquina:11434` e um cliente do Ollama é criado
- **ENTÃO** o cliente usa `http://outra-maquina:11434`

### Requisito: Endereço do Ollama (CFG-02)

O sistema DEVE usar `OLLAMA_HOST` como endereço do Ollama, com o padrão `http://localhost:11434` quando a variável estiver vazia ou ausente, e DEVE acrescentar `http://` a um endereço sem esquema.

Fonte: `omaker/config.py` ; Verificado por: `tests/test_config.py::test_defaults`, `tests/test_config.py::test_host_without_scheme_gets_http`

#### Cenário: endereço sem esquema

- **DADO** `OLLAMA_HOST=127.0.0.1:11434`
- **QUANDO** o endereço é lido
- **ENTÃO** o valor usado é `http://127.0.0.1:11434`

### Requisito: Fonte das entidades (CFG-03)

O sistema DEVE aceitar em `OMAKER_ENTITIES` os valores `ner`, `llm` e `both`, sem diferenciar maiúsculas e ignorando espaços, com `both` como padrão para valor vazio ou ausente; um valor inválido DEVE falhar só quando as entidades forem extraídas, antes de qualquer chamada ao LLM, e NÃO DEVE afetar o treino, o caminho do checkpoint nem o cliente do Ollama.

Fonte: `omaker/config.py`, `omaker/pipeline/engine.py` ; Verificado por: `tests/test_config.py::test_entity_source_is_normalized`, `tests/test_config.py::test_empty_entity_source_defaults_to_both`, `tests/test_config.py::test_invalid_entity_source_raises`, `tests/test_config.py::test_bad_entity_source_does_not_break_checkpoint_or_client`, `tests/test_config.py::test_bad_entity_source_reported_when_generating`

#### Cenário: valor normalizado

- **DADO** `OMAKER_ENTITIES=" NER "`
- **QUANDO** a fonte é lida
- **ENTÃO** o valor usado é `ner`

#### Cenário: erro de digitação

- **DADO** `OMAKER_ENTITIES=nerr`
- **QUANDO** o usuário gera uma ontologia
- **ENTÃO** a geração falha com uma mensagem que cita `OMAKER_ENTITIES` e os valores aceitos
- **E** o LLM não é chamado

### Requisito: Caminho do checkpoint (CFG-04)

O sistema DEVE usar `OMAKER_CHECKPOINT` como caminho do checkpoint do PURE quando a variável estiver definida; sem ela, o caminho DEVE ser `omaker_pure.pt` na raiz do repositório, ou, no executável, `%LOCALAPPDATA%\OMAKER\models\omaker_pure.pt` ([DIS-07](../distribuicao/spec.md)).

Fonte: `omaker/config.py`, `omaker/paths.py` ; Verificado por: `tests/test_config.py::test_checkpoint_from_env`, `tests/test_paths.py::test_checkpoint_env_override`, `tests/test_paths.py::test_checkpoint_path_independent_of_cwd`

#### Cenário: checkpoint em outro lugar

- **DADO** `OMAKER_CHECKPOINT=D:\modelos\x.pt`
- **QUANDO** o pipeline procura o checkpoint
- **ENTÃO** o caminho usado é `D:\modelos\x.pt`

### Requisito: Semente do LLM (CFG-05)

O sistema DEVE ler `OMAKER_LLM_SEED` como número inteiro e, quando ela estiver vazia ou ausente, NÃO DEVE enviar semente ao Ollama ([LLM-08](../integracao-com-llm/spec.md)).

Fonte: `omaker/config.py` ; Verificado por: `tests/test_e2e.py::test_llm_seed_sent_to_ollama`

#### Cenário: semente definida

- **DADO** `OMAKER_LLM_SEED=7`
- **QUANDO** um pedido vai ao Ollama
- **ENTÃO** ele leva a semente 7

### Requisito: Download automático desligável (CFG-06)

O sistema DEVE desligar o download automático do checkpoint quando `OMAKER_NO_DOWNLOAD` tiver qualquer valor diferente de vazio e de `0` ([MOD-24](../modelo-de-relacoes/spec.md)); a suíte de testes DEVE definir essa variável para que nenhum teste baixe o modelo.

Fonte: `omaker/relations/download.py`, `tests/conftest.py` ; Verificado por: `tests/test_download.py::test_ensure_skips_when_disabled_or_present`

#### Cenário: máquina sem internet

- **DADO** `OMAKER_NO_DOWNLOAD=1`
- **QUANDO** o checkpoint falta
- **ENTÃO** nenhum download é tentado e as relações vêm do LLM

### Requisito: Java do HermiT (CFG-07)

O sistema DEVE usar o `java.exe` indicado em `OMAKER_JAVA` antes de qualquer outro, desde que o arquivo exista; se não existir, a busca DEVE continuar pelas outras opções ([ONT-14](../geracao-de-ontologia/spec.md)).

Fonte: `omaker/ontology/java.py` ; Verificado por: `tests/test_java_locator.py::test_omaker_java_wins`, `tests/test_java_locator.py::test_missing_omaker_java_falls_through`

#### Cenário: Java escolhido pelo usuário

- **DADO** `OMAKER_JAVA` com um `java.exe` existente e outro Java no `PATH`
- **QUANDO** o Java é procurado
- **ENTÃO** o resultado é o de `OMAKER_JAVA`

### Requisito: Preferências gravadas (CFG-08)

O sistema DEVE gravar nas configurações do usuário (`QSettings` "MeuMestrado" / "OntoGenApp", no registro do Windows) o modelo do LLM, a lista de modelos, a temperatura, a pasta de destino, o caminho do Protégé (sem aspas em volta), o nome do autor e a URI base, e DEVE relê-los ao abrir o programa.

Fonte: `omaker/ui/pages/settings.py`, `omaker/ui/pages/metadata.py` ; Verificado por: `tests/test_ui_pages.py::test_settings_readers`

#### Cenário: temperatura

- **DADO** o controle de temperatura na posição 25 (de 0 a 100)
- **QUANDO** as páginas de trabalho leem a temperatura
- **ENTÃO** o valor é 0,25

#### Cenário: URI base vazia

- **DADO** a URI base gravada vazia
- **QUANDO** a URI base é lida
- **ENTÃO** o valor é `http://www.mestrado.edu/ontologias/`

### Requisito: Valores padrão das preferências (CFG-09)

Sem preferências gravadas, o sistema DEVE usar o modelo `qwen3:8b`, a temperatura 0,10, a URI base `http://www.mestrado.edu/ontologias/`, o caminho do Protégé vazio e, como pasta de destino, `Documentos/OMAKER` na pasta do usuário (`default_output_dir` em `omaker/paths.py`), nunca a pasta corrente.

Fonte: `omaker/ui/pages/settings.py`, `omaker/llm/client.py` ; Verificado por: `tests/test_ui_pages.py::test_settings_keeps_default_model_when_only_gemini_saved` (modelo padrão), `tests/test_ui_pages.py::test_default_export_folder_does_not_depend_on_the_current_folder` (pasta de destino); os demais padrões não têm teste automatizado, `tests/test_ui_pages.py::test_first_run_uses_the_default_model_temperature_uri_and_protege_path`

#### Cenário: primeira execução

- **DADO** nenhuma preferência gravada
- **QUANDO** a página de Configurações abre
- **ENTÃO** o modelo selecionado é `qwen3:8b` e a temperatura é 0,10

### Requisito: Restos de versões antigas (CFG-10)

O sistema DEVE descartar da lista de modelos os nomes que começam com "gemini" (de versões antigas que usavam um serviço externo), voltando a `qwen3:8b` se nada sobrar, e DEVE apagar a chave `api_key` gravada ao salvar as configurações; a página NÃO DEVE ter campo de chave de API.

Fonte: `omaker/ui/pages/settings.py` ; Verificado por: `tests/test_ui_pages.py::test_settings_drops_old_gemini_models`, `tests/test_ui_pages.py::test_settings_keeps_default_model_when_only_gemini_saved`, `tests/test_ui_pages.py::test_settings_has_no_api_key_field`

#### Cenário: configurações de uma versão antiga

- **DADO** as preferências com `modelo=gemini-2.5-flash`, a lista ["gemini-2.5-flash", "qwen3:8b", "Gemini-Pro"] e uma `api_key`
- **QUANDO** a página de Configurações abre e o usuário salva
- **ENTÃO** a lista de modelos é ["qwen3:8b"] e o modelo selecionado é `qwen3:8b`
- **E** a chave `api_key` não existe mais nas preferências

### Requisito: Modelo informado pelo usuário (CFG-11)

O sistema DEVE permitir acrescentar à lista um modelo digitado pelo usuário (o nome exato do `ollama list`), sem duplicar nomes já presentes, e DEVE selecioná-lo.

Fonte: `omaker/ui/pages/settings.py` ; Verificado por: `tests/test_ui_pages.py::test_typed_model_is_added_to_the_list_and_selected`, `tests/test_ui_pages.py::test_typed_model_already_in_the_list_is_not_duplicated`, `tests/test_ui_pages.py::test_typed_model_already_in_the_list_is_selected`, `tests/test_ui_pages.py::test_blank_model_name_is_not_added`, `tests/test_ui_pages.py::test_added_model_is_saved_with_the_list`

#### Cenário: modelo quantizado

- **DADO** o usuário digita `qwen3:8b-q4_K_M` e clica no botão de acrescentar
- **QUANDO** a lista é atualizada
- **ENTÃO** `qwen3:8b-q4_K_M` aparece na lista e fica selecionado
