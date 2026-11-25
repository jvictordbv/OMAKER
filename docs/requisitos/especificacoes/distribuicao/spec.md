# Distribuição

## Propósito

Entregar o OMAKER de dois jeitos: a partir do código-fonte (`python -m omaker`) e como executável leve para Windows, montado pelo PyInstaller, que não embute os modelos e os baixa na primeira execução. O CI monta o executável, confere que ele abre com `--self-check` e anexa o `.zip` à Release de cada tag `v*`. As escolhas estão nos registros de decisão [0008](../../../decisoes/0008-executavel-leve-com-download.md) e [0010](../../../decisoes/0010-licenca-agpl.md). Na Release v0.3.0, o executável ocupa 771 MB descompactado e 296 MB no `.zip`.

## Requisitos

### Requisito: Pontos de entrada (DIS-01)

O sistema DEVE abrir a interface por `python -m omaker` e por `python OMAKER.py`, a partir da raiz do repositório, e DEVE devolver como código de saída o código do laço de eventos da interface.

Fonte: `omaker/__main__.py`, `OMAKER.py` ; Verificado por: `tests/test_entrypoint.py::test_main_returns_exec_code`, `tests/test_entrypoint.py::test_legacy_entrypoint_runs_main`

#### Cenário: atalho antigo

- **DADO** o usuário roda `python OMAKER.py`
- **QUANDO** o programa termina
- **ENTÃO** o código de saída é o devolvido por `omaker.__main__.main`

### Requisito: Executável leve (DIS-02)

O sistema DEVE ser empacotado pelo `OMAKER.spec` como uma pasta `OMAKER` com `OMAKER.exe` de janela (sem console), sem os modelos de NER, de relações e de embeddings, que são baixados na primeira execução ([MOD-24](../modelo-de-relacoes/spec.md)).

Fonte: `OMAKER.spec`, `.github/workflows/exe.yml` ; Verificado por: `tests/test_packaging.py::test_spec_is_valid_python`; a montagem é verificada pelo fluxo `.github/workflows/exe.yml` (não pela suíte de testes)

#### Cenário: montagem no CI

- **DADO** uma tag `v*` enviada ao repositório
- **QUANDO** o fluxo do executável roda
- **ENTÃO** ele monta `dist\OMAKER\OMAKER.exe` e informa o tamanho da pasta em MB

### Requisito: Dados do pacote no executável (DIS-03)

O `OMAKER.spec` DEVE listar todos os arquivos de dados que não são código dentro de `omaker/` (por exemplo `omaker/resources/symp.owl`, `omaker/relations/train_relations.json` e `omaker/evaluation/gold/samples.json`).

Fonte: `OMAKER.spec` ; Verificado por: `tests/test_packaging.py::test_spec_lists_all_package_data`

#### Cenário: arquivo de dados novo

- **DADO** um arquivo `.json` novo em `omaker/` que não está no `OMAKER.spec`
- **QUANDO** a suíte de testes roda
- **ENTÃO** o teste falha e cita o arquivo que falta

### Requisito: Licença junto do executável (DIS-04)

O sistema DEVE incluir o arquivo `LICENSE` na raiz do executável distribuído, e o `pyproject.toml` DEVE declarar a licença `AGPL-3.0-only`.

Fonte: `OMAKER.spec`, `pyproject.toml`, `LICENSE` ; Verificado por: `tests/test_packaging.py::test_license_ships_with_the_executable`

#### Cenário: LICENSE removido do spec

- **DADO** o `OMAKER.spec` sem a entrada `('LICENSE', '.')`
- **QUANDO** a suíte de testes roda
- **ENTÃO** o teste falha

### Requisito: Verificação do executável (DIS-05)

Com `--self-check <arquivo>`, o sistema DEVE, sem abrir a janela, importar os módulos de que o pipeline depende (inclusive os que o `transformers` carrega só na hora), instanciar e rodar BERT e DistilBERT mínimos sem baixar nada e conferir a presença de `symp.owl`, `LICENSE` e da pasta do HermiT; DEVE gravar no arquivo uma linha por verificação e, no fim, "OK" com código 0 ou "FALHOU" com código 1.

