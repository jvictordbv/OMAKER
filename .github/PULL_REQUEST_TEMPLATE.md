## O que é

<!-- Uma ou duas frases: o que este PR entrega. Se houver issue, cite: "Resolve #N". -->

## Por quê

<!-- O problema ou a necessidade que motivou a mudança: o que estava errado, faltando ou decidido.
     Cite números, a decisão (docs/decisoes/NNNN-*.md) ou o requisito (docs/requisitos/) quando houver. -->

## Objetivo

<!-- O resultado esperado depois do merge, do ponto de vista de quem usa ou mantém o OMAKER. -->

## O que muda

<!-- A lista das mudanças, com os arquivos principais. -->

## Impacto e riscos

<!-- Quem ou o que é afetado (usuário, .exe, treino, avaliação, dados), compatibilidade com versões
     anteriores, o que pode dar errado e como desfazer. Escreva "Nenhum" se for o caso. -->

## Como foi testado

<!-- Testes novos ou alterados; para mudanças na interface, o passo a passo feito à mão;
     para treino/avaliação, o comando executado e o resultado. -->

## Checklist

- [ ] `uv run ruff check .` passa
- [ ] `uv run pytest -q -m "not slow and not ollama"` passa
- [ ] Comportamento novo ou corrigido tem teste
- [ ] README atualizado, se mudou algum comando, variável de ambiente ou requisito
- [ ] Requisitos e rastreabilidade (`docs/requisitos/`) atualizados, se mudou algum comportamento
- [ ] Registro de decisão novo (`docs/decisoes/`), se a mudança é uma decisão de projeto
- [ ] Arquivos de dados novos em `omaker/` estão no `OMAKER.spec`

## Referências

<!-- PRs, registros de decisão, requisitos, experimentos ou execuções (runs/) relacionados. -->
