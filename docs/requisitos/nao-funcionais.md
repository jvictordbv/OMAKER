# Requisitos não funcionais

Qualidades que valem para o sistema inteiro. Cada requisito tem um critério verificável, a fonte no código ou na configuração do repositório, a verificação (teste, fluxo do CI ou inspeção) e um cenário. As convenções são as da [especificação de requisitos](README.md#convenções-desta-especificação).

## Sumário

| Código | Qualidade | Requisito |
|---|---|---|
| RNF-01 | Privacidade | Texto processado só na máquina |
| RNF-02 | Privacidade | Nenhum serviço de nuvem nem chave de API |
| RNF-03 | Privacidade | Modelo publicado sem texto de terceiros |
| RNF-04 | Reprodutibilidade | Treino reproduzível |
| RNF-05 | Reprodutibilidade | Avaliação reproduzível e rastreável |
| RNF-06 | Reprodutibilidade | Experimentos registrados |
| RNF-07 | Portabilidade | Windows e Python 3.12 |
| RNF-08 | Portabilidade | Independência da pasta corrente |
| RNF-09 | Portabilidade | Caminhos com acento |
| RNF-10 | Robustez | Retomada de treino, avaliação e downloads |
| RNF-11 | Robustez | Gravações atômicas |
| RNF-12 | Robustez | Falha rápida do LLM em laço |
| RNF-13 | Robustez | Degradação sem internet ou sem Java |
| RNF-14 | Desempenho | Interface responsiva |
| RNF-15 | Recursos | Tamanho do executável e dos modelos |
| RNF-16 | Recursos | Memória e tempo de treino observados |
| RNF-17 | Manutenibilidade | Suíte rápida, isolada e sem rede |
| RNF-18 | Manutenibilidade | CI com lint e testes em todo push |
| RNF-19 | Manutenibilidade | Rótulos num só lugar |
| RNF-20 | Segurança | Downloads conferidos e extração segura |
| RNF-21 | Segurança | Fluxos do CI com permissões mínimas |
| RNF-22 | Licenciamento | AGPL-3.0-only no código e no executável |
| RNF-23 | Idioma | Entrada em inglês, interface em português |
| RNF-24 | Reprodutibilidade | Modelos do Hugging Face com revisão fixa |

## Privacidade

### Requisito: Texto processado só na máquina (RNF-01)

O sistema NÃO DEVE enviar o texto do usuário a nenhum serviço fora da máquina, exceto ao Ollama no endereço de `OLLAMA_HOST` (por padrão, `localhost`). As únicas outras conexões de rede DEVEM ser downloads de modelos e dados (Hugging Face, Release do GitHub, NCBI), que não levam o texto.

Critério: as chamadas HTTP do código estão só em `omaker/llm/client.py` (Ollama), `omaker/relations/download.py` (Release `pure-biored-v1`) e `omaker/relations/biored.py` (BioRED, só no comando de treino); os modelos do Hugging Face são baixados pelas bibliotecas `transformers` e `sentence-transformers` na primeira execução.

Fonte: `omaker/llm/client.py`, `omaker/relations/download.py`, `omaker/relations/biored.py`, `omaker/config.py` ; Verificado por: inspeção (busca por `requests` em `omaker/`); a substituição do cliente por um sem rede é verificada por `tests/test_llm_protocol.py::test_engine_runs_with_any_llm_client`, `tests/test_local_only.py::test_ollama_host_defaults_to_localhost`, `tests/test_local_only.py::test_only_the_ollama_client_and_the_downloaders_import_network_libraries`, `tests/test_local_only.py::test_generating_an_ontology_sends_the_text_only_to_the_local_ollama`

#### Cenário: Ollama na própria máquina

- **DADO** `OLLAMA_HOST` não definido
- **QUANDO** o usuário gera uma ontologia
- **ENTÃO** o texto só é enviado a `http://localhost:11434`

### Requisito: Nenhum serviço de nuvem nem chave de API (RNF-02)

O sistema NÃO DEVE pedir, guardar nem usar chave de API, e as funções públicas do motor NÃO DEVEM ter parâmetro de chave.

Fonte: `omaker/pipeline/engine.py`, `omaker/ui/pages/settings.py` ; Verificado por: `tests/test_hybrid_engine.py::test_engine_entry_points_take_no_api_key`, `tests/test_ui_pages.py::test_settings_has_no_api_key_field`

#### Cenário: configurações antigas com chave

- **DADO** uma `api_key` gravada por uma versão antiga
- **QUANDO** o usuário salva as configurações
- **ENTÃO** a chave é apagada das preferências

### Requisito: Modelo publicado sem texto de terceiros (RNF-03)

O checkpoint publicado NÃO DEVE conter as frases de treino (texto de resumos do PubMed); DEVE conter só os sha256 das frases normalizadas, suficientes para a verificação de contaminação.

Fonte: `omaker/relations/release.py`, `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_download.py::test_export_strips_training_texts`, `tests/test_e2e.py::test_contamination_with_hashed_training_texts`

#### Cenário: arquivo da Release

- **DADO** o `omaker_pure.pt` da Release `pure-biored-v1`
- **QUANDO** o arquivo é aberto
- **ENTÃO** ele não tem `train_texts` e tem `train_text_hashes`

## Reprodutibilidade

### Requisito: Treino reproduzível (RNF-04)

Dois treinos com a mesma configuração, os mesmos dados e o mesmo dispositivo DEVEM dar o mesmo histórico e as mesmas métricas de teste. As sementes (padrão 42) e a divisão fixa dos dados DEVEM ser gravadas junto com cada treino.

Critério: igualdade exata de `metrics.json` (histórico e teste) entre duas execuções. Limite conhecido: trocar de dispositivo no meio (por exemplo, retomar na GPU um treino começado na CPU) não reproduz bit a bit, porque o estado aleatório da GPU não existia no ponto gravado (nota `06-experimentos/2026-11-12-pure-biored.md`).

Fonte: `omaker/relations/train.py`, `omaker/relations/data.py` ; Verificado por: `tests/test_training.py::test_training_is_reproducible`, `tests/test_relation_data.py::test_split_is_deterministic_and_disjoint_by_text`, `tests/test_training.py::test_existing_splits_are_reused`

#### Cenário: repetir um treino

- **DADO** a configuração `configs/pure_biored.toml`
- **QUANDO** o treino roda duas vezes na mesma máquina
- **ENTÃO** os dois `metrics.json` têm o mesmo histórico e o mesmo resultado de teste

### Requisito: Avaliação reproduzível e rastreável (RNF-05)

A avaliação de ponta a ponta DEVE rodar o LLM com temperatura 0 e semente fixa (padrão 0) e DEVE gravar com os resultados o commit, o sha256 do gabarito, o modelo, a temperatura, a semente e o sha256 do checkpoint; uma retomada com qualquer um desses valores diferente DEVE ser recusada.

Fonte: `omaker/evaluation/e2e.py` ; Verificado por: `tests/test_e2e.py::test_results_written_after_each_system_with_metadata`, `tests/test_e2e.py::test_llm_seed_sent_to_ollama`, `tests/test_e2e.py::test_resume_refuses_a_different_model`

#### Cenário: conferir de onde veio um número

- **DADO** um `results.json` de avaliação
- **QUANDO** alguém quer repetir a execução
- **ENTÃO** os metadados dizem o commit, o gabarito, o modelo, a semente e o checkpoint exatos

### Requisito: Experimentos registrados (RNF-06)

Cada treino DEVE gravar a configuração usada, a divisão com manifesto (semente, proporções, sha256 dos dados, contagens), as métricas com intervalo de confiança e um relatório com o commit, a máquina e o comando exato; o teste DEVE ser avaliado uma única vez.

Fonte: `omaker/relations/train.py` ; Verificado por: `tests/test_training.py::test_run_writes_artifacts`, `tests/test_training.py::test_test_set_evaluated_once`

#### Cenário: relatório de um treino

- **DADO** um treino concluído
- **QUANDO** o `report.md` é aberto
- **ENTÃO** ele mostra o commit, o dispositivo, o comando e o micro-F1 de teste com o intervalo de 95%

## Portabilidade

### Requisito: Windows e Python 3.12 (RNF-07)

O sistema DEVE rodar no Windows com Python 3.12 (`requires-python = ">=3.12,<3.13"`); a suíte de testes e a montagem do executável DEVEM rodar no Windows do CI.

Fonte: `pyproject.toml`, `.python-version`, `.github/workflows/ci.yml`, `.github/workflows/exe.yml` ; Verificado por: fluxos do CI (`runs-on: windows-latest`), `tests/test_workflows.py::test_project_requires_python_3_12`, `tests/test_workflows.py::test_tests_and_executable_build_run_on_windows`

#### Cenário: pull request

- **DADO** um pull request aberto
- **QUANDO** o CI roda
- **ENTÃO** lint e testes rodam numa máquina Windows

### Requisito: Independência da pasta corrente (RNF-08)

O sistema DEVE achar o checkpoint, os recursos do pacote e os caminhos relativos das configurações de treino a partir da raiz do projeto, e não da pasta corrente. A pasta de destino padrão também não depende dela ([CFG-09](especificacoes/configuracao/spec.md)).

Fonte: `omaker/paths.py`, `omaker/relations/train.py` ; Verificado por: `tests/test_paths.py::test_checkpoint_path_independent_of_cwd`, `tests/test_ui_synonyms.py::test_synonyms_default_independent_of_cwd`

#### Cenário: atalho em outra pasta

- **DADO** o programa iniciado com a pasta corrente fora do repositório
- **QUANDO** a página de sinônimos abre
- **ENTÃO** a `symp.owl` do pacote é encontrada

### Requisito: Caminhos com acento (RNF-09)

O sistema DEVE rodar a partir de uma pasta cujo caminho tenha acentos (por exemplo `C:\Projetos\acadêmicos\...`); por isso o projeto NÃO DEVE ser instalado em modo editável, cujo arquivo `.pth` o Python 3.12 do Windows lê em cp1252.

Fonte: `pyproject.toml` (`[tool.uv] package = false`) ; Verificado por: `tests/test_accented_paths.py::test_project_is_not_installed_in_editable_mode`, `tests/test_accented_paths.py::test_ontology_is_generated_and_updated_in_a_folder_with_accents`, `tests/test_accented_paths.py::test_checkpoint_is_downloaded_to_a_folder_with_accents`

#### Cenário: repositório numa pasta com acento

- **DADO** o repositório clonado em `C:\Projetos\acadêmicos\OMAKER`
- **QUANDO** o usuário roda `uv run python -m omaker`
- **ENTÃO** o programa abre

## Robustez

### Requisito: Retomada de treino, avaliação e downloads (RNF-10)

Toda tarefa longa DEVE poder continuar de onde parou depois de uma queda (falta de energia, Ctrl+C, falta de memória, queda de rede): o treino pelo `last.pt` (a cada 50 passos por padrão e no fim de cada época), a avaliação por documento, o download do checkpoint pelo `.part` e o do BioRED refazendo só o que faltou.

Critério: o treino retomado chega ao mesmo resultado de um treino sem queda; a avaliação retomada não reprocessa documentos gravados; o download retomado pede só os bytes que faltam.

Fonte: `omaker/relations/train.py`, `omaker/evaluation/e2e.py`, `omaker/relations/download.py`, `omaker/relations/biored.py` ; Verificado por: `tests/test_training.py::test_resume_after_crash_matches_uninterrupted_run`, `tests/test_e2e.py::test_biored_run_resumes_per_document`, `tests/test_e2e.py::test_resume_skips_systems_already_evaluated`, `tests/test_download.py::test_download_resumes_after_a_drop`, `tests/test_biored.py::test_download_interrupted_leaves_no_zip_and_retries`

#### Cenário: queda de energia na avaliação

- **DADO** uma avaliação no teste do BioRED que caiu no meio
- **QUANDO** o usuário roda o mesmo comando com `--resume runs/<pasta>`
- **ENTÃO** a avaliação continua do primeiro documento ainda não gravado

### Requisito: Gravações atômicas (RNF-11)

O sistema DEVE gravar pontos de retomada, parciais de avaliação, downloads e arquivos extraídos primeiro num arquivo temporário (`.part`) e trocar o nome só no fim, para que uma queda durante a gravação não deixe um arquivo corrompido no lugar do bom.

Fonte: `omaker/relations/train.py`, `omaker/evaluation/e2e.py`, `omaker/relations/download.py`, `omaker/relations/biored.py` ; Verificado por: `tests/test_download.py::test_download_verifies_and_renames`, `tests/test_biored.py::test_download_interrupted_leaves_no_zip_and_retries`

#### Cenário: queda durante o download do BioRED

- **DADO** uma queda no meio do download
- **QUANDO** a pasta é examinada
- **ENTÃO** não existe `BIORED.zip` incompleto

### Requisito: Falha rápida do LLM em laço (RNF-12)

Uma resposta do LLM que não termina DEVE ser interrompida pelo limite de 4.096 tokens, e não pelo tempo limite de 600 s, e NÃO DEVE ser repetida.

Critério: um único pedido ao Ollama quando a resposta para por limite de tokens.

Fonte: `omaker/llm/client.py` ; Verificado por: `tests/test_llm_client.py::test_output_limit_stops_a_looping_model_without_retrying`

#### Cenário: resumo que faz o modelo repetir

- **DADO** um resumo em que o `qwen3` repete a mesma lista sem fechar o JSON
- **QUANDO** a avaliação chega nele
- **ENTÃO** o documento falha logo, conta como sem previsões e a avaliação segue

### Requisito: Degradação sem internet ou sem Java (RNF-13)

Sem internet, o sistema DEVE seguir com as relações pelo LLM; sem Java, DEVE gravar a ontologia e dizer que ela não foi validada. Nenhum dos dois casos DEVE derrubar a geração.

Fonte: `omaker/relations/download.py`, `omaker/pipeline/engine.py`, `omaker/ontology/builder.py`, `omaker/ui/messages.py` ; Verificado por: `tests/test_download.py::test_ensure_reports_failure_without_raising`, `tests/test_hybrid_engine.py::test_missing_checkpoint_is_downloaded_before_falling_back_to_the_llm`, `tests/test_owl_builder.py::test_construir_reports_reasoner_unavailable`, `tests/test_ui_messages.py::test_completion_message_never_claims_validation_when_unavailable`

#### Cenário: notebook sem rede e sem Java

- **DADO** nenhuma conexão, nenhum Java e o modelo do LLM instalado no Ollama
- **QUANDO** o usuário gera uma ontologia
- **ENTÃO** o arquivo `.owl` é gravado e a mensagem diz que ele foi gerado sem validação

## Desempenho e recursos

### Requisito: Interface responsiva (RNF-14)

A interface NÃO DEVE congelar durante a geração, a atualização ou a detecção de sinônimos, e o pedido de fechar a janela no meio de uma etapa longa DEVE retornar em menos de 0,5 s.

Fonte: `omaker/ui/workers.py`, `omaker/ui/main_window.py` ; Verificado por: `tests/test_ui_generation.py::test_close_during_silent_step_does_not_block_and_closes_later`, `tests/test_ui_generation.py::test_generation_runs_off_gui_thread`

#### Cenário: fechar durante uma chamada ao LLM

- **DADO** uma chamada ao LLM em andamento, sem log
- **QUANDO** o usuário fecha a janela
- **ENTÃO** o fechamento retorna em menos de 0,5 s e a janela fecha ao fim da etapa

### Requisito: Tamanho do executável e dos modelos (RNF-15)

O executável NÃO DEVE embutir os modelos. Valores medidos na Release v0.3.0: 771 MB descompactado e 296 MB no `OMAKER-windows.zip`. Os modelos são baixados na primeira execução: SpanBERT (cerca de 410 MB), NER (cerca de 250 MB), classificador PURE publicado (438 MB) e Sentence-BERT.

Critério: o passo "Tamanho" do fluxo do executável informa o tamanho da pasta montada; o `.zip` não contém `omaker_pure.pt`.

Fonte: `OMAKER.spec`, `.github/workflows/exe.yml`, `omaker/relations/download.py` ; Verificado por: `tests/test_workflows.py::test_executable_does_not_bundle_the_models`, `tests/test_workflows.py::test_executable_workflow_reports_the_size_of_the_built_folder`

#### Cenário: nova versão

- **DADO** uma tag `v*`
- **QUANDO** o executável é montado
- **ENTÃO** o log do fluxo mostra o tamanho de `dist\OMAKER` em MB

### Requisito: Memória e tempo de treino observados (RNF-16)

Esta especificação registra, sem limite obrigatório, os recursos observados: o Ollama com o `qwen3` ocupou cerca de 9,6 GB de memória durante a avaliação; o treino do PURE com o BioRED levou cerca de 8 s por passo na CPU e cerca de 2 minutos por época numa RTX 3050 de 6 GB (máquina com 32 GB de RAM). Tarefas longas DEVEM poder rodar numa janela própria, fora de outros processos pesados, graças à retomada (RNF-10).

Fonte: nota `06-experimentos/2026-11-12-pure-biored.md` ; Verificado por: sem teste automatizado (medição manual)

#### Cenário: avaliação numa máquina com pouca memória

- **DADO** uma avaliação interrompida por falta de memória
- **QUANDO** ela é retomada numa janela própria com `--resume`
- **ENTÃO** ela continua do último documento gravado

## Manutenibilidade

### Requisito: Suíte rápida, isolada e sem rede (RNF-17)

A suíte rápida (`pytest -m "not slow and not ollama"`) DEVE rodar sem rede e sem o Ollama real, NÃO DEVE baixar o checkpoint e NÃO DEVE ler nem gravar as configurações reais do usuário; os testes que baixam modelos levam o marcador `slow` e os que precisam do Ollama real, `ollama`.

Fonte: `tests/conftest.py`, `pyproject.toml` ; Verificado por: `tests/test_ui_synonyms.py::test_default_settings_are_isolated_in_tests`, `tests/conftest.py` (fixtures `no_model_download`, `isolated_qsettings` e o Ollama falso `fake_ollama`)

#### Cenário: testes da interface

- **DADO** um teste que abre a janela principal
- **QUANDO** ele lê as preferências
- **ENTÃO** elas vêm de um arquivo `.ini` temporário, e não do registro do Windows

### Requisito: CI com lint e testes em todo push (RNF-18)

Todo push e todo pull request DEVEM passar pelo `ruff check .` (regras E, F, W, B, I, UP e BLE; o limite de tamanho de linha, E501, fica desligado) e pela suíte rápida no CI; o gancho de pré-commit DEVE rodar o ruff e a suíte rápida antes de cada commit local. A `main` NÃO DEVE receber commit direto.

Fonte: `.github/workflows/ci.yml`, `pyproject.toml`, `.pre-commit-config.yaml`, `CONTRIBUTING.md` ; Verificado por: fluxo `.github/workflows/ci.yml`, `tests/test_workflows.py::test_ci_runs_lint_and_the_fast_suite_on_every_push_and_pull_request`, `tests/test_workflows.py::test_ruff_rules_are_the_documented_ones`, `tests/test_workflows.py::test_pre_commit_hook_runs_ruff_and_the_fast_suite`

#### Cenário: pull request com erro de lint

- **DADO** um pull request com um import não usado
- **QUANDO** o CI roda
- **ENTÃO** o passo "Lint (ruff)" falha e o pull request não fica verde

### Requisito: Rótulos num só lugar (RNF-19)

Os tipos de entidade, os rótulos de relação, os pares de tipos permitidos, as classes-base e o domínio das relações DEVEM ser definidos só em `omaker/domain/labels.py`, e um checkpoint treinado com outros rótulos DEVE ser recusado.

Fonte: `omaker/domain/labels.py`, `omaker/relations/model.py` ; Verificado por: `tests/test_relation_extractor.py::test_load_rejects_incompatible_labels`

#### Cenário: rótulo novo

- **DADO** uma relação nova acrescentada a `REL2ID`
- **QUANDO** o checkpoint antigo é carregado
- **ENTÃO** o carregamento falha e pede um novo treino

## Segurança

### Requisito: Downloads conferidos e extração segura (RNF-20)

O checkpoint e a calibração baixados DEVEM ser conferidos pelo sha256 publicado antes de serem usados, e a extração do BioRED DEVE gravar só os três arquivos esperados, pelo nome, nunca pelo caminho guardado no zip.

Fonte: `omaker/relations/download.py`, `omaker/relations/biored.py` ; Verificado por: `tests/test_download.py::test_download_rejects_a_wrong_hash`, `tests/test_download.py::test_published_hashes_are_filled_in`, `tests/test_biored.py::test_download_extracts_only_pubtator_and_skips_when_done`

#### Cenário: zip com caminho malicioso

- **DADO** um zip do BioRED com uma entrada extra `../fora.txt`
- **QUANDO** ele é extraído
- **ENTÃO** só os três arquivos PubTator são gravados, dentro da pasta de destino, e `fora.txt` não aparece fora dela

### Requisito: Fluxos do CI com permissões mínimas (RNF-21)

Os fluxos do CI DEVEM ter só permissão de leitura por padrão, com escrita apenas no passo que anexa o executável à Release, e DEVEM fixar cada ação externa pelo SHA do commit.

Fonte: `.github/workflows/ci.yml`, `.github/workflows/exe.yml` ; Verificado por: `tests/test_workflows.py::test_workflows_are_read_only_by_default`, `tests/test_workflows.py::test_only_the_release_job_can_write_to_the_repository`, `tests/test_workflows.py::test_every_external_action_is_pinned_by_commit_sha`

#### Cenário: revisão de um fluxo

- **DADO** o arquivo `.github/workflows/exe.yml`
- **QUANDO** ele é inspecionado
- **ENTÃO** `permissions: contents: read` vale para todos os jobs, exceto `release`, e todo `uses:` aponta para um SHA

## Licenciamento

### Requisito: AGPL-3.0-only no código e no executável (RNF-22)

O código DEVE ser distribuído sob a AGPL-3.0-only, declarada no `pyproject.toml` e no `LICENSE`, e o executável DEVE levar o texto da licença; os modelos baixados mantêm as licenças de quem os publicou.

Fonte: `LICENSE`, `pyproject.toml`, `OMAKER.spec`, `omaker/self_check.py` ; Verificado por: `tests/test_packaging.py::test_license_ships_with_the_executable`, `tests/test_self_check.py::test_self_check_passes_from_source` (confere o `LICENSE` junto do programa)

#### Cenário: executável distribuído

- **DADO** o `OMAKER-windows.zip` de uma Release
- **QUANDO** ele é descompactado
- **ENTÃO** a pasta tem o arquivo `LICENSE`

## Idioma

### Requisito: Entrada em inglês, interface em português (RNF-23)

O pipeline DEVE processar texto em inglês (os modelos foram treinados em inglês) e a interface DEVE estar em português, com aviso fixo de idioma e pergunta antes de processar um texto que pareça português ou espanhol ([INT-07](especificacoes/interface/spec.md), [INT-08](especificacoes/interface/spec.md)). As mensagens de log do motor ficam em inglês. Esta especificação está em português do Brasil.

Fonte: `omaker/domain/text.py`, `omaker/ui/pages/runner.py` ; Verificado por: `tests/test_ui_generation.py::test_pages_say_the_text_must_be_in_english`, `tests/test_ui_generation.py::test_non_english_text_asks_before_generating`, `tests/test_text_utils.py::test_portuguese_and_spanish_texts_are_flagged`

#### Cenário: texto em espanhol

- **DADO** um texto médico em espanhol
- **QUANDO** o usuário clica no botão de gerar
- **ENTÃO** o programa pergunta se deve processar mesmo assim

### Requisito: Modelos do Hugging Face com revisão fixa (RNF-24)

O sistema DEVE carregar o NER (o padrão e o do BC5CDR), o SpanBERT e o Sentence-BERT numa revisão fixa (o commit, com 40 dígitos hexadecimais, guardado ao lado do nome do modelo), para que uma atualização no Hugging Face não mude os resultados sem aviso.

Fonte: `omaker/domain/labels.py` (`MODEL_REVISION`, `NER_MODEL_REVISION`), `omaker/nlp/synonyms.py` (`SYNONYM_MODEL_REVISION`), `omaker/nlp/ner.py`, `omaker/relations/model.py` ; Verificado por: `tests/test_model_revisions.py::test_revisions_are_full_commit_hashes`, `tests/test_model_revisions.py::test_ner_pipeline_gets_pinned_revision`, `tests/test_model_revisions.py::test_bc5cdr_ner_pipeline_gets_its_pinned_revision`, `tests/test_model_revisions.py::test_sentence_bert_gets_pinned_revision`, `tests/test_model_revisions.py::test_pure_pins_spanbert_revision_in_training_and_load`

#### Cenário: modelo atualizado no Hugging Face

- **DADO** o autor do NER publica uma versão nova do modelo
- **QUANDO** o OMAKER carrega o NER
- **ENTÃO** ele continua usando o commit fixado
