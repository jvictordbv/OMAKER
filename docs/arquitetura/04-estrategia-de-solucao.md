# 4. Estratégia de solução

A ideia central do OMAKER é dividir o trabalho entre componentes que fazem bem uma coisa e conferir o que vem do componente menos confiável. Modelos especializados extraem (NER para entidades, PURE para relações, com uma confiança calibrada). O LLM ajuda onde o texto livre exige flexibilidade (mais entidades, a taxonomia), mas tudo o que ele devolve é verificado pelo código antes de entrar na ontologia. No fim, um raciocinador lógico confere o resultado, e a interface relata exatamente o que ele disse.

## 4.1 Escolhas centrais

| Escolha | Por quê | Registro |
|---|---|---|
| **Pipeline só em inglês**, com aviso na interface | Todos os modelos, dados e prompts são em inglês; traduzir introduziria erros e invalidaria a avaliação. | [0001](../decisoes/0001-pipeline-em-ingles.md) |
| **LLM local pelo Ollama**, atrás de um protocolo (`LLMClient`) | O texto não sai da máquina, não há chave de API nem custo por uso. O protocolo permite trocar de provedor sem mudar o motor (`tests/test_llm_protocol.py::test_engine_runs_with_any_llm_client`). | [0002](../decisoes/0002-llm-local-ollama.md) |
| **Entidades pelo NER e pelo LLM**, com verificação no texto | O NER sozinho erra muito em resumos científicos (F1 0,409); o LLM acha mais, mas pode inventar. Cada proposta do LLM só entra se for achada no texto como palavra inteira. Na sobreposição, vence o trecho mais longo. | [0003](../decisoes/0003-entidades-ner-e-llm.md) |
| **Classificador PURE com marcadores tipados** sobre o SpanBERT | Um modelo treinável, com confiança por par e uma só função de codificação (`_encode`) para treino, avaliação e inferência, o que impede que as três divirjam. | [0004](../decisoes/0004-classificador-pure-marcadores-tipados.md) |
| **BioRED como dados de treino** | Dados públicos em quantidade, com divisão oficial. O conjunto anterior, de 31 frases, dava um intervalo de confiança de 0 a 1. | [0005](../decisoes/0005-biored-como-dados-de-treino.md) |
| **Avaliação com o teste oficial do BioRED** | 100 resumos que nunca entram no treino, com um protocolo de casamento por conceito (`omaker/evaluation/biored_gold.py`). | [0006](../decisoes/0006-avaliacao-com-teste-do-biored.md) |
| **Calibração por temperatura** e limite escolhido na validação | A confiança crua era otimista demais (ECE 0,271); com T = 4,33 cai para 0,055, e o limite de 0,35 vem da validação, não de um valor fixo. | [0007](../decisoes/0007-calibracao-por-temperatura.md) |
| **Executável leve com download dos modelos** | Um `.exe` completo passaria de 2 GB; o leve tem 296 MB no `.zip`, e um checkpoint novo não exige um `.exe` novo. | [0008](../decisoes/0008-executavel-leve-com-download.md) |
| **Checkpoint publicado sem o texto de treino** | As frases vêm de resumos do PubMed; o checkpoint guarda só os hashes delas, que bastam para a verificação de contaminação. | [0009](../decisoes/0009-checkpoint-publicado-sem-texto.md) |
| **Licença AGPL-3.0-only** | Mantém o código aberto, inclusive em uso como serviço, e é compatível com as dependências Apache-2.0. | [0010](../decisoes/0010-licenca-agpl.md) |
| **Só a `main`, branches curtos e CI obrigatório** | Equipe de duas pessoas, sem ambiente de homologação; a `main` sempre funciona e as versões saem por tag. | [0011](../decisoes/0011-fluxo-de-branches-e-ci.md) |
| **Atualização alinhada à hierarquia existente** | Numa ontologia externa, criar `Symptom` ao lado do `symptom` dela duplicaria a hierarquia. O OMAKER reaproveita as classes pelo rótulo e pelo sinônimo exato, e cria o que falta no próprio namespace. | [0012](../decisoes/0012-atualizacao-alinhada-a-hierarquia.md) |
| **Teto de tokens na resposta do LLM** | Com temperatura 0 e semente fixa, um modelo em laço repete o laço sempre; o teto de 4096 tokens transforma a espera de 600 s num erro imediato. | [0013](../decisoes/0013-limite-de-tokens-do-llm.md) |
| **Trocar o NER por um modelo treinado no BC5CDR** (Proposto) | Dobraria o F1 do NER (0,409 para 0,810), mas o BC5CDR não separa sintoma de doença. Aguarda a decisão do João. | [0014](../decisoes/0014-troca-do-ner-bc5cdr.md) |

## 4.2 Decomposição e tecnologia

- **Motor sem interface.** `HybridEngine` (`omaker/pipeline/engine.py`) é um conjunto de métodos estáticos que recebem um `log_callback`. Ele não importa Qt, então o mesmo código serve à interface, à avaliação de ponta a ponta e aos testes.
- **Interface fina.** As páginas só coletam a entrada, rodam o motor numa `QThread` (`PipelineWorker` em `omaker/ui/workers.py`) e mostram o resultado. Nenhum widget é tocado fora da thread da interface.
- **Montagem idempotente.** `populate` (`omaker/ontology/builder.py`) reaproveita o que já existe, então a mesma função gera uma ontologia nova e atualiza uma existente.
- **Constantes num lugar só.** Tipos, rótulos, marcadores e classes-base vivem em `omaker/domain/labels.py`, compartilhados pelo treino, pela inferência e pela exportação OWL.
- **Importações pesadas tardias.** `torch`, `transformers` e `sentence-transformers` são importados dentro das funções que os usam (`SynonymWorker.run` em `omaker/ui/workers.py`; `HybridEngine.extrair` e `_relations_pure` em `omaker/pipeline/engine.py`), para a janela abrir rápido. O `owlready2` é exceção: o motor o importa ao carregar `ReasonerStatus` ([seção 11](11-riscos-e-debito-tecnico.md)).

## 4.3 Como a estratégia atende aos objetivos de qualidade

| Objetivo ([seção 1.2](01-introducao-e-objetivos.md#12-objetivos-de-qualidade)) | Abordagem |
|---|---|
| Resultados corretos e honestos | Verificação das entidades do LLM no texto; validação da taxonomia; filtro de domínio das relações; HermiT; `ReasonerStatus` com três estados e mensagem correspondente. |
| Privacidade | Ollama local (o texto vai só para `OLLAMA_HOST`, que por padrão é a própria máquina); modelos locais; a rede externa só é usada para baixar modelos; checkpoint publicado sem texto. |
| Reprodutibilidade científica | Treino por arquivo TOML, sementes, divisão gravada, teste avaliado uma vez, IC por bootstrap, LLM com temperatura 0 e semente na avaliação, metadados e hashes em cada execução. |
| Robustez em tarefas longas | Retomada atômica no treino, na avaliação e no download; quedas controladas (LLM no lugar do PURE, NER sem o LLM, ontologia sem validação quando falta o Java). |
| Instalação simples no Windows | `.exe` leve conferido no CI por `--self-check`; `paths.py` independe da pasta corrente; `find_java` procura o Java em sete lugares (variável `OMAKER_JAVA`, `JAVA_HOME`, `PATH`, três pastas de `C:\Program Files` e o JRE do Protégé). |
