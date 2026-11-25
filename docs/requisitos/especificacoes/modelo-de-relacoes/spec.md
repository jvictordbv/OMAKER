# Modelo de relações

## Propósito

Produzir, de forma reproduzível, o classificador de relações usado pelo pipeline: preparar os dados (inclusive o BioRED), treinar com divisão fixa e retomada após queda, calibrar a confiança, publicar o checkpoint sem o texto de treino e baixá-lo com segurança na primeira execução. As escolhas estão nos registros de decisão [0005](../../../decisoes/0005-biored-como-dados-de-treino.md), [0007](../../../decisoes/0007-calibracao-por-temperatura.md), [0008](../../../decisoes/0008-executavel-leve-com-download.md) e [0009](../../../decisoes/0009-checkpoint-publicado-sem-texto.md). O modelo publicado (Release `pure-biored-v1`) teve micro-F1 de 0,739 no teste do BioRED (IC 95% de 0,694 a 0,785, 385 exemplos).

## Requisitos

### Requisito: Configuração do treino (MOD-01)

O sistema DEVE ler a configuração do treino da seção `[train]` de um arquivo TOML, com os valores padrão de `TrainConfig` para as chaves ausentes, e DEVE recusar o arquivo que tiver uma chave desconhecida, citando-a.

Fonte: `omaker/relations/config.py`, `configs/pure_biored.toml` ; Verificado por: `tests/test_training.py::test_load_config_reads_toml_and_rejects_unknown_key`, `tests/test_training.py::test_biored_config_is_valid`

#### Cenário: chave com erro de digitação

- **DADO** um TOML com a chave `epoch` no lugar de `epochs`
- **QUANDO** a configuração é lida
- **ENTÃO** a leitura falha com "chave desconhecida em [train]: epoch"

#### Cenário: configuração do BioRED

- **DADO** o arquivo `configs/pure_biored.toml`
- **QUANDO** ele é lido
- **ENTÃO** `splits_dir` é `data/biored/splits` e `save_every_steps` é 50

### Requisito: Artefatos de cada treino (MOD-02)

O sistema DEVE gravar cada treino numa pasta nova `runs/<data>-<hora>-<nome>/` com a configuração usada (`config.toml`), a divisão dos dados (`splits/`, com manifesto), as métricas (`metrics.json`), um relatório (`report.md`, com o commit e o comando exato) e o melhor checkpoint (`model.pt`); caminhos relativos da configuração DEVEM ser resolvidos a partir da raiz do repositório.

Fonte: `omaker/relations/train.py` ; Verificado por: `tests/test_training.py::test_run_writes_artifacts`

#### Cenário: treino concluído

- **DADO** uma configuração válida
- **QUANDO** o treino termina
- **ENTÃO** a pasta do treino tem `config.toml`, `splits/`, `metrics.json`, `report.md` e `model.pt`

### Requisito: Exemplos validados (MOD-03)

O sistema DEVE recusar um exemplo de treino com relação fora de `treats`, `causes`, `prevents` e `no_relation` ou com tipo de entidade desconhecido, informando o índice do exemplo.

Fonte: `omaker/relations/data.py` ; Verificado por: `tests/test_relation_data.py::test_load_current_dataset`, `tests/test_relation_data.py::test_unknown_relation_is_reported_with_index`, `tests/test_relation_data.py::test_unknown_type_is_reported_with_index`

#### Cenário: relação desconhecida

- **DADO** o terceiro exemplo do arquivo com a relação "inhibits"
- **QUANDO** os exemplos são carregados
- **ENTÃO** a leitura falha com "exemplo 2: relação desconhecida 'inhibits'"

### Requisito: Divisão fixa e agrupada por texto (MOD-04)

O sistema DEVE dividir os exemplos em treino, validação e teste com semente fixa, mantendo todos os exemplos da mesma frase no mesmo conjunto, estratificando pela relação quando cada relação tiver pelo menos três frases, e DEVE gravar um manifesto com a semente, as proporções, o sha256 dos dados de origem, se houve estratificação e as contagens por relação.

