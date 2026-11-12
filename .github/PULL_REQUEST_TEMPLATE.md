## O que muda

<!-- Uma ou duas frases: o problema e a solução. Se houver issue, cite: "Resolve #N". -->

## Como foi testado

<!-- Testes novos ou alterados; para mudanças na interface, o passo a passo feito à mão;
     para treino/avaliação, o comando executado e o resultado. -->

## Checklist

- [ ] `uv run ruff check .` passa
- [ ] `uv run pytest -q -m "not slow and not ollama"` passa
- [ ] Comportamento novo ou corrigido tem teste
- [ ] README atualizado, se mudou algum comando, variável de ambiente ou requisito
- [ ] Arquivos de dados novos em `omaker/` estão no `OMAKER.spec`
