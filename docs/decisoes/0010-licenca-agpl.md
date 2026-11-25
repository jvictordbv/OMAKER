# 0010. Licença AGPL-3.0-only

- **Status:** Aceita
- **Data:** 2026-11-24
- **Decidido por:** João Victor

## Contexto

Até a versão 0.2.0, o repositório não tinha licença declarada; sem licença, o código fica, por padrão, com todos os direitos reservados aos autores, e ninguém sabe o que pode fazer com ele. O João queria uma licença que mantivesse o projeto aberto e propôs a GPL, achando que ela impedia o uso comercial por terceiros. Não impede: a GPL só obriga quem distribuir uma versão modificada a abrir o código, e não cobre o uso do programa como serviço na rede.

Duas restrições pesam na escolha: a licença precisa ser compatível com as dependências (em especial o `transformers`, sob Apache-2.0), e os autores querem poder negociar outros termos com quem quiser usar o código num produto fechado.

## Decisão

- O OMAKER é distribuído sob a GNU Affero General Public License v3.0, com o identificador SPDX `AGPL-3.0-only`.
- O texto oficial está em `LICENSE`; o identificador está em `pyproject.toml` e em `CITATION.cff`; o README tem um resumo e o contato para outros termos.
- O `LICENSE` vai junto do `.exe`, porque a licença exige o texto junto do programa distribuído.

## Alternativas consideradas

- **GPL-3.0.** Mantém o código aberto, mas não cobre o uso como serviço web, que a AGPL cobre.
- **GPL-2.0.** Incompatível com a Apache-2.0 do `transformers`.
- **AGPL-3.0-or-later.** Ficou `-only`, que dá mais controle aos autores: versões futuras da AGPL não se aplicam sozinhas. Trocar é só mudar o identificador.
- **Licença permissiva (MIT, Apache-2.0).** Não atenderia ao objetivo declarado de manter as versões derivadas abertas.

## Consequências

### Positivas

- Quem modificar e distribuir o programa, ou oferecê-lo como serviço, precisa publicar o código sob a mesma licença.
- Uso sob outros termos passa por negociação com os autores, o que abre espaço para uma licença comercial à parte.
- As dependências são compatíveis: PySide6, HermiT e owlready2 (LGPL), `transformers` (Apache-2.0), torch, numpy e scikit-learn (BSD).

### Negativas e riscos

- A AGPL afasta empresas que evitam licenças com obrigação de rede, o que pode reduzir o uso e as contribuições.
- A licença comercial à parte só funciona se os autores detiverem os direitos de todo o código. Com contribuições externas, será preciso um termo de cessão no `CONTRIBUTING.md`, que ainda não existe.
- Os modelos baixados na primeira execução têm licenças próprias (Apache-2.0 e MIT hoje), e o checkpoint do PURE é derivado do BioRED, cuja licença não é declarada ([0009](0009-checkpoint-publicado-sem-texto.md)). A AGPL cobre o código, não esses modelos.

## Referências

- `LICENSE`, `pyproject.toml`, `CITATION.cff`, `README.md` (seção "Licença"), `OMAKER.spec`.
- Teste: `tests/test_packaging.py::test_license_ships_with_the_executable`.
- [PR #19](https://github.com/jvictordbv/OMAKER/pull/19): licença AGPL-3.0.
- Notas internas do projeto: registro da escolha da licença (2026-11-24).