Fonte: `omaker/relations/data.py` ; Verificado por: `tests/test_relation_data.py::test_split_is_deterministic_and_disjoint_by_text`, `tests/test_relation_data.py::test_split_falls_back_when_class_too_small`, `tests/test_relation_data.py::test_save_and_load_roundtrip`

#### Cenário: mesma semente

- **DADO** os mesmos exemplos e a mesma semente
- **QUANDO** a divisão é feita duas vezes
- **ENTÃO** as duas divisões são iguais
- **E** nenhuma frase aparece em dois conjuntos

#### Cenário: relação rara

- **DADO** uma relação com menos de três frases
- **QUANDO** a divisão é feita
- **ENTÃO** ela não é estratificada, e o manifesto registra isso

### Requisito: Divisão gravada reaproveitada (MOD-05)

Quando `splits_dir` estiver configurado, o sistema DEVE usar a divisão gravada nessa pasta em vez de sortear outra, qualquer que seja a semente.

Fonte: `omaker/relations/train.py` ; Verificado por: `tests/test_training.py::test_existing_splits_are_reused`

#### Cenário: outra semente

- **DADO** a divisão de um treino anterior em `splits_dir` e a semente 999 na configuração
- **QUANDO** um novo treino começa
- **ENTÃO** os arquivos `train.json`, `dev.json` e `test.json` do novo treino são idênticos aos do anterior

### Requisito: Treino reproduzível (MOD-06)

O sistema DEVE fixar as sementes do Python, do NumPy e do PyTorch e DEVE gerar a ordem dos lotes de cada época a partir da semente e do número da época, de modo que dois treinos com a mesma configuração e os mesmos dados deem as mesmas métricas no mesmo dispositivo.

Fonte: `omaker/relations/train.py` ; Verificado por: `tests/test_training.py::test_training_is_reproducible`

#### Cenário: dois treinos iguais

- **DADO** a mesma configuração
- **QUANDO** o treino roda duas vezes
- **ENTÃO** o histórico por época e as métricas de teste são iguais

### Requisito: Teste avaliado uma única vez (MOD-07)

O sistema DEVE escolher o melhor checkpoint pelo micro-F1 na validação e DEVE avaliar o conjunto de teste uma única vez, no fim, com esse checkpoint; as métricas DEVEM trazer o micro-F1 sem `no_relation`, o macro-F1, os valores por classe e o intervalo de confiança de 95% ([AVA-01](../avaliacao/spec.md), [AVA-03](../avaliacao/spec.md)).

Fonte: `omaker/relations/train.py` ; Verificado por: `tests/test_training.py::test_test_set_evaluated_once`

#### Cenário: exemplos de teste

- **DADO** um treino de várias épocas
- **QUANDO** ele termina
- **ENTÃO** cada exemplo de teste passou pelo modelo exatamente uma vez

### Requisito: Ponto de retomada (MOD-08)

O sistema DEVE gravar um ponto de retomada (`last.pt`, com pesos, otimizador, agendador, histórico e estado dos geradores aleatórios) a cada `save_every_steps` passos e no fim de cada época, gravando primeiro num arquivo temporário e trocando o nome depois, e DEVE apagar o `last.pt` quando o treino terminar.

Fonte: `omaker/relations/train.py`, `omaker/relations/config.py` ; Verificado por: `tests/test_training.py::test_resume_after_crash_matches_uninterrupted_run`

#### Cenário: queda no meio da época

- **DADO** um treino com `save_every_steps=2` que cai no meio da primeira época
- **QUANDO** a pasta do treino é examinada
- **ENTÃO** existe `last.pt` e não existe `metrics.json`

### Requisito: Retomada equivalente (MOD-09)

O sistema DEVE retomar um treino interrompido com `--resume runs/<pasta>`, relendo a configuração e a divisão gravadas e pulando os lotes já feitos, e o resultado DEVE ser igual ao de um treino sem queda no mesmo dispositivo.

Fonte: `omaker/relations/train.py` ; Verificado por: `tests/test_training.py::test_resume_after_crash_matches_uninterrupted_run`

#### Cenário: queda no meio, no fim de época ou na segunda época

- **DADO** um treino que caiu depois de 3, 13 ou 21 passos
- **QUANDO** ele é retomado
- **ENTÃO** o histórico, as métricas de teste e a melhor época são iguais aos de um treino sem queda
- **E** o `last.pt` não existe mais

