# 0008. Executável leve, com download dos modelos

- **Status:** Aceita
- **Data:** 2026-11-12
- **Decidido por:** João Victor (haverá `.exe`) e Gustavo (formato leve); o João aprovou em 2026-11-24 levar o modelo do BioRED no `.exe` leve

## Contexto

O OMAKER é um programa de desktop para Windows, usado por avaliadores e outros pesquisadores que não necessariamente têm Python. Os tamanhos medidos em 2026-11-12:

| Parte | Tamanho |
|---|---|
| Programa sem modelos (PyInstaller, PyTorch para CPU) | cerca de 534 MB |
| SpanBERT base | 412 MB |
| Checkpoint do PURE treinado | 438 MB |
| NER `d4data/biomedical-ner-all` | 255 MB |
| Sentence-BERT dos sinônimos | cerca de 470 MB (estimativa) |

Um `.exe` com tudo dentro passaria de 2 GB, e cada checkpoint novo do PURE exigiria um `.exe` novo.

## Decisão

- O `.exe` leva o programa e o PyTorch para CPU, mas nenhum modelo.
- Na primeira execução, os modelos do Hugging Face (SpanBERT, NER, Sentence-BERT) vão para o cache do Hugging Face.
- O checkpoint do PURE é baixado da Release `pure-biored-v1` do GitHub quando o pipeline precisa dele. O download é retomável, conferido pelo sha256 e gravado em `%LOCALAPPDATA%\OMAKER\models` no `.exe`. Se falhar, as relações são classificadas pelo LLM, e o download é tentado de novo na próxima vez. `OMAKER_NO_DOWNLOAD=1` desliga o download automático.
- O CI monta o `.exe` (`.github/workflows/exe.yml`), roda `OMAKER.exe --self-check`, compacta em `OMAKER-windows.zip` e, numa tag `v*`, anexa o arquivo à Release.
- O `--self-check` importa o que o pipeline usa, monta modelos mínimos sem baixar nada e confere os arquivos de dados.

## Alternativas consideradas

- **`.exe` completo, com os modelos.** Funciona sem internet, mas passa de 2 GB a cada versão e acopla o programa ao checkpoint.
- **Só pelo Python (`uv sync` e `uv run python -m omaker`).** Continua sendo o caminho de desenvolvimento, mas exige instalar o `uv`.
- **Hospedar o checkpoint no Hugging Face Hub.** Possível; a Release do GitHub mantém tudo no mesmo repositório.

## Consequências

### Positivas

- O `.exe` da versão 0.3.0 tem 771 MB descompactado e 296 MB no `.zip`, bem abaixo dos mais de 2 GB.
- Um checkpoint novo do PURE não exige um `.exe` novo.
- Cada montagem no CI prova que o executável abre e importa o que precisa.

### Negativas e riscos

- A primeira execução precisa de internet e baixa cerca de 1,1 GB: SpanBERT (412 MB), NER (255 MB) e o checkpoint (438 MB), além do Sentence-BERT quando os sinônimos são usados.
- O SpanBERT base é baixado mesmo havendo o checkpoint, que já contém o encoder inteiro ([0004](0004-classificador-pure-marcadores-tipados.md)).
- O Ollama e o modelo do LLM continuam sendo instalados à parte, e o HermiT precisa de Java na máquina.
- O `--self-check` não roda o pipeline com os modelos reais; o caminho pesado só é exercitado na máquina do usuário.
- O programa depende da disponibilidade da Release do GitHub e do Hugging Face.

## Referências

- `OMAKER.spec`, `.github/workflows/exe.yml`, `omaker/self_check.py`, `omaker/__main__.py`, `omaker/relations/download.py`, `omaker/paths.py` (`user_data_dir`, `default_checkpoint_path`).
- Testes: `tests/test_download.py::test_download_resumes_after_a_drop`, `tests/test_download.py::test_download_rejects_a_wrong_hash`, `tests/test_download.py::test_ensure_reports_failure_without_raising`, `tests/test_hybrid_engine.py::test_missing_checkpoint_is_downloaded_before_falling_back_to_the_llm`, `tests/test_self_check.py::test_entrypoint_runs_the_self_check_without_opening_the_window`.
- [PR #20](https://github.com/jvictordbv/OMAKER/pull/20) (download do checkpoint), [PR #21](https://github.com/jvictordbv/OMAKER/pull/21) (`.exe` no CI), [PR #23](https://github.com/jvictordbv/OMAKER/pull/23) (versão 0.3.0).
- Notas internas do projeto: proposta das decisões D1, D3 e D5 (tabela de tamanhos) e diário de 2026-11-24 (primeira montagem).
