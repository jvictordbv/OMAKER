# Extração de relações

## Propósito

Decidir, para cada par de entidades da mesma frase, se o texto afirma uma relação `treats`, `causes` ou `prevents`. O classificador principal é o PURE (SpanBERT com marcadores tipados), com confiança calibrada; sem ele, o LLM classifica. As triplas que contrariam o domínio da relação são descartadas. As escolhas estão nos registros de decisão [0004](../../../decisoes/0004-classificador-pure-marcadores-tipados.md) e [0007](../../../decisoes/0007-calibracao-por-temperatura.md).

## Requisitos

### Requisito: Divisão em frases (REL-01)

O sistema DEVE dividir o texto em frases depois de `.`, `!` ou `?` seguidos de espaço e de maiúscula ou dígito, e NÃO DEVE dividir depois das abreviações conhecidas (por exemplo "Dr.", "e.g.", "vs.", "Fig."); uma letra isolada seguida de ponto continua encerrando a frase.

Fonte: `omaker/domain/text.py` ; Verificado por: `tests/test_text_utils.py::test_split_keeps_title_abbreviations`, `tests/test_text_utils.py::test_split_keeps_latin_and_figure_abbreviations`, `tests/test_text_utils.py::test_split_still_splits_real_boundaries`

#### Cenário: abreviação de título

- **DADO** o texto "Dr. Smith gave aspirin."
- **QUANDO** o texto é dividido em frases
- **ENTÃO** o resultado é uma frase só

#### Cenário: limites reais

- **DADO** o texto "Is 5 mg safe? Yes. Hepatitis B. Patients recovered."
- **QUANDO** o texto é dividido em frases
- **ENTÃO** o resultado tem quatro frases: "Is 5 mg safe?", "Yes.", "Hepatitis B." e "Patients recovered."

### Requisito: Pares candidatos na mesma frase (REL-02)

O sistema DEVE formar pares ordenados (sujeito, objeto) só entre menções da mesma frase e só com os tipos permitidos (`DRUG` e `SYMPTOM`, `DRUG` e `DISEASE`, `DISEASE` e `SYMPTOM`, `SYMPTOM` e `DISEASE`), usando a frase como texto do par e posições relativas a ela.

Fonte: `omaker/nlp/pairs.py`, `omaker/domain/labels.py` ; Verificado por: `tests/test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output` (de forma indireta: a ordem e a quantidade de pares definem os ids da resposta do LLM)

#### Cenário: entidades em frases diferentes

- **DADO** "Aspirin prevents stroke. Chemotherapy causes nausea."
- **QUANDO** os pares são formados
- **ENTÃO** existem os pares (Aspirin, stroke) e (Chemotherapy, nausea)
- **E** não existe par entre "Aspirin" e "nausea"

#### Cenário: tipo não permitido

- **DADO** dois fármacos na mesma frase
- **QUANDO** os pares são formados
- **ENTÃO** nenhum par entre os dois fármacos é criado

### Requisito: Texto sem pares (REL-03)

O sistema NÃO DEVE carregar, baixar nem chamar um classificador quando não houver pares candidatos; nesse caso nenhuma tripla é produzida e a geração continua para a taxonomia.

Fonte: `omaker/pipeline/engine.py` ; Verificado por: `tests/test_engine_extraction.py::test_text_without_pairs_loads_downloads_and_calls_no_classifier`

#### Cenário: entidades isoladas

- **DADO** um texto com um único fármaco
- **QUANDO** o motor extrai as relações
- **ENTÃO** o log registra "0 candidate pairs" e "0 triples kept"
- **E** nenhum download do classificador é tentado

### Requisito: Classificador PURE com marcadores tipados (REL-04)

O sistema DEVE classificar cada par com o PURE: insere marcadores tipados (`<S:TIPO>`, `</S:TIPO>`, `<O:TIPO>`, `</O:TIPO>`) em volta do sujeito e do objeto, junta as representações dos dois marcadores de abertura e devolve um rótulo entre `treats`, `causes`, `prevents` e `no_relation`, com a confiança dada por softmax(logits / temperatura).