### Requisito: Retomada sem o que retomar (MOD-10)

O sistema NÃO DEVE refazer um treino que já terminou (tem `metrics.json`) e DEVE falhar com uma mensagem que cita o `last.pt` quando a pasta não tiver ponto de retomada.

Fonte: `omaker/relations/train.py` ; Verificado por: `tests/test_training.py::test_resume_of_finished_run_does_nothing`, `tests/test_training.py::test_resume_without_checkpoint_fails_clearly`

#### Cenário: treino já terminado

- **DADO** a pasta de um treino concluído
- **QUANDO** o usuário pede a retomada
- **ENTÃO** o `metrics.json` continua igual

#### Cenário: queda antes do primeiro ponto

- **DADO** uma pasta sem `last.pt`
- **QUANDO** o usuário pede a retomada
- **ENTÃO** o comando falha com uma mensagem que cita "last.pt" e manda rodar o treino de novo

### Requisito: Divisão ausente (MOD-11)

O sistema DEVE falhar antes de treinar, com o comando que gera os dados do BioRED, quando `splits_dir` apontar para uma pasta que não existe.

Fonte: `omaker/relations/train.py` ; Verificado por: `tests/test_training.py::test_missing_splits_dir_fails_clearly`

#### Cenário: BioRED não preparado

- **DADO** `splits_dir` com uma pasta inexistente
- **QUANDO** o treino começa
- **ENTÃO** ele falha com uma mensagem que contém "omaker.relations.biored"

### Requisito: Instalação explícita do checkpoint (MOD-12)

O sistema NÃO DEVE substituir o checkpoint usado pela interface ao fim de um treino, a menos que o usuário passe `--install`; com `--install`, DEVE copiar o modelo e a calibração deste treino, ou apagar a calibração antiga quando o treino não tiver uma.

Fonte: `omaker/relations/train.py` ; Verificado por: `tests/test_training.py::test_gui_checkpoint_untouched_without_install`, `tests/test_training.py::test_install_removes_a_stale_calibration`

#### Cenário: sem --install

- **DADO** um treino sem `--install`
- **QUANDO** ele termina
- **ENTÃO** o checkpoint da interface não é criado nem alterado

#### Cenário: calibração de outro modelo

- **DADO** o checkpoint da interface com um arquivo de calibração antigo
- **QUANDO** um treino novo é instalado com `--install`
- **ENTÃO** o checkpoint é substituído e o arquivo de calibração antigo é apagado

### Requisito: Leitura do formato PubTator (MOD-13)

O sistema DEVE ler os arquivos PubTator do BioRED (título, resumo, menções e relações) e DEVE recusar o documento em que o trecho indicado pelas posições de uma menção não bate com o texto da menção.

Fonte: `omaker/relations/biored.py` ; Verificado por: `tests/test_biored.py::test_parse_pubtator_reads_text_mentions_and_relations`, `tests/test_biored.py::test_parse_pubtator_rejects_offsets_that_do_not_match_the_text`

#### Cenário: posições erradas

- **DADO** uma menção cujas posições apontam para outra palavra
- **QUANDO** o arquivo é lido
- **ENTÃO** a leitura falha com "offsets ... não batem"

### Requisito: Download do BioRED (MOD-14)

O sistema DEVE baixar o BioRED do NCBI só quando os três arquivos PubTator ainda não existirem, gravando o zip primeiro como `.part`, apagando o parcial se o download cair, reaproveitando um zip válido já baixado e extraindo só `Train.PubTator`, `Dev.PubTator` e `Test.PubTator` pelo nome do arquivo; sem os arquivos, a leitura DEVE dizer como baixá-los.

Fonte: `omaker/relations/biored.py` ; Verificado por: `tests/test_biored.py::test_download_extracts_only_pubtator_and_skips_when_done`, `tests/test_biored.py::test_download_interrupted_leaves_no_zip_and_retries`, `tests/test_biored.py::test_download_reuses_existing_zip`, `tests/test_biored.py::test_load_biored_missing_file_says_how_to_get_it`

#### Cenário: download interrompido

