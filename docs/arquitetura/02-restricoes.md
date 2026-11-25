# 2. Restrições

Restrições são condições que a arquitetura não escolhe: ela precisa respeitá-las. Cada linha diz de onde vem a restrição e o que ela provoca no projeto.

## 2.1 Restrições técnicas

| Restrição | Origem ou evidência | Consequência na arquitetura |
|---|---|---|
| **Python 3.12**, e só ele | `requires-python = ">=3.12,<3.13"` em `pyproject.toml`; `.python-version` | O uv instala essa versão. O ruff mira `py312`. |
| **Windows** como plataforma alvo | CI em `windows-latest` (`.github/workflows/ci.yml`, `exe.yml`); busca de `java.exe` em `C:\Program Files` (`omaker/ontology/java.py`); `%LOCALAPPDATA%` (`omaker/paths.py`) | O `.exe` é só para Windows. Em outro sistema o código-fonte pode rodar, mas isso não é testado no CI: a busca do Java procura `java.exe` (só o `PATH` funciona igual) e a pasta do usuário cai em `~/.local/share`. |
| **Caminho com acento** na máquina de desenvolvimento | Comentário de `[tool.uv]` em `pyproject.toml` | `package = false`: o projeto roda da raiz, sem instalação editável, porque o `.pth` é lido em cp1252 e quebra com acento. Os comandos são `python -m omaker...` a partir da raiz. |
| **PySide6** (Qt 6) | `PySide6>=6.7,<7` | Interface com `QThread` e sinais; preferências no `QSettings`; testes com `pytest-qt` e `QT_QPA_PLATFORM=offscreen` no CI. |
| **Ollama local** com um modelo Qwen3 | `DEFAULT_MODEL = "qwen3:8b"` em `omaker/llm/client.py` | O Ollama é instalado à parte, em qualquer forma de distribuição. O nome do modelo precisa ser o exato que o Ollama usa (`OllamaClient.check`). Geração e atualização exigem o Ollama no ar. |
| **Java 11 ou mais novo** para o HermiT | owlready2 chama o HermiT por um processo Java (`omaker/ontology/builder.py`, `run_reasoner`) | O Java não vem no `.exe`. Sem Java, a ontologia é gravada sem validação e a interface diz isso. |
| **GPU opcional** | `torch.cuda.is_available()` em `omaker/nlp/ner.py`, `omaker/relations/model.py` e `omaker/relations/train.py` | Tudo roda na CPU. A GPU acelera o treino: cerca de 8 s por passo na CPU contra cerca de 2 min por época numa RTX 3050 de 6 GB (`.conhecimento/06-experimentos/2026-11-12-pure-biored.md`). |
| **Tamanho dos modelos** | SpanBERT 412 MB (só no treino; o pipeline usa os pesos do checkpoint), NER 255 MB, Sentence-BERT cerca de 470 MB (estimativa), checkpoint do PURE 438 MB (`.conhecimento/01-arquitetura/dependencias.md`) | Os modelos não vão dentro do `.exe`: são baixados na primeira execução ([registro 0008](../decisoes/0008-executavel-leve-com-download.md)). O `.exe` tem 771 MB descompactado e 296 MB no `.zip`. |
| **Limites de entrada dos modelos** | NER com limite de 512 tokens; PURE com `MAX_LENGTH = 256` (`omaker/relations/model.py`); LLM com `num_ctx` 8192 e resposta de até 4096 tokens (`omaker/llm/client.py`) | O NER roda frase a frase; cada par do PURE é uma única frase; as entidades pelo LLM vão em blocos de até 3000 caracteres; o prompt da taxonomia usa só os primeiros 6000 caracteres do texto (`TAXONOMY_TEXT_LIMIT`), com aviso no log. |
| **Texto em inglês** | NER, SpanBERT, BioRED e prompts são em inglês | O pipeline não traduz. A interface avisa e pergunta quando o texto parece português ou espanhol ([registro 0001](../decisoes/0001-pipeline-em-ingles.md)). |
| **transformers abaixo da versão 6** | `transformers>=4.44,<6` | O SpanBERT vem em fp16 e o transformers 5 mantém o tipo do checkpoint; o modelo chama `self.float()` para a cabeça e o encoder rodarem em fp32 (`omaker/relations/model.py`). |
| **PyInstaller** para o executável | `OMAKER.spec`, `pyinstaller>=6.10` | Os arquivos de dados do pacote são listados à mão no `.spec`; um teste confere a lista (`tests/test_packaging.py::test_spec_lists_all_package_data`). |

