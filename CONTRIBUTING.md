# Como contribuir com o OMAKER

Obrigado pelo interesse. Este guia explica como preparar o ambiente, propor uma mudança e o que um pull request precisa ter para ser integrado.

## Antes de começar

- Para um **bug**, abra uma issue com o modelo "Relato de bug". Diga o que você fez, o que esperava, o que aconteceu e o trecho do log.
- Para uma **mudança maior** (nova funcionalidade, troca de modelo ou de dataset, mudança no esquema de relações), abra uma issue antes de escrever o código. Algumas decisões do projeto dependem do autor e do orientador.
- Mudanças pequenas e correções podem ir direto para um pull request.

## Ambiente

```bash
git clone https://github.com/jvictordbv/OMAKER.git
cd OMAKER
uv sync --extra dev
uv run pre-commit install        # roda ruff e a suíte rápida antes de cada commit
```

Requisitos externos (Ollama, Java, Protégé): ver a seção [Requisitos](README.md#requisitos) do README. Rode os comandos sempre a partir da raiz do repositório.

## Fluxo de trabalho

1. Atualize a `main` e crie um branch curto para a mudança:
   ```bash
   git switch main && git pull
   git switch -c fix/descricao-curta      # ou feat/, docs/, refactor/, test/
   ```
2. Faça a mudança com testes (ver abaixo).
3. Abra um pull request para a `main`, preenchendo o modelo.
4. O PR só entra com o CI verde e depois da revisão. A `main` nunca recebe commit direto.

Um branch por assunto: um PR pequeno é revisado mais rápido e mais bem.

## Padrão de commits

Use o formato [Conventional Commits](https://www.conventionalcommits.org/pt-br/v1.0.0/), com a descrição em português:

```text
<tipo>: <o que muda, no imperativo ou descritivo, em minúsculas>

<corpo opcional: por que a mudança é necessária e o que ela afeta>
```

Tipos usados no projeto: `feat` (funcionalidade), `fix` (correção), `refactor` (reorganização sem mudar comportamento), `test`, `docs`, `chore` (manutenção). Exemplos reais do histórico:

```text
fix: OMAKER_ENTITIES inválido só falha ao gerar a ontologia
feat: Gerar e Atualizar rodam em segundo plano, com botão Cancelar
refactor: mover core/ e ui/ para o pacote omaker/
```

## Código

- **Python 3.12**, formatado e verificado com `ruff` (`uv run ruff check .`).
- **Comportamento novo ou corrigido vem com teste.** Escreva o teste primeiro, veja-o falhar e depois implemente.
- **Testes que baixam modelos** levam o marcador `@pytest.mark.slow`; os que precisam do Ollama real, `@pytest.mark.ollama`. A suíte rápida (`-m "not slow and not ollama"`) precisa rodar em segundos, sem rede.
- **Testes com janelas** usam `qtbot.addWidget(...)` e nunca leem nem gravam as configurações reais do usuário (o `conftest.py` já isola o `QSettings`).
- **Rótulos e tipos** (relações, tipos de entidade, classes-base) vivem só em `omaker/domain/labels.py`. Mudar `REL2ID` invalida os checkpoints treinados.
- **Mensagens ao usuário** nunca afirmam o que não aconteceu (por exemplo, "validado" quando o HermiT não rodou).
- **Arquivos de dados novos** dentro de `omaker/` (JSON, OWL) precisam entrar na lista `datas` do `OMAKER.spec`; um teste confere isso.
- **Um dataset novo** entra por um leitor que devolva `list[RelationExample]` (`omaker/relations/data.py`); o treino e a avaliação não precisam mudar.

## Antes de abrir o pull request

```bash
uv run ruff check .
uv run pytest -q -m "not slow and not ollama"
```

As duas coisas precisam passar. Se a mudança mexe na interface, descreva no PR como você testou à mão. Se mexe no treino ou na avaliação, diga qual comando rodou e o que saiu.

## Documentação

- O README descreve o uso; atualize-o quando um comando, uma variável de ambiente ou um requisito mudar.
- Docstrings e comentários explicam o porquê, não o óbvio.

## Dúvidas

Abra uma issue com a sua pergunta.
