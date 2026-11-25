# 0011. Só a main, branches curtos, CI e tags de versão

- **Status:** Aceita
- **Data:** 2026-11-09
- **Decidido por:** Gustavo; seguido desde então pelos dois autores (o João integrou o PR #12 pelo mesmo fluxo)

## Contexto

O OMAKER é um programa de desktop, sem servidor nem ambiente de implantação, mantido por duas pessoas. Em 2026-11-09, o repositório tinha só a `main`, nenhuma tag, nenhum teste automatizado e nenhum CI. O Gustavo, colaborador com permissão de escrita, ia começar uma reestruturação grande, em várias fases, no repositório do João.

## Decisão

- A `main` fica sempre funcionando e só recebe mudanças por pull request, com o CI aprovado. Ela nunca recebe commit direto.
- Cada mudança tem um branch curto (`feat/<assunto>`, `fix/<assunto>`, `docs/<assunto>`), que deveria ser apagado depois do merge.
- O CI (`.github/workflows/ci.yml`) roda em todo push e pull request, no Windows: `ruff check .` e a suíte rápida (`pytest -m "not slow and not ollama"`).
- As versões saem por tag `v*`; numa tag, o workflow `exe.yml` monta o `.exe` e o anexa à Release. Uma versão candidata (`vX.Y.Z-rc1`) faz o papel de homologação, testada pelo João na máquina dele.
- As contribuições entram por pull request direto no repositório do João, não por fork.
- As actions dos workflows ficam fixadas pelo SHA do commit, e só o job que publica a Release tem permissão de escrita.

## Alternativas consideradas

- **Branches `develop`, `homolog` e `main`.** Pressupõe um ambiente de homologação que não existe; cada correção passaria por três merges, e os branches tendem a se afastar. Volta a fazer sentido se surgirem usuários externos que precisem de uma versão estável enquanto o desenvolvimento continua.
- **Fork do Gustavo com PRs para o repositório do João.** Desnecessário com a permissão de escrita, e afasta o histórico de quem é dono do projeto.

## Consequências

### Positivas

- 23 pull requests integrados entre 2026-11-12 e 2026-11-24, todos com o CI verde, e a suíte cresceu de 51 para 226 testes.
- A versão 0.3.0 saiu por tag, com o `.exe` montado e anexado pelo CI.

### Negativas e riscos

- Com duas pessoas, a revisão por outra pessoa não é garantida. Dos 23 PRs integrados, 22 foram integrados pelo próprio autor, o Gustavo; só o #12 teve aprovação formal do João. O `CONTRIBUTING.md` diz que o PR entra "depois da revisão", o que na prática não acontece.
- A proteção da `main` depende de uma configuração do GitHub que só o dono do repositório liga; ela não está registrada no repositório.
- Os branches integrados não foram apagados no repositório remoto: na data deste registro, onze continuavam lá.
- A versão 0.3.0 saiu direto, sem versão candidata.
- O CI não roda os testes lentos (modelos reais) nem os que precisam do Ollama.

## Referências

- `.github/workflows/ci.yml`, `.github/workflows/exe.yml`, `CONTRIBUTING.md`.
- [PR #1](https://github.com/jvictordbv/OMAKER/pull/1) (testes, lint e CI), [PR #12](https://github.com/jvictordbv/OMAKER/pull/12) (integrado pelo João), [PR #21](https://github.com/jvictordbv/OMAKER/pull/21) (actions fixadas pelo SHA), [PR #23](https://github.com/jvictordbv/OMAKER/pull/23) (versão 0.3.0).
- Notas internas do projeto: registro do fluxo de branches (2026-11-09) e plano de reestruturação (decisão D4, sobre o fluxo de contribuição).
