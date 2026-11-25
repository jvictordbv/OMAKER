# Arquitetura do OMAKER

Documentação de arquitetura da versão 0.3.0. Ela descreve como o sistema é construído, por que foi construído assim e o que ainda preocupa. Os diagramas ficam no próprio texto e são renderizados pelo GitHub. Requisitos estão em [../requisitos/](../requisitos/README.md) e as decisões detalhadas, em [../decisoes/](../decisoes/README.md).

| Seção | Conteúdo |
|---|---|
| [1. Introdução e objetivos](01-introducao-e-objetivos.md) | Requisitos principais em resumo, os cinco objetivos de qualidade e as partes interessadas. |
| [2. Restrições](02-restricoes.md) | Restrições técnicas (Python 3.12, Windows, PySide6, Ollama, Java, GPU, tamanho dos modelos), organizacionais e convenções. |
| [3. Contexto e escopo](03-contexto-e-escopo.md) | Diagrama de contexto, interfaces externas com formato e código, o que fica dentro e fora do escopo. |
| [4. Estratégia de solução](04-estrategia-de-solucao.md) | As escolhas centrais, o motivo de cada uma e o registro de decisão correspondente. |
| [5. Visão de blocos](05-visao-de-blocos.md) | Diagrama de contêineres, dependências entre pacotes e diagramas de componentes de cada pacote. |
| [6. Visão de execução](06-visao-de-execucao.md) | Diagramas de sequência: gerar, atualizar, primeiro uso com download, treino e calibração, avaliação com retomada. |
| [7. Visão de implantação](07-visao-de-implantacao.md) | Código-fonte com uv e `.exe` leve, onde ficam os arquivos, pipeline de CI. |
| [8. Conceitos transversais](08-conceitos-transversais.md) | Configuração, caminhos, retomada, reprodutibilidade, erros, logs, idioma, verificação do LLM, segurança e testes. |
| [9. Decisões](09-decisoes.md) | Resumo de todos os registros de decisão, com status. |
| [10. Requisitos de qualidade](10-requisitos-de-qualidade.md) | Árvore de qualidade e cenários com estímulo, resposta e medida. |
| [11. Riscos e débito técnico](11-riscos-e-debito-tecnico.md) | Riscos com probabilidade, impacto e mitigação; débito técnico conhecido. |
| [12. Glossário](12-glossario.md) | Termos do domínio e termos técnicos. |

## Convenções desta documentação

- Toda afirmação técnica cita o arquivo ou o teste que a sustenta, no formato `omaker/pipeline/engine.py` ou `tests/test_e2e.py::nome_do_teste`.
- O que não está implementado aparece marcado como "Proposto".
- Os números de experimentos vêm de execuções registradas em `runs/` e nas notas do projeto; os principais estão repetidos onde são usados.
- Ao mudar o comportamento descrito numa seção, atualize a seção no mesmo pull request.
