# Integração com LLM

## Propósito

Falar com o LLM local (Qwen3 no Ollama) de forma previsível: conferir antes de começar se o Ollama e o modelo existem, pedir sempre JSON num esquema fixo, tentar de novo quando a resposta não é JSON válido, falhar rápido quando o modelo entra em laço e seguir sem o LLM quando ele não é a única fonte de entidades. As escolhas estão nos registros de decisão [0002](../../../decisoes/0002-llm-local-ollama.md) e [0013](../../../decisoes/0013-limite-de-tokens-do-llm.md).

## Requisitos

### Requisito: Ollama local, sem chave (LLM-01)

O sistema DEVE falar só com o Ollama, no endereço de `OLLAMA_HOST` ([CFG-02](../configuracao/spec.md)), pela rota `/api/chat` sem streaming, e NÃO DEVE pedir nem guardar chave de API.

Fonte: `omaker/llm/client.py`, `omaker/pipeline/engine.py` ; Verificado por: `tests/test_hybrid_engine.py::test_engine_entry_points_take_no_api_key`, `tests/test_ui_pages.py::test_settings_has_no_api_key_field`

#### Cenário: assinaturas do motor

- **DADO** as funções públicas `gerar_ontologia` e `atualizar_ontologia`
- **QUANDO** os parâmetros delas são inspecionados
- **ENTÃO** nenhuma tem o parâmetro `api_key`

### Requisito: Verificação antes de extrair (LLM-02)

Quando alguma etapa for usar o LLM, o sistema DEVE conferir se o Ollama responde e se o modelo está instalado, antes do NER se já se sabe que o LLM será usado (entidades pelo LLM ou taxonomia) e, no caso restante, só quando as relações caírem no LLM (sem checkpoint do PURE); NÃO DEVE exigir o Ollama quando nenhuma etapa o usa (modo `ner`, com o PURE e sem taxonomia); e DEVE falhar com uma mensagem acionável: "`ollama serve`" quando o Ollama não responde, ou a lista dos modelos instalados e o comando `ollama pull <modelo>` quando o modelo falta.

Fonte: `omaker/llm/client.py`, `omaker/pipeline/engine.py` ; Verificado por: `tests/test_llm_client.py::test_check_missing_model_suggests_pull`, `tests/test_llm_client.py::test_check_lists_installed_models`, `tests/test_hybrid_engine.py::test_ollama_is_not_required_when_no_step_uses_the_llm`, `tests/test_hybrid_engine.py::test_llm_client_is_created_once_when_needed`

#### Cenário: modelo não instalado

- **DADO** o Ollama só com o `qwen3:8b` instalado e o modelo `llama3` nas Configurações
- **QUANDO** a geração começa
- **ENTÃO** ela falha antes de extrair entidades
- **E** a mensagem lista "qwen3:8b" e sugere "ollama pull llama3"

#### Cenário: avaliação sem o LLM

- **DADO** o modo `ner`, um checkpoint do PURE e a extração sem taxonomia (o sistema `pure` da avaliação)
- **QUANDO** a extração roda com o Ollama desligado
- **ENTÃO** ela termina normalmente, sem conferir o Ollama

### Requisito: Nome exato do modelo (LLM-03)

O sistema DEVE exigir o nome exato do modelo, como o Ollama o usa: um nome sem tag DEVE ser comparado como `<nome>:latest`, e uma tag diferente NÃO DEVE ser aceita no lugar da configurada.

Fonte: `omaker/llm/client.py` ; Verificado por: `tests/test_llm_client.py::test_check_requires_the_exact_name_ollama_will_use`

#### Cenário: só outra tag instalada

- **DADO** o Ollama só com `qwen3:8b-q4_K_M` instalado
- **QUANDO** o modelo configurado é `qwen3:8b`
- **ENTÃO** a verificação falha

#### Cenário: nome sem tag

- **DADO** o Ollama com `qwen3:latest` instalado
- **QUANDO** o modelo configurado é `qwen3`
- **ENTÃO** a verificação passa

### Requisito: Saída estruturada (LLM-04)

O sistema DEVE enviar em cada pedido o esquema JSON esperado (campo `format`) e `think` desligado, e DEVE ler a resposta removendo um bloco `<think>...</think>` e uma cerca de código antes de interpretar o JSON; se o Ollama recusar o campo `think` (erro 400), o pedido DEVE ser repetido sem ele.

Fonte: `omaker/llm/client.py` ; Verificado por: `tests/test_llm_client.py::test_parses_think_block_and_fenced_json`; a repetição sem `think` não tem teste automatizado

#### Cenário: resposta com raciocínio e cerca

- **DADO** o modelo responde com um bloco `<think>` seguido de JSON dentro de uma cerca de código
- **QUANDO** a resposta é lida
- **ENTÃO** o resultado é o objeto JSON, sem o raciocínio

### Requisito: Nova tentativa com o erro (LLM-05)