Fonte: `omaker/relations/model.py`, `omaker/domain/labels.py` ; Verificado por: `tests/test_relation_extractor.py::test_load_fp16_base_model_predicts`, `tests/test_relation_extractor.py::test_spanbert_roundtrip` (slow), `tests/test_calibration.py::test_confidences_divide_logits_by_temperature`

#### Cenário: par marcado

- **DADO** a frase "aspirin prevents stroke ." com sujeito "aspirin" (`DRUG`) e objeto "stroke" (`DISEASE`)
- **QUANDO** o PURE classifica o par
- **ENTÃO** o resultado é um dos quatro rótulos, com confiança entre 0 e 1

#### Cenário: modelo base em meia precisão

- **DADO** um encoder salvo em float16, como o SpanBERT publicado
- **QUANDO** o PURE é criado, salvo e carregado de novo
- **ENTÃO** todos os parâmetros ficam em float32 e a predição funciona

### Requisito: Par com marcador cortado (REL-05)

O sistema DEVE limitar a entrada do PURE a 256 tokens e DEVE classificar como `no_relation`, com confiança 0, todo par cujo marcador de sujeito ou de objeto tenha sido cortado.

Fonte: `omaker/relations/model.py` ; Verificado por: `tests/test_relation_extractor.py::test_pair_whose_object_marker_is_cut_is_no_relation_with_zero_confidence`, `tests/test_relation_extractor.py::test_pure_input_is_truncated_to_256_tokens`

#### Cenário: frase longa demais

- **DADO** uma frase em que o objeto aparece depois do token 256
- **QUANDO** o PURE classifica o par
- **ENTÃO** o resultado é (`no_relation`, 0,0)

### Requisito: Checkpoint incompatível recusado (REL-06)

O sistema DEVE recusar um checkpoint cujos rótulos de relação ou tipos de entidade sejam diferentes dos de `omaker/domain/labels.py`, com um erro que manda treinar de novo.

Fonte: `omaker/relations/model.py` ; Verificado por: `tests/test_relation_extractor.py::test_load_rejects_incompatible_labels`

#### Cenário: rótulos antigos

- **DADO** um checkpoint gravado com outro conjunto de rótulos
- **QUANDO** o PURE tenta carregá-lo
- **ENTÃO** o carregamento falha com um erro que contém "Retrain"

### Requisito: Escolha do classificador (REL-07)

O sistema DEVE usar o PURE quando o checkpoint existir no caminho padrão ([CFG-04](../configuracao/spec.md)); se ele faltar, DEVE tentar baixá-lo ([MOD-24](../modelo-de-relacoes/spec.md)) e, se ainda faltar, DEVE classificar os pares com o LLM.

Fonte: `omaker/pipeline/engine.py` ; Verificado por: `tests/test_hybrid_engine.py::test_missing_checkpoint_is_downloaded_before_falling_back_to_the_llm`

#### Cenário: sem checkpoint e sem internet

- **DADO** o checkpoint não existe e o download falha
- **QUANDO** o motor classifica os pares
- **ENTÃO** o download foi tentado para o caminho padrão
- **E** as relações vêm do LLM, por exemplo (Aspirin, prevents, stroke)

### Requisito: Limite de confiança (REL-08)

O sistema DEVE descartar as previsões do PURE com confiança abaixo do limite; o limite é o do arquivo de calibração do checkpoint, quando existir, e 0,70 caso contrário. Com calibração, o log DEVE informar a temperatura e o limite usados.

Fonte: `omaker/pipeline/engine.py`, `omaker/relations/model.py`, `omaker/domain/labels.py` ; Verificado por: `tests/test_hybrid_engine.py::test_pure_uses_the_calibrated_threshold`

#### Cenário: sem calibração

- **DADO** um checkpoint sem arquivo de calibração e uma previsão `prevents` com confiança 0,6
- **QUANDO** o motor filtra as previsões
- **ENTÃO** nenhuma tripla é mantida, porque 0,6 é menor que 0,70

#### Cenário: com calibração

- **DADO** um checkpoint calibrado com limite 0,5 e a mesma previsão com confiança 0,6
- **QUANDO** o motor filtra as previsões
- **ENTÃO** a tripla (Aspirin, prevents, stroke) é mantida

