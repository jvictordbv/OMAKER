# 0004. Classificador de relações PURE com marcadores tipados

- **Status:** Aceita
- **Data:** 2026-10-20
- **Decidido por:** João Victor (commit `0d727f8`, reescrito por ele em `04ddc4b`); correções do Gustavo na reestruturação

## Contexto

Depois de achar as entidades, o OMAKER precisa decidir, para cada par na mesma frase, se há `treats`, `causes`, `prevents` ou nenhuma relação (`no_relation`). É o único componente do sistema treinado pela equipe, e o centro do trabalho de mestrado. O LLM também consegue classificar pares, mas sem uma confiança numérica e com custo de uma chamada por lote de pares.

## Decisão

- O classificador segue a abordagem PURE (Zhong e Chen, 2021): marcadores tipados em volta do sujeito e do objeto, por exemplo `<S:DRUG> Paracetamol </S:DRUG> treats <O:SYMPTOM> fever </O:SYMPTOM>`.
- Os marcadores são gerados a partir de `ENTITY_TYPES` (DRUG, SYMPTOM, DISEASE, GENE), nos dois papéis: 16 tokens especiais acrescentados ao vocabulário.
- O encoder é o `SpanBERT/spanbert-base-cased`. A representação do par é a concatenação dos estados dos marcadores de abertura do sujeito e do objeto, seguida de uma camada oculta com ReLU e dropout de 0,1.
- Só são classificados os pares de tipos de `ALLOWED_TYPE_PAIRS`: fármaco e sintoma, fármaco e doença, doença e sintoma (nos dois sentidos).
- Rótulos, tipos e marcadores vivem só em `omaker/domain/labels.py`. O checkpoint grava `rel2id` e `entity_types`, e a carga recusa um checkpoint que não bata com eles.
- Sem checkpoint disponível, as relações são classificadas pelo LLM (`classify_pairs`).

## Alternativas consideradas

- **Só o LLM para relações.** Continua como reserva. Não dá uma confiança calibrável ([0007](0007-calibracao-por-temperatura.md)) e não é um modelo treinável, que é o objeto do trabalho.
- **Encoder biomédico (BioBERT, PubMedBERT).** A primeira versão do código já citava o BioBERT como opção. Não houve comparação registrada entre encoders, nem justificativa escrita para o SpanBERT; um encoder treinado em texto biomédico continua sendo uma variação a testar.

## Consequências

### Positivas

- Treinado com o BioRED, o classificador chega a micro-F1 0,739 no teste (IC 95% 0,694 a 0,785; 385 exemplos), com as entidades do gabarito ([0005](0005-biored-como-dados-de-treino.md)).
- Um único caminho de código (`_encode`) serve ao treino, à avaliação e à inferência, então os três não divergem.

### Negativas e riscos

- Mudar `REL2ID` ou `ENTITY_TYPES` invalida todos os checkpoints treinados.
- Frases com mais de 256 tokens podem perder um marcador no corte; o par é marcado como inválido e não recebe classe.
- O BioRED só ensina pares químico e doença. Os marcadores de SYMPTOM e os pares com sintoma não têm dados de treino públicos, e `prevents` também não ([0005](0005-biored-como-dados-de-treino.md)).
- O checkpoint guarda o encoder inteiro (438 MB), e a carga ainda baixa o SpanBERT base para montar a arquitetura: o mesmo encoder ocupa espaço duas vezes.
- O `transformers` 5 carrega o SpanBERT em fp16; a inferência quebrava com checkpoint treinado até a correção que força float32.

## Referências

- `omaker/relations/model.py` (`RelationExtractorPURE`, `mark_text`, `_encode`, `load`), `omaker/domain/labels.py`, `omaker/llm/relations.py` (`classify_pairs`).
- Testes: `tests/test_relation_extractor.py::test_load_fp16_base_model_predicts`, `tests/test_relation_extractor.py::test_load_rejects_incompatible_labels`, `tests/test_relation_extractor.py::test_spanbert_roundtrip`.
- [PR #1](https://github.com/jvictordbv/OMAKER/pull/1) (correção de fp16 e float32), [PR #8](https://github.com/jvictordbv/OMAKER/pull/8) (treino por configuração, divisão fixa).
- Z. Zhong e D. Chen, "A Frustratingly Easy Approach for Entity and Relation Extraction", NAACL 2021.
- Notas internas do projeto: revisão do código de 2026-11-09 (itens 21 e 22).