## 2.2 Restrições organizacionais

| Restrição | Origem | Consequência |
|---|---|---|
| **Projeto de mestrado** com prazo e equipe de duas pessoas | `README.md`, `CITATION.cff` | Escopo enxuto: um aplicativo de desktop, sem servidor nem ambiente de homologação. |
| **O dono do repositório decide** | Registros em `.conhecimento/05-decisoes/` (decisões D1, D3 e D5 respondidas pelo João) | Mudanças de modelo, dataset, licença ou distribuição esperam a decisão do João. A troca do NER está só proposta ([registro 0014](../decisoes/0014-troca-do-ner-bc5cdr.md)). |
| **Licença AGPL-3.0-only** | `LICENSE`, `license = "AGPL-3.0-only"` em `pyproject.toml` | O texto da licença vai junto do `.exe` (`OMAKER.spec`, `tests/test_packaging.py::test_license_ships_with_the_executable`). As dependências precisam ser compatíveis com a GPL-3.0 ([registro 0010](../decisoes/0010-licenca-agpl.md)). |
| **Licenças de terceiros** | Modelos do Hugging Face e BioRED | Os modelos baixados têm licenças próprias (`README.md`). A licença dos dados do BioRED não está declarada ([seção 11](11-riscos-e-debito-tecnico.md)). |
| **Pull request com CI verde** | `CONTRIBUTING.md`; `.github/workflows/ci.yml` | A `main` nunca recebe commit direto. Branch curto por assunto, revisão e CI verde ([registro 0011](../decisoes/0011-fluxo-de-branches-e-ci.md)). |
| **Versões por tag** | `.github/workflows/exe.yml` (gatilho `tags: ["v*"]`) | Uma tag `v*` monta o `.exe` e o anexa à Release da tag. |

## 2.3 Convenções

| Convenção | Onde está definida | Como é verificada |
|---|---|---|
| Documentação e interface em **português do Brasil** | `README.md`, `CONTRIBUTING.md`, textos de `omaker/ui/` | Revisão. Mensagens de log do motor e prompts ficam em inglês; nomes no código misturam os dois idiomas (por exemplo, `HybridEngine.extrair`, `gerar_ontologia`). |
| **Conventional Commits** com descrição em português | `CONTRIBUTING.md` | Revisão do PR. |
| **ruff** com as regras E, F, W, B, I, UP e BLE; linha de 120; E501 desligada | `[tool.ruff]` em `pyproject.toml` | `uv run ruff check .` no CI e no pre-commit (`.pre-commit-config.yaml`). |
| **Teste para todo comportamento novo ou corrigido** | `CONTRIBUTING.md` | 226 testes; 224 na suíte rápida (`-m "not slow and not ollama"`), que roda sem rede no CI e no pre-commit. |
| **Rótulos e tipos num único lugar** | `omaker/domain/labels.py` | Mudar `REL2ID` invalida checkpoints; `RelationExtractorPURE.load` recusa um checkpoint com rótulos diferentes (`tests/test_relation_extractor.py::test_load_rejects_incompatible_labels`). |
| **Mensagens nunca afirmam o que não aconteceu** | `CONTRIBUTING.md`; `omaker/ui/messages.py` | `tests/test_ui_messages.py::test_completion_message_never_claims_validation_when_unavailable`. |
| **Arquivos de dados do pacote listados no `.spec`** | `OMAKER.spec` | `tests/test_packaging.py::test_spec_lists_all_package_data`. |
