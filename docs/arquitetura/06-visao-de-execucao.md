# 6. Visão de execução

Cinco cenários mostram como os blocos colaboram em tempo de execução. Os nomes nos diagramas são os das classes e funções do código, para que cada passo possa ser conferido.

## 6.1 Gerar uma ontologia: do texto ao OWL validado

Arquivos: `omaker/ui/pages/generator.py`, `omaker/ui/pages/runner.py`, `omaker/ui/workers.py`, `omaker/pipeline/engine.py`, `omaker/ontology/builder.py`.

```mermaid
sequenceDiagram
  autonumber
  actor U as Usuario
  participant G as GeneratorPage
  participant W as PipelineWorker
  participant E as HybridEngine
  participant L as OllamaClient
  participant N as BiomedicalNER
  participant P as RelationExtractorPURE
  participant B as ontology.builder
  participant H as HermiT via Java

  U->>G: cola o texto, informa o nome e clica em processar
  G->>G: confere campos e looks_non_english
  opt texto parece portugues ou espanhol
    G->>U: pergunta se deve processar mesmo assim
  end
  G->>W: _rodar(gerar_ontologia) e start()
  Note over G,W: botao de gerar desligado, Cancelar ligado
  W->>E: gerar_ontologia(texto, ..., log_callback)
  E->>L: check() com GET /api/tags
  alt Ollama fora do ar ou modelo ausente
    L-->>E: LLMError
    E-->>W: excecao
    W-->>G: falhou(mensagem)
  end
  E->>N: extract(texto), se OMAKER_ENTITIES for ner ou both
  E->>L: extract_entities_llm, blocos de ate 3000 caracteres
  L-->>E: propostas, cada uma localizada no texto
  E->>E: merge_entities, unique_entities, generate_pairs
  E->>P: load(checkpoint) e predict(pares)
  P-->>E: relacao e confianca por par, com temperatura aplicada
  E->>E: limite de confianca, melhor tripla por chave, filter_by_domain
  E->>L: ask_taxonomy
  L-->>E: classes, instancias, disjuncoes
  E->>E: validate_taxonomy
  E->>B: new_world_ontology(IRI) e populate
  B->>H: sync_reasoner_hermit
  H-->>B: consistente, inconsistente ou erro
  B-->>E: ReasonerStatus e save em RDF/XML
  E-->>W: OntologyResult
  W-->>G: concluido(resultado)
  G->>U: completion_message e botao Abrir no Protege
```

Pontos de atenção:

