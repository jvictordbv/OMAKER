# Interface

## Propósito

Dar ao usuário uma janela de desktop (PySide6) para gerar, atualizar e enriquecer ontologias sem travar enquanto o motor trabalha. Etapas longas (Ollama, HermiT, download) rodam em segundo plano e podem ser canceladas, a janela fecha com segurança no meio de uma execução, e as mensagens nunca afirmam o que não aconteceu. A interface está em português; o texto de entrada deve estar em inglês ([registro de decisão 0001](../../../decisoes/0001-pipeline-em-ingles.md)).

## Requisitos

### Requisito: Páginas da janela (INT-01)

O sistema DEVE oferecer, numa barra lateral, sete páginas: Início, Gerador de Ontologia, Atualizador (Mescla), Fusão de Sinônimos, Metadados do Projeto, Configurações e Sobre.

Fonte: `omaker/ui/main_window.py`, `omaker/ui/pages/` ; Verificado por: `tests/test_ui_pages.py::test_main_window_composes_pages`

#### Cenário: janela aberta

- **DADO** o programa iniciado
- **QUANDO** a janela principal aparece
- **ENTÃO** a barra lateral tem 7 itens e a área de conteúdo tem 7 páginas

### Requisito: Execução em segundo plano (INT-02)

O sistema DEVE rodar a geração e a atualização numa thread separada da interface e DEVE mostrar, no console da página, cada mensagem de log do motor à medida que ela é emitida; a thread de trabalho NÃO DEVE tocar em widgets.

Fonte: `omaker/ui/workers.py`, `omaker/ui/pages/runner.py` ; Verificado por: `tests/test_ui_generation.py::test_generation_runs_off_gui_thread`, `tests/test_ui_generation.py::test_update_runs_off_gui_thread`, `tests/test_pipeline_worker.py::test_emits_log_and_result_from_other_thread`

#### Cenário: geração

- **DADO** o nome do arquivo e um texto preenchidos
- **QUANDO** o usuário clica no botão de gerar
- **ENTÃO** o motor roda fora da thread principal
- **E** as mensagens de log aparecem no console da página

### Requisito: Uma execução por vez (INT-03)

Durante uma execução, o sistema DEVE desabilitar o botão de iniciar, habilitar o de Cancelar e ignorar novos pedidos; ao fim, com sucesso, falha ou cancelamento, DEVE reabilitar o botão de iniciar e desabilitar o de Cancelar.

Fonte: `omaker/ui/pages/runner.py` ; Verificado por: `tests/test_ui_generation.py::test_generate_button_disabled_while_running`, `tests/test_ui_generation.py::test_generate_failure_reenables_button`

#### Cenário: segundo clique

- **DADO** uma geração em andamento
- **QUANDO** um novo pedido de geração chega
- **ENTÃO** ele é ignorado e o motor roda uma vez só

#### Cenário: falha do motor

- **DADO** o motor falha com "Ollama fora do ar"
- **QUANDO** a execução termina
- **ENTÃO** o log mostra a mensagem, uma caixa de erro aparece e o botão de gerar volta a ficar habilitado

### Requisito: Cancelar (INT-04)

O sistema DEVE oferecer o botão Cancelar nas páginas de geração e de atualização; o cancelamento DEVE valer na próxima mensagem de log do motor, atravessar os tratamentos genéricos de exceção do motor e terminar com a mensagem "[CANCELADO]" no log, sem caixa de erro, avisando que as etapas já concluídas não são desfeitas.

Fonte: `omaker/ui/workers.py`, `omaker/ui/pages/runner.py`, `omaker/ui/pages/generator.py`, `omaker/ui/pages/updater.py` ; Verificado por: `tests/test_ui_generation.py::test_cancel_generation`, `tests/test_pipeline_worker.py::test_cancel_stops_at_next_log`, `tests/test_pipeline_worker.py::test_cancelled_is_an_exception`, `tests/test_pipeline_worker.py::test_cancel_not_swallowed_by_broad_except`

#### Cenário: cancelar uma geração