- **DADO** uma queda de conexão no meio do download
- **QUANDO** o comando termina com erro
- **ENTÃO** não fica zip parcial na pasta
- **E** o próximo comando baixa de novo

#### Cenário: arquivos já presentes

- **DADO** os três arquivos PubTator na pasta
- **QUANDO** o download é pedido
- **ENTÃO** nada é baixado

### Requisito: Conversão do BioRED (MOD-15)

O sistema DEVE converter o BioRED para o esquema do OMAKER: `ChemicalEntity` vira `DRUG`, `DiseaseOrPhenotypicFeature` vira `DISEASE`, `Positive_Correlation` vira `causes` e `Negative_Correlation` vira `treats`, com o químico como sujeito; cada par químico e doença na mesma frase gera um exemplo com a primeira menção de cada conceito, o par sem relação vira `no_relation` e o par com outro tipo de relação é descartado. A divisão oficial em treino, validação e teste DEVE ser mantida.

Fonte: `omaker/relations/biored.py` ; Verificado por: `tests/test_biored.py::test_document_examples_maps_labels_per_sentence`, `tests/test_biored.py::test_document_examples_use_sentence_relative_spans_and_omaker_types`, `tests/test_biored.py::test_pair_split_across_sentences_gives_no_example`, `tests/test_biored.py::test_load_biored_uses_official_parts`, `tests/test_biored.py::test_cli_writes_splits`

#### Cenário: par em frases diferentes

- **DADO** um químico e uma doença relacionados no documento, mas em frases diferentes
- **QUANDO** o documento é convertido
- **ENTÃO** esse par não gera exemplo

#### Cenário: relação Association

- **DADO** um par químico e doença anotado com `Association` na mesma frase
- **QUANDO** o documento é convertido
- **ENTÃO** o par é descartado, e não vira `no_relation`

### Requisito: Amostra para conferência manual (MOD-16)

Com `--review-sample N`, o sistema DEVE gravar `revisao_mapeamento.csv` com N exemplos do treino, repartidos igualmente entre os rótulos, e colunas para o revisor marcar se o rótulo está correto.

Fonte: `omaker/relations/biored.py` ; Verificado por: `tests/test_biored.py::test_review_sample_is_balanced_csv`

#### Cenário: amostra de 100

- **DADO** os exemplos de treino do BioRED com três rótulos
- **QUANDO** o comando roda com `--review-sample 100`
- **ENTÃO** o CSV tem 100 linhas de exemplos, com 33 ou 34 de cada rótulo

### Requisito: Temperatura ajustada na validação (MOD-17)

O sistema DEVE ajustar a temperatura do PURE minimizando a log-verossimilhança negativa dos logits da validação, e a temperatura NÃO DEVE mudar a classe prevista, só a confiança.

Fonte: `omaker/relations/calibration.py` ; Verificado por: `tests/test_calibration.py::test_fit_temperature_recovers_overconfident_scale`, `tests/test_calibration.py::test_confidences_divide_logits_by_temperature`

#### Cenário: modelo confiante demais

- **DADO** logits três vezes maiores que os verdadeiros
- **QUANDO** a temperatura é ajustada
- **ENTÃO** ela fica perto de 3 (erro relativo de até 10%)

### Requisito: Erro de calibração medido (MOD-18)

O sistema DEVE medir o erro esperado de calibração (ECE) em 10 faixas de confiança e DEVE relatar, para o teste, o ECE, a precisão, a revocação e o micro-F1 antes da calibração (temperatura 1, limite 0,70), depois dela e sem limite, com o diagrama de confiabilidade por faixa.

Fonte: `omaker/relations/calibration.py` ; Verificado por: `tests/test_calibration.py::test_ece_is_zero_when_confidence_matches_accuracy`, `tests/test_calibration.py::test_ece_measures_overconfidence`

#### Cenário: confiança acima do acerto

- **DADO** 10 previsões com confiança 0,9 e metade delas certa
- **QUANDO** o ECE é medido
- **ENTÃO** o ECE é 0,4

### Requisito: Limite escolhido na validação (MOD-19)

O sistema DEVE escolher o limite de confiança na validação, entre 0,30 e 0,95 em passos de 0,05, como o que der o maior micro-F1 depois de transformar em `no_relation` as previsões abaixo dele, e, no empate, o menor limite; o teste NÃO DEVE participar da escolha.

