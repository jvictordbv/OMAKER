# 1. Introdução e objetivos

O OMAKER (Ontology Mapping & Knowledge Engineering Resource) é um aplicativo de desktop para Windows que transforma texto biomédico em inglês numa ontologia OWL conferida por um raciocinador lógico. Ele combina um reconhecedor de entidades (NER) biomédico, um LLM local servido pelo Ollama e um classificador de relações treinável (PURE, sobre o SpanBERT). A ontologia gerada pode ser aberta no Protégé.

Esta documentação descreve a versão 0.3.0 (`pyproject.toml`, `omaker/__init__.py`), integrada na `main` no commit `c2358cc`.

## 1.1 Requisitos principais

O sistema é organizado em onze capacidades. O detalhe de cada uma, com cenários verificáveis e rastreabilidade até os testes, está na [especificação de requisitos](../requisitos/README.md).

| Capacidade | Código | Em resumo | Especificação |
|---|---|---|---|
| Extração de entidades | ENT | Encontra fármacos, sintomas e doenças no texto pelo NER, pelo LLM ou pelos dois (`OMAKER_ENTITIES`). Toda menção proposta pelo LLM precisa existir no texto. | [extracao-de-entidades](../requisitos/especificacoes/extracao-de-entidades/spec.md) |
| Extração de relações | REL | Forma pares de entidades da mesma frase e classifica cada par em `treats`, `causes`, `prevents` ou `no_relation` com o PURE; sem checkpoint, com o LLM. | [extracao-de-relacoes](../requisitos/especificacoes/extracao-de-relacoes/spec.md) |
| Geração de ontologia | ONT | Monta classes, indivíduos, propriedades e disjunções com o owlready2, roda o HermiT e grava RDF/XML com IRI absoluto. | [geracao-de-ontologia](../requisitos/especificacoes/geracao-de-ontologia/spec.md) |
| Atualização de ontologia | ATU | Acrescenta evidências a um `.owl` existente; numa ontologia externa, reaproveita as classes pelo rótulo e pelo sinônimo exato. | [atualizacao-de-ontologia](../requisitos/especificacoes/atualizacao-de-ontologia/spec.md) |
| Sinônimos | SIN | Agrupa termos com Sentence-BERT e grava `owl:equivalentClass` numa cópia da ontologia, depois da confirmação do usuário. | [sinonimos](../requisitos/especificacoes/sinonimos/spec.md) |
| Integração com LLM | LLM | Cliente do Ollama com saída em esquema JSON, novas tentativas, teto de tokens e conferência do nome exato do modelo. | [integracao-com-llm](../requisitos/especificacoes/integracao-com-llm/spec.md) |
| Modelo de relações | MOD | Treino por configuração com retomada, calibração da confiança, publicação e download do checkpoint. | [modelo-de-relacoes](../requisitos/especificacoes/modelo-de-relacoes/spec.md) |
| Avaliação | AVA | Métricas com intervalo de confiança, avaliação de ponta a ponta com retomada e medida do NER. | [avaliacao](../requisitos/especificacoes/avaliacao/spec.md) |
| Interface | INT | Sete páginas, execução em segundo plano com cancelamento, aviso de idioma e mensagens que não afirmam validação inexistente. | [interface](../requisitos/especificacoes/interface/spec.md) |
| Distribuição | DIS | Execução a partir do código-fonte com uv e `.exe` leve montado e conferido no CI. | [distribuicao](../requisitos/especificacoes/distribuicao/spec.md) |
| Configuração | CFG | Variáveis de ambiente lidas na hora do uso e preferências da interface no QSettings. | [configuracao](../requisitos/especificacoes/configuracao/spec.md) |

## 1.2 Objetivos de qualidade

Os cinco objetivos abaixo orientam as escolhas de arquitetura, em ordem de prioridade. Os cenários que os tornam mensuráveis estão na [seção 10](10-requisitos-de-qualidade.md).

| Prioridade | Objetivo | Por que importa | Como é atingido |
|---|---|---|---|
| 1 | **Resultados corretos e honestos** | A ontologia é conhecimento formal: um axioma inventado ou uma "validação" que não ocorreu contamina tudo o que vier depois. A revisão de 2026-11-09 achou a interface anunciando sucesso falso. | O LLM só propõe; o código confere no texto e valida a taxonomia (`omaker/llm/entities.py`, `omaker/llm/taxonomy.py`). A mensagem final depende do estado real do raciocinador (`omaker/ui/messages.py`). |
| 2 | **Privacidade** | Textos clínicos e de pesquisa não devem sair da máquina do usuário. | LLM local pelo Ollama (`omaker/llm/client.py`); os modelos rodam no próprio computador; a rede só é usada para baixar modelos. |
| 3 | **Reprodutibilidade científica** | Os números da dissertação precisam poder ser refeitos por outra pessoa. | Sementes fixas, divisão gravada com manifesto, teste avaliado uma vez, LLM com temperatura 0 e semente fixa na avaliação, metadados em cada execução (`omaker/relations/train.py`, `omaker/evaluation/e2e.py`). |
| 4 | **Robustez em tarefas longas** | Treino, avaliação e download levam de minutos a horas; uma queda não pode jogar o trabalho fora. | Pontos de retomada atômicos no treino, na avaliação e no download; quedas controladas quando um serviço externo falta ([seção 8](08-conceitos-transversais.md)). |
| 5 | **Instalação simples no Windows** | Avaliadores e outros pesquisadores não devem precisar instalar Python. | `.exe` leve que baixa os modelos na primeira execução, caminhos independentes da pasta corrente e localização automática do Java (`omaker/paths.py`, `omaker/ontology/java.py`). |

## 1.3 Partes interessadas

| Papel | Quem | O que espera da arquitetura |
|---|---|---|
| Autor e dono do repositório | João Victor Ferreira Barbosa (UFPE, mestrado), conta `jvictordbv` | Um sistema que sustente a dissertação. Decide escopo, dados, modelos, licença e versões. |
| Coautor do software | Gustavo Souto Silva de Barros Santos (UPE) | Código testável e organizado, CI confiável, decisões registradas. |
| Orientação acadêmica | Orientadores citados na página Sobre (`omaker/ui/pages/about.py`) | Validade científica da avaliação; podem mudar o rumo do dataset. |
| Banca e leitores da dissertação | Avaliadores do trabalho | Números reproduzíveis, limitações declaradas, comparação justa com baselines. |
| Usuários | Pesquisadores e engenheiros de ontologias | Instalar sem Python, gerar uma ontologia a partir de um texto e abri-la no Protégé. |
| Contribuidores | Quem abrir um pull request | Guia de contribuição (`CONTRIBUTING.md`), suíte rápida sem rede e CI verde como regra de entrada. |
