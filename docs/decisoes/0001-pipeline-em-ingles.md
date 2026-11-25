# 0001. Pipeline em inglês, com aviso na interface

- **Status:** Aceita
- **Data:** 2026-11-12
- **Decidido por:** João Victor (com o orientador), sobre proposta do Gustavo

## Contexto

Todos os componentes que entendem o texto são em inglês: o NER `d4data/biomedical-ner-all`, o encoder `SpanBERT/spanbert-base-cased` do classificador de relações, os prompts do LLM e todos os conjuntos de dados candidatos ao treino (ver [0005](0005-biored-como-dados-de-treino.md)). A interface, porém, está em português e convidava a colar "Texto Médico". Na revisão do código de 2026-11-09, ficou claro que um texto em português tende a não render entidade nenhuma, e a geração termina no erro "No biomedical entities".

Para português existem recursos de NER (BioBERTpt, corpus SemClinBr), mas a busca feita para a proposta não achou um corpus em português anotado com relações de tratamento, causa e prevenção.

## Decisão

- O pipeline inteiro trabalha com texto em inglês.
- As páginas Gerador e Atualizador dizem que o texto deve estar em inglês, e o campo de texto repete o aviso.
- Antes de processar, a interface confere o idioma com uma heurística (`looks_non_english` em `omaker/domain/text.py`): conta palavras funcionais do português e do espanhol. Com proporção de 0,08 ou mais, pergunta "Processar mesmo assim?", com "Não" como padrão. Textos com menos de 12 palavras nunca são marcados.

## Alternativas consideradas

- **Inglês por dentro, com tradução da entrada pelo LLM.** Fica para depois, como recurso extra. A tradução introduz erros, as posições das entidades passam a ser do texto traduzido e a avaliação exigiria um conjunto de teste em português.
- **Português nativo.** Exigiria anotar um conjunto de relações em português, o que muda o escopo do trabalho.

## Consequências

### Positivas

- Toda a avaliação feita com dados em inglês (BioRED) vale para o uso real.
- A heurística não deu falso alarme em nenhum dos 600 resumos do BioRED (maior proporção medida: 0,055).

### Negativas e riscos

- O usuário brasileiro precisa traduzir o texto antes de colar.
- A heurística só reconhece português e espanhol. Um texto em francês ou alemão passa sem aviso e tende a render poucas entidades.
- A interface continua em português e o conteúdo em inglês, o que pode confundir quem chega ao programa sem ler o aviso.

## Referências

- `omaker/domain/text.py` (`looks_non_english`); `omaker/ui/pages/runner.py` (aviso e pergunta, comuns ao Gerador e ao Atualizador); `omaker/ui/pages/generator.py` (texto do campo de entrada).
- Testes: `tests/test_text_utils.py::test_portuguese_and_spanish_texts_are_flagged`, `tests/test_text_utils.py::test_short_text_is_never_flagged`, `tests/test_ui_generation.py::test_non_english_text_asks_before_generating`, `tests/test_ui_generation.py::test_pages_say_the_text_must_be_in_english`.
- [PR #14](https://github.com/jvictordbv/OMAKER/pull/14): aviso de idioma.
- Notas internas do projeto: proposta das decisões D1, D3 e D5 (2026-11-12) e resposta do João no mesmo dia.