Fonte: `omaker/relations/calibration.py` ; Verificado por: `tests/test_calibration.py::test_apply_threshold_turns_low_confidence_relations_into_no_relation`, `tests/test_calibration.py::test_best_threshold_drops_wrong_low_confidence_predictions`

#### Cenário: erros com confiança baixa

- **DADO** duas previsões certas com confiança 0,95 e 0,9 e duas erradas com 0,55 e 0,5
- **QUANDO** o limite é escolhido entre 0,0, 0,6 e 0,97
- **ENTÃO** o limite é 0,6 e o micro-F1 é 1,0

### Requisito: Arquivo de calibração ao lado do checkpoint (MOD-20)

O sistema DEVE gravar a temperatura e o limite em `<checkpoint>.calibration.json`, ao lado do checkpoint, sem alterar o `model.pt`, e o carregamento do PURE DEVE ler esse arquivo sozinho; sem ele, a temperatura é 1 e o limite fica indefinido.

Fonte: `omaker/relations/calibration.py`, `omaker/relations/model.py` ; Verificado por: `tests/test_calibration.py::test_sidecar_is_read_next_to_the_checkpoint`, `tests/test_calibration.py::test_loaded_model_uses_calibration_sidecar`

#### Cenário: modelo calibrado

- **DADO** `model.calibration.json` com temperatura 50 e limite 0,4 ao lado de `model.pt`
- **QUANDO** o PURE é carregado
- **ENTÃO** o modelo usa temperatura 50 e limite 0,4, e a confiança cai para perto de 1/4

### Requisito: Calibração instalada só no mesmo modelo (MOD-21)

Com `--install`, o sistema DEVE copiar a calibração para o checkpoint da interface só se esse checkpoint tiver o mesmo sha256 do `model.pt` calibrado; caso contrário, DEVE avisar que não instalou.

Fonte: `omaker/relations/calibration.py` ; Verificado por: `tests/test_calibration.py::test_install_copies_calibration_only_to_the_same_model`

#### Cenário: outro modelo instalado

- **DADO** o checkpoint da interface com pesos diferentes dos do treino calibrado
- **QUANDO** a calibração é instalada
- **ENTÃO** nada é copiado

### Requisito: Publicação sem texto de treino (MOD-22)

O sistema DEVE preparar os arquivos de uma Release com `omaker_pure.pt` sem as frases de treino (só os sha256 das frases normalizadas), a calibração do treino, se houver, e um `SHA256SUMS` no formato do `sha256sum`, com fim de linha LF.

Fonte: `omaker/relations/release.py`, `omaker/relations/data.py` ; Verificado por: `tests/test_download.py::test_export_strips_training_texts`

#### Cenário: checkpoint com frases

- **DADO** um `model.pt` que guarda "Aspirin prevents stroke." entre os textos de treino
- **QUANDO** o checkpoint é preparado para publicação
- **ENTÃO** o arquivo publicado não tem `train_texts` e tem o hash dessa frase em `train_text_hashes`
- **E** o `SHA256SUMS` tem o sha256 do arquivo publicado e nenhum `\r`

### Requisito: Download retomável e conferido (MOD-23)

O sistema DEVE baixar um arquivo publicado para `<destino>.part`, continuando um `.part` existente com o cabeçalho `Range` (e recomeçando do zero se o servidor ignorar o `Range`), DEVE conferir o sha256 e só então trocar o nome para o destino; com sha256 diferente, DEVE apagar o parcial e falhar.

Fonte: `omaker/relations/download.py` ; Verificado por: `tests/test_download.py::test_download_verifies_and_renames`, `tests/test_download.py::test_download_resumes_after_a_drop`, `tests/test_download.py::test_download_rejects_a_wrong_hash`

#### Cenário: queda no meio

- **DADO** um download do checkpoint que caiu depois de parte dos bytes
- **QUANDO** o download é pedido de novo
- **ENTÃO** ele continua do byte em que parou e o arquivo final confere com o sha256

#### Cenário: arquivo adulterado