- **DADO** uma geração em andamento
- **QUANDO** o usuário clica em Cancelar
- **ENTÃO** o log mostra "[CANCELANDO]" e, na próxima etapa, "[CANCELADO]"
- **E** nenhuma caixa de erro ou de aviso aparece, e o botão "Abrir no Protégé" continua desabilitado

### Requisito: Um único desfecho (INT-05)

O sistema DEVE emitir, ao fim de cada execução, exatamente um dos sinais concluído, falhou ou cancelado; uma exceção do motor DEVE virar o sinal falhou com a mensagem da exceção, sem derrubar a interface.

Fonte: `omaker/ui/workers.py` ; Verificado por: `tests/test_pipeline_worker.py::test_exception_becomes_falhou`, `tests/test_pipeline_worker.py::test_emits_log_and_result_from_other_thread`

#### Cenário: exceção no motor

- **DADO** o motor levanta uma exceção
- **QUANDO** a execução termina
- **ENTÃO** só o sinal falhou é emitido, com a mensagem da exceção

### Requisito: Fechar durante uma execução (INT-06)

Ao fechar a janela durante uma geração, atualização ou detecção de sinônimos, o sistema NÃO DEVE bloquear a interface nem encerrar com a thread rodando: DEVE pedir o cancelamento (a detecção de sinônimos não tem cancelamento e é aguardada), mostrar no título que está cancelando, suprimir as caixas de diálogo e fechar sozinho quando a etapa atual terminar.

Fonte: `omaker/ui/main_window.py` ; Verificado por: `tests/test_ui_generation.py::test_close_during_run_waits_for_worker`, `tests/test_ui_generation.py::test_close_during_silent_step_does_not_block_and_closes_later`, `tests/test_ui_generation.py::test_close_during_synonyms_waits_for_worker`

#### Cenário: etapa longa sem log

- **DADO** uma chamada ao LLM que leva 1,5 s sem emitir log
- **QUANDO** o usuário fecha a janela
- **ENTÃO** o pedido de fechar retorna em menos de 0,5 s e a janela continua visível
- **E** a janela fecha quando a etapa termina, sem nenhuma caixa de diálogo

### Requisito: Aviso fixo de idioma (INT-07)

O sistema DEVE mostrar nas páginas de geração e de atualização o aviso "O texto deve estar em inglês: os modelos de entidades e de relações foram treinados em inglês."

Fonte: `omaker/ui/pages/runner.py`, `omaker/ui/pages/generator.py`, `omaker/ui/pages/updater.py` ; Verificado por: `tests/test_ui_generation.py::test_pages_say_the_text_must_be_in_english`

#### Cenário: páginas de trabalho

- **DADO** a janela aberta
- **QUANDO** o usuário abre o Gerador ou o Atualizador
- **ENTÃO** a página tem um texto que menciona "inglês"

### Requisito: Pergunta quando o texto não parece inglês (INT-08)

Antes de gerar ou atualizar, o sistema DEVE perguntar se deve seguir quando o texto parecer português ou espanhol (pelo menos 12 palavras, com 8% ou mais de palavras comuns dessas línguas), com "Não" como resposta padrão, e NÃO DEVE perguntar para textos em inglês ou curtos.

Fonte: `omaker/ui/pages/runner.py`, `omaker/domain/text.py` ; Verificado por: `tests/test_ui_generation.py::test_non_english_text_asks_before_generating`, `tests/test_ui_generation.py::test_non_english_text_asks_before_updating`, `tests/test_ui_generation.py::test_english_text_is_not_questioned`, `tests/test_text_utils.py::test_english_medical_text_is_not_flagged`, `tests/test_text_utils.py::test_portuguese_and_spanish_texts_are_flagged`, `tests/test_text_utils.py::test_short_text_is_never_flagged`

#### Cenário: texto em português, usuário recusa

- **DADO** um texto médico em português
- **QUANDO** o usuário clica no botão de gerar e responde "Não"
- **ENTÃO** o motor não roda

#### Cenário: texto em português, usuário aceita

- **DADO** o mesmo texto
- **QUANDO** o usuário responde "Sim"
- **ENTÃO** a geração roda normalmente

#### Cenário: texto em inglês

- **DADO** um texto médico em inglês
- **QUANDO** o usuário clica no botão de gerar
- **ENTÃO** nenhuma pergunta aparece

