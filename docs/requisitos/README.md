# Especificação de requisitos do OMAKER

Este documento descreve o que o OMAKER 0.3.0 faz, para quem e com que garantias. Ele descreve o sistema como ele é hoje: cada requisito aponta o código que o implementa e o teste que o verifica. O que existe só como proposta aparece marcado como "Proposto".

## Sumário

- [Visão do produto](#visão-do-produto)
- [Partes interessadas](#partes-interessadas)
- [Escopo](#escopo)
- [Premissas e dependências externas](#premissas-e-dependências-externas)
- [Convenções desta especificação](#convenções-desta-especificação)
- [Capacidades](#capacidades)
- [Outros documentos](#outros-documentos)

## Visão do produto

### Problema

Construir uma ontologia formal (OWL, Lógica de Descrição) a partir de texto livre exige muito trabalho manual de um engenheiro do conhecimento. É o gargalo de aquisição de conhecimento da Web Semântica. No domínio biomédico, o texto está em artigos e diretrizes clínicas, e quem precisa da ontologia nem sempre pode enviar esse texto a um serviço externo.

### Solução

O OMAKER é um aplicativo de desktop que transforma um texto biomédico em inglês numa ontologia OWL:

1. reconhece as entidades (fármacos, sintomas, doenças) com um NER biomédico e com um LLM local, e só aceita do LLM o que está escrito no texto;
2. forma pares de entidades na mesma frase;
3. classifica a relação de cada par (`treats`, `causes`, `prevents`) com um classificador treinado (PURE, SpanBERT com marcadores tipados), ou com o LLM quando não há classificador;
4. pede ao LLM uma taxonomia (subclasses, tipagem das instâncias, disjunções) e valida a resposta;
5. monta a ontologia com o owlready2 e confere a consistência com o raciocinador HermiT;
6. abre o resultado no Protégé.

O OMAKER também atualiza ontologias existentes, alinhando as entidades à hierarquia delas (por exemplo, a Symptom Ontology), e agrupa sinônimos com Sentence-BERT. O texto do usuário não sai da máquina: o LLM roda no Ollama local.

### Para quem

- Pesquisadores e engenheiros do conhecimento que precisam de um primeiro rascunho de ontologia biomédica a partir de texto, para revisar no Protégé.
- O autor do projeto de mestrado, que precisa treinar, calibrar e avaliar o pipeline de forma reproduzível.

## Partes interessadas

| Parte interessada | Interesse principal | Capacidades mais relevantes |
|---|---|---|
| Pesquisador e autor do projeto (João Victor Ferreira Barbosa, UFPE) | Resultados reproduzíveis e defensáveis na dissertação; controle das decisões de modelo e de dados | [MOD](especificacoes/modelo-de-relacoes/spec.md), [AVA](especificacoes/avaliacao/spec.md), [REL](especificacoes/extracao-de-relacoes/spec.md) |
| Orientador | Rigor metodológico: divisão fixa dos dados, teste avaliado uma vez, intervalo de confiança, comparação com baselines | [AVA](especificacoes/avaliacao/spec.md), [MOD](especificacoes/modelo-de-relacoes/spec.md), [requisitos não funcionais](nao-funcionais.md) |
| Usuário que gera ontologias | Interface que não trava, mensagens que não prometem o que não aconteceu, privacidade do texto, instalação simples | [INT](especificacoes/interface/spec.md), [ONT](especificacoes/geracao-de-ontologia/spec.md), [ATU](especificacoes/atualizacao-de-ontologia/spec.md), [SIN](especificacoes/sinonimos/spec.md), [DIS](especificacoes/distribuicao/spec.md) |
| Mantenedor (coautor do software, Gustavo Souto Silva de Barros Santos, UPE, e contribuidores) | Código testado, CI verde, empacotamento conferido automaticamente, configuração em um só lugar | [DIS](especificacoes/distribuicao/spec.md), [CFG](especificacoes/configuracao/spec.md), [requisitos não funcionais](nao-funcionais.md) |

## Escopo

### Dentro do escopo

- Texto biomédico em inglês, colado na interface.
- Entidades dos tipos `DRUG`, `SYMPTOM` e `DISEASE`.
- Relações `treats`, `causes` e `prevents` entre entidades da mesma frase.
- Geração de uma ontologia OWL nova e atualização de uma ontologia existente, inclusive externa (Symptom Ontology).
- Detecção de sinônimos e gravação de `owl:equivalentClass` numa cópia da ontologia.
- Treino, calibração, publicação e download do classificador de relações.
- Avaliação de ponta a ponta contra um gabarito pequeno e contra o teste oficial do BioRED, e medição do NER.
- Executável para Windows, com os modelos baixados na primeira execução.

### Fora do escopo

- Textos em outros idiomas: a interface avisa e pergunta antes de processar, mas o pipeline só foi feito para inglês ([INT-08](especificacoes/interface/spec.md)).
- Entidades do tipo `GENE`: a classe-base `Gene` e os marcadores existem (`omaker/domain/labels.py`), mas nenhum extrator produz esse tipo.
- Relações entre frases diferentes e relações além das três citadas.
- LLM em serviço de nuvem ou com chave de API.
- Uso como serviço de rede ou por vários usuários ao mesmo tempo.
- Edição manual da ontologia: ela é feita no Protégé.
- Executável para Linux ou macOS: o código usa caminhos independentes do sistema, mas só o Windows é montado e testado no CI.
- Troca do NER pelo modelo treinado no BC5CDR: **Proposto** ([registro de decisão 0014](../decisoes/0014-troca-do-ner-bc5cdr.md)).
- Ícone do executável: pendente (`OMAKER.spec`, `icon=None`).

## Premissas e dependências externas

### Premissas

- O texto de entrada está em inglês e trata de fármacos, sintomas e doenças.
- A máquina do usuário tem memória para o Ollama com o modelo escolhido. Na avaliação de ponta a ponta, o Ollama com o `qwen3` ocupou cerca de 9,6 GB (nota `06-experimentos/2026-11-12-pure-biored.md`).
- O usuário revisa a ontologia gerada antes de usá-la: o OMAKER produz um rascunho, não uma ontologia curada.

### Dependências externas

| Dependência | Para quê | Quando é necessária | O que acontece sem ela |
|---|---|---|---|
| Ollama, com o modelo configurado (padrão `qwen3:8b`) | Entidades, taxonomia e, sem classificador, relações | Em toda geração e atualização: o motor confere o Ollama e o modelo antes de começar | A operação para com uma mensagem que diz como instalar o modelo ([LLM-02](especificacoes/integracao-com-llm/spec.md)) |
| Java 11 ou mais novo | Raciocinador HermiT | Ao final de cada geração ou atualização | A ontologia é salva e marcada como "gerada sem validação" ([ONT-12](especificacoes/geracao-de-ontologia/spec.md)) |
| Internet na primeira execução | Modelos do Hugging Face (SpanBERT, cerca de 410 MB; NER, cerca de 250 MB; Sentence-BERT) e o classificador publicado na Release `pure-biored-v1` (438 MB) | Na primeira vez que cada modelo é usado | Sem o classificador, as relações são classificadas pelo LLM ([REL-07](especificacoes/extracao-de-relacoes/spec.md)); sem os modelos do Hugging Face em cache, o NER e o Sentence-BERT não carregam |
| Protégé (opcional) | Abrir a ontologia gerada; o JRE que vem com ele serve ao HermiT | Ao clicar em "Abrir no Protégé" | O botão mostra um aviso ([INT-11](especificacoes/interface/spec.md)) |
| BioRED (servidor do NCBI) | Treino do classificador e gabarito de avaliação | Só nos comandos de treino e avaliação | O comando diz como baixar ([MOD-14](especificacoes/modelo-de-relacoes/spec.md)) |
| uv e Python 3.12 | Rodar a partir do código-fonte | Fora do executável | Não se aplica ao executável |

## Convenções desta especificação

### Palavras normativas

- **DEVE**: obrigatório. O sistema atual cumpre, e um teste ou uma inspeção mostra isso.
- **NÃO DEVE**: proibido.
- **PODE**: permitido, mas não obrigatório.

### Formato de um requisito

```text
### Requisito: <nome curto> (<CÓDIGO>)
O sistema DEVE ... (uma ou duas frases normativas)
Fonte: <arquivo do código> ; Verificado por: <arquivo do teste>::<nome do teste>
#### Cenário: <nome>
- DADO <contexto>
- QUANDO <ação>
- ENTÃO <resultado esperado>
- E <resultado adicional, se houver>
```

- Cada requisito tem ao menos um cenário.
- "Verificado por" cita testes da pasta `tests/`. Os testes marcados `slow` baixam modelos e não rodam no CI; isso vem indicado ao lado do nome. Quando não há teste, a linha diz "sem teste automatizado" e o requisito aparece na seção correspondente de [rastreabilidade](rastreabilidade.md).
- Mensagens entre aspas são as do código, no idioma em que aparecem (o log do motor está em inglês; as caixas de diálogo, em português).

### Códigos

- Cada capacidade tem um prefixo de três letras (tabela abaixo). Os requisitos são numerados em sequência: `ENT-01`, `ENT-02` e assim por diante.
- Os requisitos não funcionais usam `RNF-01`, `RNF-02` e assim por diante, em [nao-funcionais.md](nao-funcionais.md).
- Um código nunca é reaproveitado. Um requisito retirado fica marcado como "Retirado", com o motivo.

## Capacidades

| Código | Capacidade | O que cobre |
|---|---|---|
| ENT | [Extração de entidades](especificacoes/extracao-de-entidades/spec.md) | NER biomédico, proposta e confirmação pelo LLM, união das fontes |
| REL | [Extração de relações](especificacoes/extracao-de-relacoes/spec.md) | Frases, pares candidatos, classificador PURE, limite de confiança, classificação pelo LLM, filtro de domínio |
| ONT | [Geração de ontologia](especificacoes/geracao-de-ontologia/spec.md) | Taxonomia validada, montagem do OWL, IRI, HermiT, Java, Protégé |
| ATU | [Atualização de ontologia](especificacoes/atualizacao-de-ontologia/spec.md) | Mescla com ontologias existentes, alinhamento à hierarquia externa, idempotência |
| SIN | [Sinônimos](especificacoes/sinonimos/spec.md) | Agrupamento com Sentence-BERT, gravação de equivalências numa cópia |
| LLM | [Integração com LLM](especificacoes/integracao-com-llm/spec.md) | Cliente do Ollama, nome exato do modelo, saída estruturada, limite de tokens, queda para o NER |
| MOD | [Modelo de relações](especificacoes/modelo-de-relacoes/spec.md) | Dados, treino reproduzível e retomável, calibração, publicação, download |
| AVA | [Avaliação](especificacoes/avaliacao/spec.md) | Métricas, ponta a ponta com baselines, gabarito BioRED, retomada, medição do NER |
| INT | [Interface](especificacoes/interface/spec.md) | Páginas, execução em segundo plano, Cancelar, fechamento seguro, aviso de idioma, mensagens honestas |
| DIS | [Distribuição](especificacoes/distribuicao/spec.md) | Executável leve, verificação do executável, licença, caminhos, versão |
| CFG | [Configuração](especificacoes/configuracao/spec.md) | Variáveis de ambiente e preferências da interface |

## Outros documentos

- [Requisitos não funcionais](nao-funcionais.md): privacidade, reprodutibilidade, portabilidade, robustez, desempenho e recursos, manutenibilidade, segurança, licenciamento e idioma.
- [Rastreabilidade](rastreabilidade.md): requisito, módulos e testes, e a lista dos requisitos sem teste automatizado.
- [Documentação de arquitetura](../arquitetura/README.md) e [registros de decisão](../decisoes/README.md): o como e o porquê.
- [README do repositório](../../README.md): instalação, uso, treino e avaliação.
