# 0009. Checkpoint publicado sem as frases de treino

- **Status:** Aceita
- **Data:** 2026-11-24
- **Decidido por:** Gustavo (formato e publicação da Release), com a aprovação do João Victor para distribuir o modelo do BioRED no `.exe` leve

## Contexto

O `.exe` leve baixa o checkpoint do PURE de uma Release pública ([0008](0008-executavel-leve-com-download.md)). O checkpoint de treino guardava, além dos pesos, as 794 frases de treino, usadas para conferir se uma frase do gabarito de avaliação apareceu no treino (contaminação). Essas frases são trechos de resumos do PubMed, cujos direitos são das editoras. Publicá-las junto com o modelo seria redistribuir texto de terceiros.

## Decisão

- O arquivo publicado guarda só o sha256 de cada frase de treino normalizada (`train_text_hashes`), no lugar do texto. Isso basta para a conferência de contaminação.
- O treino passa a gravar assim; checkpoints antigos, com o texto, continuam aceitos.
- A exportação (`omaker/relations/release.py`) gera `omaker_pure.pt`, `omaker_pure.calibration.json` e `SHA256SUMS`.
- Os arquivos foram publicados na Release `pure-biored-v1` do repositório. O checkpoint tem 438 MB, e o download confere o sha256 antes de usar o arquivo.

## Alternativas consideradas

- **Publicar o checkpoint como estava.** Mais simples, mas redistribui texto do PubMed.
- **Retirar a lista de frases sem pôr nada no lugar.** Perderia a conferência de contaminação na avaliação.
- **Não publicar o modelo** (cada usuário treina o seu). Inviável para quem só quer usar o programa: o treino exige baixar o BioRED e leva horas na CPU (cerca de 8 s por passo, medido em 2026-11-12).

## Consequências

### Positivas

- A conferência de contaminação continua funcionando com o arquivo publicado.
- O download é verificável: o mesmo sha256 está no código e no `SHA256SUMS` da Release.

### Negativas e riscos

- Os pesos continuam sendo derivados do BioRED, cuja licença não é declarada pelo NCBI. O risco foi considerado baixo, mas não foi eliminado.
- Um hash só detecta frases idênticas depois da normalização; uma frase levemente alterada passa como nova.
- Trocar o modelo exige publicar uma Release nova e atualizar o sha256 no código.

## Referências

- `omaker/relations/release.py` (`export`), `omaker/relations/data.py` (`text_fingerprint`), `omaker/relations/download.py` (`RELEASE`, `PURE_MODEL`), `omaker/evaluation/e2e.py` (conferência de contaminação).
- Testes: `tests/test_download.py::test_export_strips_training_texts`, `tests/test_download.py::test_published_hashes_are_filled_in`, `tests/test_e2e.py::test_contamination_with_hashed_training_texts`.
- [PR #20](https://github.com/jvictordbv/OMAKER/pull/20): download do checkpoint e exportação sem as frases.
- Release [`pure-biored-v1`](https://github.com/jvictordbv/OMAKER/releases/tag/pure-biored-v1).
- Notas internas do projeto: diário de 2026-11-24.