- **DADO** um arquivo baixado cujo sha256 não é o publicado
- **QUANDO** o download termina
- **ENTÃO** o parcial é apagado, o destino não é criado e a mensagem manda baixar de novo

### Requisito: Garantia do checkpoint na primeira execução (MOD-24)

Quando o checkpoint faltar, o sistema DEVE baixar o modelo e o arquivo de calibração da Release `pure-biored-v1`, registrando o progresso de 10 em 10%; NÃO DEVE baixar se o checkpoint já existir ou se `OMAKER_NO_DOWNLOAD` tiver um valor diferente de vazio e de `0`; uma falha DEVE ser registrada no log, sem exceção, para o pipeline seguir com o LLM.

Fonte: `omaker/relations/download.py`, `omaker/pipeline/engine.py` ; Verificado por: `tests/test_download.py::test_ensure_skips_when_disabled_or_present`, `tests/test_download.py::test_ensure_downloads_model_and_calibration`, `tests/test_download.py::test_ensure_reports_failure_without_raising`

#### Cenário: sem internet

- **DADO** o checkpoint ausente e nenhuma conexão
- **QUANDO** o pipeline precisa do PURE
- **ENTÃO** o log diz "Download failed (...). Relations will be classified by the LLM; the download resumes next time."
- **E** nenhuma exceção interrompe a geração

#### Cenário: download desligado

- **DADO** `OMAKER_NO_DOWNLOAD=1` e o checkpoint ausente
- **QUANDO** o pipeline precisa do PURE
- **ENTÃO** nada é baixado

### Requisito: Hashes publicados preenchidos (MOD-25)

O sistema DEVE ter no código os sha256 do checkpoint e da calibração publicados, cada um com 64 dígitos hexadecimais.

Fonte: `omaker/relations/download.py` ; Verificado por: `tests/test_download.py::test_published_hashes_are_filled_in`

#### Cenário: hash esquecido

- **DADO** um sha256 vazio ou incompleto em `PURE_MODEL`
- **QUANDO** a suíte de testes roda
- **ENTÃO** o teste falha

### Requisito: Download explícito (MOD-26)

O comando `python -m omaker.relations.download` DEVE baixar o checkpoint para o caminho padrão, ou para `--dest`, mesmo com `OMAKER_NO_DOWNLOAD` definido, e DEVE terminar com código 0 em caso de sucesso e 1 em caso de falha.

Fonte: `omaker/relations/download.py` ; Verificado por: sem teste automatizado

#### Cenário: baixar antes de usar

- **DADO** `OMAKER_NO_DOWNLOAD=1` no ambiente
- **QUANDO** o usuário roda o comando de download
- **ENTÃO** o checkpoint é baixado mesmo assim

### Requisito: Calibração do modelo publicado (MOD-27)

Quando o checkpoint existir sem o arquivo de calibração, o sistema DEVE baixar só a calibração publicada, e apenas se o checkpoint for o publicado (mesmo sha256); NÃO DEVE baixar a calibração publicada para um checkpoint próprio; uma falha DEVE ser registrada no log, e o PURE DEVE seguir rodando sem calibração (limite 0,70), com nova tentativa na próxima execução.

Fonte: `omaker/relations/download.py` ; Verificado por: `tests/test_download.py::test_missing_calibration_of_the_published_model_is_downloaded_again`, `tests/test_download.py::test_calibration_is_not_downloaded_for_another_model`, `tests/test_download.py::test_calibration_failure_keeps_the_model_and_says_so`

#### Cenário: calibração que falhou antes

- **DADO** o checkpoint publicado já baixado e o arquivo de calibração ausente
- **QUANDO** o pipeline precisa do PURE
- **ENTÃO** só a calibração é baixada
- **E** o log diz "Calibration downloaded."

#### Cenário: checkpoint próprio

- **DADO** um checkpoint treinado pelo usuário, sem arquivo de calibração
- **QUANDO** o pipeline precisa do PURE
- **ENTÃO** nada é baixado, e o modelo roda com o limite padrão de 0,70

#### Cenário: calibração sem internet

- **DADO** o checkpoint publicado sem a calibração e nenhuma conexão
- **QUANDO** o pipeline precisa do PURE
- **ENTÃO** o PURE roda sem calibração, e o log diz que o download será tentado de novo