Fonte: `omaker/self_check.py`, `omaker/__main__.py` ; Verificado por: `tests/test_self_check.py::test_self_check_passes_from_source`, `tests/test_self_check.py::test_self_check_reports_a_missing_module`, `tests/test_self_check.py::test_entrypoint_runs_the_self_check_without_opening_the_window`

#### Cenário: módulo esquecido pelo empacotador

- **DADO** um módulo necessário que não entrou no executável
- **QUANDO** `OMAKER.exe --self-check saida.txt` roda
- **ENTÃO** `saida.txt` tem a linha "FALHOU  import <módulo>" e termina com "FALHOU"
- **E** o código de saída é 1

#### Cenário: código-fonte íntegro

- **DADO** o repositório com as dependências instaladas
- **QUANDO** a verificação roda
- **ENTÃO** o arquivo termina com "OK" e o código é 0

### Requisito: Publicação do executável (DIS-06)

O fluxo do executável DEVE falhar se o `--self-check` do executável montado terminar com código diferente de 0, DEVE compactar a pasta em `OMAKER-windows.zip` e, numa tag `v*`, DEVE anexar o `.zip` à Release da tag, criando-a se não existir; só esse último passo tem permissão de escrita no repositório.

Fonte: `.github/workflows/exe.yml` ; Verificado por: sem teste automatizado (o próprio fluxo do CI é a verificação)

#### Cenário: tag de versão

- **DADO** a tag `v0.3.0`
- **QUANDO** o fluxo termina sem erro
- **ENTÃO** a Release `v0.3.0` tem o arquivo `OMAKER-windows.zip`

### Requisito: Modelo na pasta do usuário (DIS-07)

No executável, o sistema DEVE guardar o checkpoint baixado em `%LOCALAPPDATA%\OMAKER\models\omaker_pure.pt`, e não na pasta do programa, que é temporária ou protegida; a variável `OMAKER_CHECKPOINT` continua tendo precedência ([CFG-04](../configuracao/spec.md)).

Fonte: `omaker/paths.py` ; Verificado por: `tests/test_paths.py::test_frozen_app_keeps_the_checkpoint_in_the_user_folder`

#### Cenário: primeira execução do .exe

- **DADO** o executável sem `OMAKER_CHECKPOINT` definido
- **QUANDO** o pipeline procura o checkpoint
- **ENTÃO** o caminho é `%LOCALAPPDATA%\OMAKER\models\omaker_pure.pt`

### Requisito: Caminhos independentes da pasta corrente (DIS-08)

O sistema DEVE localizar a raiz do projeto, os recursos do pacote (como a `symp.owl`) e o checkpoint padrão a partir do próprio código (ou da pasta de recursos do executável), e não da pasta corrente.

Fonte: `omaker/paths.py` ; Verificado por: `tests/test_paths.py::test_checkpoint_path_independent_of_cwd`, `tests/test_paths.py::test_project_root_holds_entrypoint_and_resource_path`, `tests/test_paths.py::test_package_resource_symp_owl`

#### Cenário: programa iniciado de outra pasta

- **DADO** a pasta corrente diferente da raiz do repositório
- **QUANDO** o caminho padrão do checkpoint é calculado
- **ENTÃO** ele é `omaker_pure.pt` na raiz do repositório

### Requisito: Versão única (DIS-09)

O sistema DEVE ter uma só versão: `omaker.__version__` DEVE ser igual à versão do `pyproject.toml`.

Fonte: `omaker/__init__.py`, `pyproject.toml` ; Verificado por: `tests/test_packaging.py::test_version_matches_pyproject`

#### Cenário: versão alterada só num lugar

- **DADO** a versão mudada no `pyproject.toml` e não em `omaker/__init__.py`
- **QUANDO** a suíte de testes roda
- **ENTÃO** o teste falha
