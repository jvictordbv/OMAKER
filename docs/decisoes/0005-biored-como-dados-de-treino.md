# 0005. BioRED como dados de treino do classificador de relações

- **Status:** Aceita
- **Data:** 2026-11-12
- **Decidido por:** João Victor (como experimento; o orientador ainda pode mudar o rumo), sobre proposta do Gustavo

## Contexto

O classificador PURE ([0004](0004-classificador-pure-marcadores-tipados.md)) era treinado com 31 frases escritas à mão. Com 4 exemplos de teste, o micro-F1 saía com intervalo de confiança de 0 a 1: nenhuma conclusão era possível, e a perda de treino perto de zero indicava memorização.

Nenhum conjunto público usa exatamente o esquema do OMAKER (`treats`, `causes`, `prevents` entre fármaco, doença e sintoma). A proposta comparou sete candidatos (BC5CDR, ADE, BioRED, i2b2 2010, SemRep gold standard, ChemProt e DDI 2013) e recomendou adaptar os dados ao esquema, e não o contrário.

## Decisão

- O PURE é treinado com o BioRED (600 resumos do PubMed), na divisão oficial (400 treino, 100 validação, 100 teste).
- O leitor (`omaker/relations/biored.py`) converte o formato PubTator para o esquema do OMAKER: químico vira `DRUG`, doença vira `DISEASE`; `Positive_Correlation` vira `causes` e `Negative_Correlation` vira `treats`.
- Cada par químico e doença na mesma frase vira um exemplo. Pares sem relação viram `no_relation`; pares com outra relação (como `Association`) ficam de fora; pares em frases diferentes não geram exemplo.
- Resultado da conversão: treino com 750 `causes`, 472 `treats` e 415 `no_relation`; validação com 453 exemplos; teste com 385.
- O comando grava uma amostra de 100 pares (`revisao_mapeamento.csv`) para conferência manual do mapeamento.

## Alternativas consideradas

- **Adaptar o esquema aos dados (rótulos do BioRED).** Facilitaria comparar com a literatura, mas mudaria `REL2ID`, a ontologia gerada e os prompts.
- **ADE e BC5CDR.** Bons para `causes`, nada para `treats`. A proposta incluía o ADE no treino; a decisão ficou só com o BioRED, como primeiro experimento.
- **i2b2 2010.** Melhor encaixe para `treats` (texto clínico), mas exige acordo de uso.
- **SemRep gold standard.** Tem os três rótulos com os mesmos nomes, mas são 500 frases: serve como teste externo, não como treino.
- **ChemProt e DDI 2013.** Sem doença nem sintoma.

## Consequências

### Positivas

- Teste com micro-F1 0,739 (IC 95% 0,694 a 0,785): `causes` com F1 0,795 e `treats` com 0,633. O intervalo, de cerca de 9 pontos, já permite comparar configurações. Com 10 épocas, o teste fica em 0,740: mais épocas não ajudam.
- Dados públicos, com divisão oficial, e um treino que pode ser retomado depois de uma queda.

### Negativas e riscos

- O BioRED anota relações por resumo, não por frase (supervisão distante). Parte dos rótulos, inclusive do teste, é ruído. A conferência manual da amostra ainda não foi registrada.
- O mapeamento é aproximado: `Negative_Correlation` nem sempre é tratamento.
- `prevents`, pares com sintoma e pares com gene ficam sem dados de treino.
- O número não é comparável aos resultados publicados do BioRED, que avaliam por documento e com outros rótulos.
- A licença do BioRED não é declarada pelo NCBI (ver [0009](0009-checkpoint-publicado-sem-texto.md)).

## Referências

- `omaker/relations/biored.py`, `omaker/relations/train.py`, `configs/pure_biored.toml`.
- Testes: `tests/test_biored.py::test_document_examples_maps_labels_per_sentence`, `tests/test_biored.py::test_pair_split_across_sentences_gives_no_example`, `tests/test_biored.py::test_load_biored_uses_official_parts`, `tests/test_training.py::test_resume_after_crash_matches_uninterrupted_run`.
- [PR #11](https://github.com/jvictordbv/OMAKER/pull/11): leitor do BioRED e treino retomável.
- Luo et al., "BioRED: a rich biomedical relation extraction dataset", Briefings in Bioinformatics, 2022.
- Notas internas do projeto: proposta das decisões D1, D3 e D5 (com a tabela dos sete candidatos) e registro do experimento do PURE com o BioRED (2026-11-12).