### Requisito: Mensagens honestas (INT-09)

O sistema DEVE dizer "validado" só quando o HermiT rodou e não achou contradição; quando o HermiT apontar inconsistência, DEVE avisar que o arquivo foi salvo mas precisa de revisão; quando ele não puder rodar, DEVE avisar que a ontologia foi gerada sem validação e mandar ver o motivo no log. Toda mensagem final DEVE trazer o caminho do arquivo e o número de relações novas.

Fonte: `omaker/ui/messages.py`, `omaker/ui/pages/generator.py`, `omaker/ui/pages/updater.py` ; Verificado por: `tests/test_ui_messages.py::test_completion_message_never_claims_validation_when_unavailable`, `tests/test_ui_messages.py::test_completion_message_consistent`, `tests/test_ui_messages.py::test_completion_message_inconsistent`

#### Cenário: sem Java

- **DADO** o raciocinador terminou com o estado `UNAVAILABLE`
- **QUANDO** a mensagem final é montada
- **ENTÃO** ela é um aviso com o título "Ontologia gerada sem validação" e diz que o grafo "não foi validado"
- **E** ela traz o caminho do arquivo

#### Cenário: ontologia consistente

- **DADO** o raciocinador terminou com o estado `CONSISTENT`
- **QUANDO** a mensagem final é montada
- **ENTÃO** ela é informativa e diz que o grafo foi validado pelo HermiT

### Requisito: Campos obrigatórios (INT-10)

O sistema NÃO DEVE iniciar a geração sem o nome do arquivo e o texto, nem a atualização sem um arquivo `.owl` selecionado e o texto das novas evidências; em cada caso, DEVE mostrar um aviso que diz o que falta.

Fonte: `omaker/ui/pages/generator.py`, `omaker/ui/pages/updater.py` ; Verificado por: `tests/test_ui_generation.py::test_generation_does_not_start_without_file_name_and_text`, `tests/test_ui_generation.py::test_update_without_a_selected_owl_warns_and_does_not_run`, `tests/test_ui_generation.py::test_update_without_new_evidence_text_warns_and_does_not_run`

#### Cenário: atualização sem arquivo

- **DADO** nenhum `.owl` selecionado no Atualizador
- **QUANDO** o usuário clica em "Extrair e Mesclar Conhecimento"
- **ENTÃO** o aviso "Selecione um arquivo .owl primeiro." aparece e o motor não roda

### Requisito: Botão Abrir no Protégé (INT-11)

O sistema DEVE manter o botão "Abrir no Protégé" desabilitado até a geração gravar um arquivo que exista e DEVE transformar qualquer erro do sistema ao abrir o Protégé (executável ausente, arquivo inválido) num aviso com a mensagem do erro.

Fonte: `omaker/ui/pages/generator.py`, `omaker/ontology/protege.py` ; Verificado por: `tests/test_protege.py::test_open_button_starts_disabled`, `tests/test_protege.py::test_open_button_shows_warning_on_oserror`, `tests/test_ui_generation.py::test_generation_runs_off_gui_thread`

#### Cenário: executável inválido

- **DADO** um `Protege.exe` que o Windows não consegue executar (erro 193)
- **QUANDO** o usuário clica em "Abrir no Protégé"
- **ENTÃO** um único aviso aparece com o código 193

#### Cenário: geração concluída

- **DADO** uma geração que gravou o arquivo `.owl`
- **QUANDO** ela termina
- **ENTÃO** o botão "Abrir no Protégé" fica habilitado

### Requisito: Versão na página Sobre (INT-12)

A página Sobre DEVE mostrar a versão do pacote (`omaker.__version__`), a mesma do `pyproject.toml`.

Fonte: `omaker/ui/pages/about.py` ; Verificado por: `tests/test_ui_pages.py::test_about_page_shows_the_package_version`, `tests/test_packaging.py` (versão do pacote igual à do `pyproject.toml`)

#### Cenário: nova versão

- **DADO** a versão 0.3.0 em `pyproject.toml` e em `omaker/__init__.py`
- **QUANDO** o usuário abre a página Sobre
- **ENTÃO** ela mostra "OMAKER v0.3.0"
