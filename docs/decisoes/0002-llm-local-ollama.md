# 0002. LLM local pelo Ollama

- **Status:** Aceita
- **Data:** 2026-11-09
- **Decidido por:** João Victor; a retirada das sobras do Gemini foi autorizada por ele em 2026-11-12 e feita pelo Gustavo

## Contexto

Nas primeiras versões, a geração de ontologia do OMAKER dependia do Gemini, um serviço na nuvem que exigia chave de API. Em 2026-11-09, o João substituiu esse motor pelo pipeline híbrido (commit `04ddc4b`): NER biomédico, um LLM local (qwen3, servido pelo Ollama) para entidades, taxonomia e, sem checkpoint, relações, e o classificador PURE. Os motivos não ficaram registrados por escrito na época; este registro documenta a escolha como ela está no código.

A revisão de 2026-11-09 achou incoerências da transição: a tela de Configurações ainda pedia a chave do Gemini, o motor trocava em silêncio qualquer modelo `gemini*` por `qwen3:8b`, e a conferência do modelo no Ollama exigia um nome que podia não estar instalado.

## Decisão

- O LLM roda na máquina do usuário, pelo Ollama (`OLLAMA_HOST`, padrão `http://localhost:11434`). O modelo padrão é `qwen3:8b`.
- O cliente (`OllamaClient` em `omaker/llm/client.py`) pede saída estruturada pelo esquema JSON do Ollama, desliga o bloco de raciocínio (`think: False`), fixa `num_ctx` em 8192 e repete a pergunta com o erro de leitura como retorno.
- Antes de usar o modelo, o cliente confere se o nome exato está instalado.
- O código do Gemini saiu do repositório: campo de chave de API, parâmetro `api_key` e a troca automática de nomes.
- O motor fala com o LLM por um protocolo (`LLMClient`), para que outro provedor possa entrar sem mexer no pipeline.

## Alternativas consideradas

- **Manter o Gemini.** Exige chave de API e conexão, e envia o texto do usuário a um serviço de terceiros. Foi retirado.
- **Ollama como padrão e Gemini como opção.** Proposto no plano de reestruturação (decisão D2) "só se a dissertação exigir". Não foi exigido, e manter dois provedores dobraria os testes.

## Consequências

### Positivas

- O texto não sai da máquina, e não há custo por chamada nem chave para gerenciar.
- Com temperatura 0 e semente fixa (`OMAKER_LLM_SEED`), a avaliação pode ser repetida.

### Negativas e riscos

- O usuário precisa instalar o Ollama e baixar o modelo à parte, fora do `.exe` (ver [0008](0008-executavel-leve-com-download.md)).
- O modelo pesa na máquina: na avaliação de ponta a ponta, o Ollama ocupou cerca de 9,6 GB de memória, e a avaliação foi interrompida mais de uma vez por falta de memória.
- Sem o Ollama no ar, a geração não começa: o motor confere o Ollama e o modelo antes de tudo, e a taxonomia depende sempre do LLM.
- Um modelo local de 8 bilhões de parâmetros pode entrar em laço, o que motivou o limite de [0013](0013-limite-de-tokens-do-llm.md).

## Referências

- `omaker/llm/client.py` (`OllamaClient`, `LLMClient`, `DEFAULT_MODEL`), `omaker/pipeline/engine.py` (`HybridEngine._client`), `omaker/config.py`.
- Testes: `tests/test_llm_client.py::test_check_requires_the_exact_name_ollama_will_use`, `tests/test_llm_client.py::test_retries_with_parse_error_feedback`, `tests/test_hybrid_engine.py::test_engine_entry_points_take_no_api_key`, `tests/test_e2e.py::test_llm_seed_sent_to_ollama`.
- [PR #1](https://github.com/jvictordbv/OMAKER/pull/1) (modelo e temperatura repassados pela interface), [PR #3](https://github.com/jvictordbv/OMAKER/pull/3) (protocolo `LLMClient`), [PR #10](https://github.com/jvictordbv/OMAKER/pull/10) (retirada do Gemini), [PR #13](https://github.com/jvictordbv/OMAKER/pull/13) (nome exato do modelo).
- Notas internas do projeto: revisão do código de 2026-11-09 e plano de reestruturação (decisão D2).
