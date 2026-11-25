# Documentação do OMAKER

Documentação técnica da versão 0.3.0. Ela descreve o sistema como ele é hoje; o que ainda não foi implementado aparece marcado como "Proposto".

## Como ler

| Se você quer... | Comece por |
|---|---|
| Saber o que o sistema faz e com que garantias | Requisitos (em preparação) |
| Entender como ele é construído e por quê | Arquitetura (em preparação) |
| Saber por que uma escolha foi feita e o que ela custou | [Registros de decisão](decisoes/README.md) |
| Instalar, usar, treinar ou avaliar | [README do repositório](../README.md) |
| Contribuir com código | [CONTRIBUTING](../CONTRIBUTING.md) |

## Partes

### Requisitos

O que o sistema DEVE fazer, organizado por capacidade. Cada requisito tem um código (por exemplo `REL-03`), cenários verificáveis no formato DADO, QUANDO, ENTÃO, e aponta o código e o teste que o cobrem. Os requisitos não funcionais (privacidade, reprodutibilidade, portabilidade, robustez) ficam num arquivo próprio, e a tabela de rastreabilidade liga cada requisito ao código e aos testes.

### Arquitetura

Doze seções, da introdução ao glossário: objetivos e restrições, contexto do sistema com os serviços externos, estratégia de solução, decomposição em blocos, cenários de execução, implantação (código-fonte e executável), conceitos transversais, decisões, requisitos de qualidade, riscos e débito técnico. Os diagramas ficam no próprio texto e são renderizados pelo GitHub.

### Registros de decisão

Uma página por decisão de projeto relevante: contexto, decisão, alternativas consideradas e consequências, positivas e negativas. As decisões são numeradas e nunca reescritas; quando uma muda, um novo registro substitui o anterior.

## Manutenção

- Ao mudar um comportamento, atualize o requisito correspondente e a tabela de rastreabilidade no mesmo PR.
- Ao tomar uma decisão que afeta a arquitetura, a distribuição, a licença ou os dados, crie um registro de decisão novo.
- Números de experimentos (F1, calibração, tamanhos) citados aqui devem vir de uma execução registrada em `runs/` ou de um comando do repositório.