Quando a resposta não for JSON válido, o sistema DEVE repetir o pedido até mais duas vezes, mandando ao modelo a própria resposta e o erro de leitura, e DEVE levantar `LLMError` depois da terceira resposta inválida.

Fonte: `omaker/llm/client.py` ; Verificado por: `tests/test_llm_client.py::test_retries_with_parse_error_feedback`, `tests/test_llm_client.py::test_raises_after_retries`

#### Cenário: JSON inválido e depois válido

- **DADO** o modelo responde primeiro com texto que não é JSON e depois com JSON válido
- **QUANDO** o pedido é feito
- **ENTÃO** o resultado é o JSON da segunda resposta

#### Cenário: três respostas inválidas

- **DADO** o modelo nunca devolve JSON válido
- **QUANDO** o pedido é feito
- **ENTÃO** o cliente levanta `LLMError` depois de três tentativas

### Requisito: Limite de tokens e falha rápida em laço (LLM-06)

O sistema DEVE limitar cada resposta a 4.096 tokens (`num_predict`) e, quando o Ollama informar que a resposta parou pelo limite, DEVE levantar `LLMError` na hora, sem nova tentativa, porque com temperatura 0 e semente fixa a repetição daria o mesmo laço.

Fonte: `omaker/llm/client.py` ; Verificado por: `tests/test_llm_client.py::test_output_limit_stops_a_looping_model_without_retrying`

#### Cenário: modelo em laço

- **DADO** o Ollama devolve uma resposta incompleta com `done_reason` igual a `length`
- **QUANDO** o pedido é feito
- **ENTÃO** o cliente levanta `LLMError` com a mensagem "hit the output limit (4096 tokens)"
- **E** o Ollama recebe um único pedido

### Requisito: Contexto e tempo limite (LLM-07)

O sistema DEVE pedir ao Ollama uma janela de contexto de 8.192 tokens (`num_ctx`), para que prompts longos não sejam cortados em silêncio, e DEVE usar um tempo limite de 600 s por pedido.

Fonte: `omaker/llm/client.py` ; Verificado por: `tests/test_llm_client.py::test_parses_think_block_and_fenced_json` (`num_ctx`); o tempo limite de 600 s não tem teste automatizado

#### Cenário: opções do pedido

- **DADO** um pedido qualquer ao LLM
- **QUANDO** ele é enviado
- **ENTÃO** as opções incluem `num_ctx` 8192 e `num_predict` 4096

### Requisito: Semente do LLM (LLM-08)

O sistema DEVE enviar ao Ollama a semente de `OMAKER_LLM_SEED` quando ela estiver definida ([CFG-05](../configuracao/spec.md)) e NÃO DEVE enviar semente quando ela não estiver.

Fonte: `omaker/llm/client.py`, `omaker/config.py` ; Verificado por: `tests/test_e2e.py::test_llm_seed_sent_to_ollama`

#### Cenário: semente definida

- **DADO** `OMAKER_LLM_SEED=7`
- **QUANDO** um pedido é enviado
- **ENTÃO** as opções do pedido têm `seed` igual a 7

### Requisito: Queda para o NER (LLM-09)

No modo `both`, uma falha do LLM na extração de entidades DEVE ser registrada no log e a extração DEVE seguir só com as entidades do NER; no modo `llm`, a mesma falha DEVE interromper a operação com `LLMError`.

Fonte: `omaker/pipeline/engine.py` ; Verificado por: `tests/test_hybrid_engine.py::test_llm_entity_loop_falls_back_to_ner_entities`, `tests/test_hybrid_engine.py::test_llm_entity_loop_is_an_error_when_the_llm_is_the_only_source`

#### Cenário: laço no modo both

- **DADO** `OMAKER_ENTITIES=both` e o LLM em laço no pedido de entidades
- **QUANDO** o motor extrai as entidades
- **ENTÃO** o log mostra "[LLM-NER] skipped (...). Using the NER entities only."
- **E** a taxonomia tem só as entidades do NER

#### Cenário: laço no modo llm

- **DADO** `OMAKER_ENTITIES=llm` e o LLM em laço
- **QUANDO** o motor extrai as entidades
- **ENTÃO** a extração falha com `LLMError`

### Requisito: Cliente substituível (LLM-10)

O motor DEVE depender só do protocolo `LLMClient` (atributo `model` e método `chat_json`), de modo que outro cliente com a mesma interface rode o pipeline sem mudança no motor.

Fonte: `omaker/llm/client.py`, `omaker/pipeline/engine.py` ; Verificado por: `tests/test_llm_protocol.py::test_clients_follow_protocol`, `tests/test_llm_protocol.py::test_engine_runs_with_any_llm_client`

#### Cenário: cliente falso

- **DADO** um cliente que implementa `model` e `chat_json` sem falar com o Ollama
- **QUANDO** o motor extrai as relações e a taxonomia com ele
- **ENTÃO** a extração termina com a tripla (Aspirin, prevents, stroke), sem chamar o Ollama
