# 0013. Limite de tokens na resposta do LLM

- **Status:** Aceita
- **Data:** 2026-11-12
- **Decidido por:** Gustavo

## Contexto

Na avaliação com o gabarito do BioRED, o `qwen3:8b-q4_K_M` entrou em laço no resumo `biored-28068934`: repetia a mesma lista de entidades ("endoscopic biopsy", "surgically resected specimens") sem fechar o JSON. Com temperatura 0 e semente fixa, o laço se repetia sempre no mesmo texto. A chamada só terminava no tempo limite de 600 s, e a avaliação caía. Na interface, o usuário esperaria 10 minutos por tentativa, e o cliente ainda repetia a pergunta depois de um erro de leitura.

## Decisão

- O cliente do Ollama envia um teto para a resposta (`num_predict`), com padrão de 4.096 tokens (`max_tokens` em `OllamaClient`).
- Se a resposta parar por tamanho (`done_reason == "length"`), o cliente falha logo com `LLMError`, sem repetir a pergunta: com temperatura baixa, repetir daria o mesmo laço.
- No modo de entidades `both`, se o LLM falhar, o pipeline segue com as entidades do NER e registra o aviso no log. No modo `llm`, o erro sobe.
- Na avaliação de ponta a ponta, um documento com `LLMError` conta como sem previsões, fica registrado (`llm_errors`) e é tentado de novo numa retomada.

## Alternativas consideradas

- **Confiar no tempo limite de 600 s.** Era o comportamento anterior: 10 minutos perdidos por chamada e a avaliação interrompida.
- **Reduzir o tempo limite.** Penalizaria máquinas lentas, em que uma resposta legítima demora, sem distinguir laço de lentidão.
- **Repetir a pergunta.** Com temperatura 0 e semente fixa, o laço volta igual.

## Consequências

### Positivas

- O pipeline `both+pure` no resumo que travava, com teto de 1.500 tokens, terminou em 124 s com o aviso, em vez de 600 s e erro.
- A avaliação completa com o gabarito do BioRED pôde terminar; o resumo do laço contou como sem previsões no sistema `llm`.

### Negativas e riscos

- Uma resposta legítima maior que 4.096 tokens (um texto longo, com muitas entidades) é tratada como laço e perdida.
- No modo `both`, a queda para o NER é silenciosa para quem não lê o log: a ontologia sai, mas com menos entidades.
- A taxonomia e a classificação de relações pelo LLM não têm reserva: se baterem no teto, a geração falha.
- O laço em si não foi resolvido, só contido; ele depende do modelo e do texto.

## Referências

- `omaker/llm/client.py` (`OllamaClient`, `max_tokens`, `_options`), `omaker/pipeline/engine.py` (`HybridEngine.extrair`), `omaker/evaluation/e2e.py`.
- Testes: `tests/test_llm_client.py::test_output_limit_stops_a_looping_model_without_retrying`, `tests/test_hybrid_engine.py::test_llm_entity_loop_falls_back_to_ner_entities`, `tests/test_hybrid_engine.py::test_llm_entity_loop_is_an_error_when_the_llm_is_the_only_source`, `tests/test_e2e.py::test_llm_error_counts_as_no_prediction_and_is_recorded`.
- [PR #16](https://github.com/jvictordbv/OMAKER/pull/16): limite da resposta e queda para o NER.
- Notas internas do projeto: registro do experimento do PURE com o BioRED (seção do laço do LLM).