- Cada etapa escreve no log pelo `log_callback`. No worker, esse callback emite o sinal `log` e, se o usuário pediu para cancelar, levanta `Cancelled` (subclasse de `BaseException`, para atravessar os `except Exception` do motor). O cancelamento vale, portanto, entre etapas, e uma chamada longa ao Ollama ou ao HermiT termina antes (`tests/test_pipeline_worker.py::test_cancel_not_swallowed_by_broad_except`).
- Se não houver pares candidatos, o PURE nem é carregado. Se não houver entidades, o motor levanta `ValueError` e a página mostra o erro.
- Sem checkpoint e sem download, as relações vêm de `classify_pairs` (LLM) e entram sem confiança ([cenário 6.3](#63-primeiro-uso-com-download-do-modelo)).
- O raciocinador nunca impede a gravação: uma ontologia inconsistente é salva e a mensagem final pede revisão.

## 6.2 Atualizar uma ontologia existente

Arquivos: `omaker/ui/pages/updater.py`, `omaker/pipeline/engine.py`, `omaker/ontology/builder.py`, `omaker/ontology/alignment.py`.

```mermaid
sequenceDiagram
  autonumber
  actor U as Usuario
  participant UP as UpdaterPage
  participant W as PipelineWorker
  participant E as HybridEngine
  participant B as ontology.builder
  participant A as ontology.alignment
  participant H as HermiT via Java

  U->>UP: escolhe o .owl e cola as novas evidencias
  UP->>W: _rodar(atualizar_ontologia)
  W->>E: atualizar_ontologia(caminho_owl, texto, ...)
  E->>E: extrair(texto), igual ao cenario 6.1
  E->>B: load_world_ontology(caminho_owl)
  E->>B: populate(onto, taxonomia, triplas)
  B->>A: is_external(onto)
  alt ontologia externa, sem a raiz BiomedicalEntity
    B->>A: build_label_index, rotulos, sinonimos exatos e nomes
    B->>B: reaproveita Drug, Disease, Symptom pelo rotulo
    B->>A: aligned_class para subclasses e individuos
    Note over B,A: so dentro do ramo do tipo da entidade
    B->>B: cria o que falta no namespace do OMAKER
    B->>B: AllDisjoint so entre classes do OMAKER
  else ontologia gerada pelo OMAKER
    B->>B: reaproveita classes, propriedades e individuos pelo nome
  end
  B-->>E: numero de relacoes novas
  E->>B: run_reasoner
  B->>H: sync_reasoner_hermit
  H-->>B: estado
  E->>B: save no mesmo arquivo
  E-->>W: OntologyResult
  W-->>UP: concluido(resultado)
  UP->>U: completion_message
```

A atualização é idempotente: rodar duas vezes com a mesma entrada não duplica classes, indivíduos nem disjunções (`tests/test_alignment.py::test_second_update_is_idempotent`, `tests/test_alignment.py::test_alldisjoint_not_repeated_on_second_update`). O arquivo original é sobrescrito, sem cópia de segurança ([seção 11](11-riscos-e-debito-tecnico.md)).

## 6.3 Primeiro uso com download do modelo

Arquivos: `omaker/pipeline/engine.py`, `omaker/paths.py`, `omaker/relations/download.py`, `omaker/relations/model.py`, `omaker/relations/calibration.py`.

```mermaid
sequenceDiagram
  autonumber
  participant E as HybridEngine.extrair
  participant PA as paths
  participant D as download
  participant GH as GitHub Releases
  participant P as RelationExtractorPURE
  participant HF as Hugging Face Hub
  participant L as classify_pairs via LLM

  E->>PA: default_checkpoint_path()
  PA-->>E: OMAKER_CHECKPOINT, ou models na pasta do usuario no .exe, ou raiz do projeto
  E->>D: ensure_pure_checkpoint(caminho, log)
  alt OMAKER_NO_DOWNLOAD ligado
    D-->>E: False
  else checkpoint ausente
    D->>GH: GET omaker_pure.pt com Range a partir do .part
    GH-->>D: blocos de 1 MB, progresso de 10 em 10 por cento no log
    D->>D: confere sha256 e renomeia .part
    D->>GH: GET omaker_pure.calibration.json
    D->>D: confere sha256 e renomeia
    D-->>E: True
  end
  alt checkpoint existe
    E->>P: load(checkpoint)
    P->>HF: from_pretrained do SpanBERT, baixado na primeira vez
    P->>P: load_state_dict, read_calibration do sidecar
    P-->>E: modelo com temperatura e limite calibrados
  else download falhou ou desligado
    E->>L: classify_pairs(pares)
    L-->>E: relacoes sem confianca
  end
```

- O NER e o Sentence-BERT também vêm do Hugging Face na primeira vez que são usados, pelo cache padrão das bibliotecas.
- Uma queda no meio do download deixa o `.part`; a próxima execução continua de onde parou. Se o servidor ignorar o `Range` (resposta diferente de 206), o download recomeça do zero (`tests/test_download.py::test_download_resumes_after_a_drop`). Um sha256 diferente apaga o `.part` e falha (`tests/test_download.py::test_download_rejects_a_wrong_hash`).
- Qualquer falha de rede vira uma linha no log e o pipeline segue (`tests/test_download.py::test_ensure_reports_failure_without_raising`, `tests/test_hybrid_engine.py::test_missing_checkpoint_is_downloaded_before_falling_back_to_the_llm`).
- `uv run python -m omaker.relations.download` baixa o modelo antes, mesmo com o download automático desligado.

## 6.4 Treino e calibração do classificador

Arquivos: `omaker/relations/biored.py`, `omaker/relations/train.py`, `omaker/relations/calibration.py`, `omaker/relations/release.py`; configuração em `configs/pure_biored.toml`.

```mermaid
sequenceDiagram
  autonumber
  actor Dev as Desenvolvedor
  participant BR as relations.biored
  participant NCBI as FTP do NCBI
  participant T as relations.train
  participant R as pasta runs
  participant C as relations.calibration
  participant RL as relations.release

  Dev->>BR: biored --download --review-sample 100
  BR->>NCBI: BIORED.zip, gravado como .part
  BR->>BR: extrai os tres PubTator, converte, save_splits
  Dev->>T: train --config configs/pure_biored.toml
  T->>T: set_seeds(42), le a divisao gravada
  T->>R: config.toml e splits
  loop cada epoca
    loop cada lote, ordem fixa pela semente da epoca
      T->>T: passo de otimizacao
      opt a cada save_every_steps passos
        T->>R: last.pt atomico, com estado aleatorio
      end
    end
    T->>T: micro-F1 na validacao
    opt melhor epoca ate aqui
      T->>R: model.pt com os hashes das frases de treino
    end
    T->>R: last.pt no fim da epoca
  end
  T->>T: teste uma unica vez com o melhor model.pt
  T->>R: metrics.json e report.md, apaga last.pt
  opt queda no meio do treino
    Dev->>T: train --resume runs/pasta
    T->>R: le config.toml, splits e last.pt
    T->>T: pula os lotes ja feitos e continua
  end
  Dev->>C: calibration --run runs/pasta
  C->>C: logits de validacao e teste com T igual a 1
  C->>C: fit_temperature e best_threshold so na validacao
  C->>R: calibration.json, calibration.md, model.calibration.json
  Dev->>RL: release --run runs/pasta --out dist/modelo
  RL->>RL: omaker_pure.pt sem texto, calibracao, SHA256SUMS
  Note over Dev,RL: envio manual para a Release e atualizacao dos sha256 em download.py
```

- A retomada reproduz o treino sem queda: mesmas métricas e mesma melhor época (`tests/test_training.py::test_resume_after_crash_matches_uninterrupted_run`, com quedas no meio da primeira época, no meio da segunda e no fim de uma época).
- `train --install` copia o melhor checkpoint para o caminho da interface e leva a calibração do mesmo treino, ou apaga uma calibração antiga (`tests/test_training.py::test_install_removes_a_stale_calibration`). `calibration --install` só copia se o checkpoint instalado tiver o mesmo sha256 (`tests/test_calibration.py::test_install_copies_calibration_only_to_the_same_model`).
- Resultado de referência: micro-F1 de teste 0,739 (IC 95% de 0,694 a 0,785) em 385 exemplos; temperatura 4,33; ECE no teste de 0,271 para 0,055; limite 0,35.

## 6.5 Avaliação de ponta a ponta com retomada

Arquivos: `omaker/evaluation/e2e.py`, `omaker/evaluation/biored_gold.py`, `omaker/pipeline/engine.py`.

```mermaid
sequenceDiagram
  autonumber
  actor Dev as Desenvolvedor
  participant M as e2e.main
  participant R as pasta runs
  participant S as evaluate_system
  participant ENV as system_environment
  participant E as HybridEngine.extrair
  participant G as score_doc

  Dev->>M: e2e --gold-biored --systems ...
  M->>M: check_preconditions, checkpoint exigido para pure
  M->>M: le o gabarito e monta os metadados
  alt com --resume
    M->>R: le results.json
    M->>M: compara RESUME_MUST_MATCH
    Note over M: gabarito, limite, modelo, temperatura, semente e checkpoint precisam ser iguais
  else execucao nova
    M->>R: cria a pasta e grava results.json vazio
  end
  M->>M: OMAKER_LLM_SEED igual a 0
  loop cada sistema
    alt sistema ja em results.json
      M->>M: pula
    else
      M->>R: le partial do sistema, se houver
      M->>S: evaluate_system(nome, docs, done, on_doc)
      S->>ENV: aplica OMAKER_ENTITIES e, se preciso, um checkpoint inexistente
      loop cada documento
        alt documento ja no parcial
          S->>S: reaproveita as previsoes
        else
          S->>E: extrair(texto, temperatura 0, with_taxonomy False)
          alt LLMError
            E-->>S: erro registrado, documento sem previsoes
          else
            E-->>S: triplas
            S->>R: partial atualizado de forma atomica
          end
        end
        S->>G: score_doc(documento, previsoes)
      end
      ENV-->>S: restaura o ambiente
      S-->>M: totais, por documento, erros e contaminacao
      M->>R: results.json, report.md, apaga o partial
    end
  end
```

- `system_environment` força o sistema escolhido: `OMAKER_ENTITIES` para a fonte das entidades e, nos sistemas cujas relações vêm do LLM, um `OMAKER_CHECKPOINT` que não existe, para o motor não usar o PURE (`tests/test_e2e.py::test_system_environment_is_applied_and_restored`). O download automático continua possível nesse caminho; em teste, `OMAKER_NO_DOWNLOAD=1` o desliga (`tests/conftest.py`).
- Um documento em que o LLM falha não entra no parcial, então a retomada tenta de novo (`tests/test_e2e.py::test_llm_error_counts_as_no_prediction_and_is_recorded`, `tests/test_e2e.py::test_biored_run_resumes_per_document`).
- Mudou o modelo ou o checkpoint, a retomada é recusada (`tests/test_e2e.py::test_resume_refuses_a_different_model`).
- Resultado de referência no teste do BioRED (100 resumos, 164 pares químico e doença), F1 estrito: `pure` 0,13; `both+pure` 0,09; `ner+llm` 0,16; `llm` 0,19.