### Requisito: Classificação pelo LLM (REL-09)

Sem o PURE, o sistema DEVE enviar os pares ao LLM em lotes de 15, aceitar só os rótulos `treats`, `causes`, `prevents` e `no_relation` para ids existentes, tratar como `no_relation` o par sem resposta válida e registrar no log que as relações não têm confiança.

Fonte: `omaker/llm/relations.py` ; Verificado por: `tests/test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output`

#### Cenário: id fora do intervalo

- **DADO** o LLM responde também para o id 99, que não existe
- **QUANDO** as respostas são lidas
- **ENTÃO** a resposta do id 99 é ignorada e as demais valem

#### Cenário: relações sem confiança

- **DADO** as relações vieram do LLM
- **QUANDO** o motor filtra as previsões
- **ENTÃO** nenhuma é descartada por limite de confiança
- **E** o log mostra "classifying pairs with the LLM (no confidence scores)"

### Requisito: Uma tripla por fato (REL-10)

O sistema DEVE manter uma única tripla por (sujeito, relação, objeto), sem diferenciar maiúsculas, ficando com a de maior confiança, e NÃO DEVE manter previsões `no_relation`.

Fonte: `omaker/pipeline/engine.py` ; Verificado por: `tests/test_engine_extraction.py::test_the_same_fact_in_two_sentences_gives_one_triple_with_the_highest_confidence`, `tests/test_engine_extraction.py::test_no_relation_predictions_are_never_kept_as_triples`

#### Cenário: o mesmo fato em duas frases

- **DADO** "Aspirin prevents stroke" previsto em duas frases, com confianças 0,8 e 0,9
- **QUANDO** as triplas são reunidas
- **ENTÃO** fica uma tripla (Aspirin, prevents, stroke) com confiança 0,9

### Requisito: Domínio das relações (REL-11)

O sistema DEVE descartar as triplas `treats` e `prevents` cujo sujeito não seja um fármaco (`Drug`) e DEVE registrar cada descarte no log com "[SKIP]"; `causes` não tem restrição de sujeito.

Fonte: `omaker/pipeline/engine.py`, `omaker/domain/labels.py` ; Verificado por: `tests/test_hybrid_engine.py::test_taxonomy_validation_rejects_bad_llm_output`

#### Cenário: doença que "trata"

- **DADO** o classificador previu (tumor, treats, nausea), com "tumor" do tipo `DISEASE`
- **QUANDO** o filtro de domínio é aplicado
- **ENTÃO** a tripla é descartada
- **E** o log tem uma linha "[SKIP]" que cita "tumor"

### Requisito: Prompt de relações otimizado, opcional (REL-12)

Com `OMAKER_LLM_PROMPT=optimized` e o arquivo `omaker/llm/prompts/relations_optimized.json` presente, o sistema DEVE classificar as relações pelo LLM com a instrução e os exemplos desse arquivo; sem a variável, DEVE usar o prompt escrito à mão; com a variável e sem o arquivo, DEVE registrar no log e usar o prompt escrito à mão. O uso NÃO DEVE depender do pacote `dspy`.

Fonte: `omaker/llm/relations.py` ; Verificado por: `tests/test_llm_relations_prompt.py::test_default_prompt_is_the_handwritten_one`, `tests/test_llm_relations_prompt.py::test_handwritten_prompt_is_instruction_plus_json_request`, `tests/test_llm_relations_prompt.py::test_optimized_prompt_sends_instruction_and_examples`, `tests/test_llm_relations_prompt.py::test_optimized_requested_without_file_falls_back_to_default`

#### Cenário: prompt otimizado instalado

- **DADO** `OMAKER_LLM_PROMPT=optimized` e o prompt otimizado instalado
- **QUANDO** o LLM classifica os pares
- **ENTÃO** o prompt enviado contém a instrução otimizada e os exemplos

#### Cenário: arquivo ausente

- **DADO** `OMAKER_LLM_PROMPT=optimized` e nenhum prompt instalado
- **QUANDO** o LLM classifica os pares
- **ENTÃO** o log avisa e o prompt escrito à mão é usado
