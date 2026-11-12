"""Página Atualizador: novas evidências mescladas numa ontologia existente."""

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from omaker.pipeline.engine import HybridEngine
from omaker.ui.messages import completion_message


class UpdaterPage(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.caminho_owl_atual = ""
        self._montar()

    def _montar(self):
        pagina = self
        layout_geral = QVBoxLayout()
        layout_geral.setContentsMargins(25, 25, 25, 25)
        layout_geral.setSpacing(15)

        header = QLabel("Atualizador de Ontologias")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #0f172a; margin-bottom: 5px;")
        layout_geral.addWidget(header)

        workspace = QHBoxLayout()
        workspace.setSpacing(20)

        col_esquerda = QVBoxLayout()
        col_esquerda.setSpacing(12)

        card_arquivo = QFrame()
        card_arquivo.setObjectName("CardPane")
        layout_card = QVBoxLayout(card_arquivo)

        self.lbl_arquivo_selecionado = QLabel("Nenhum arquivo base (.owl) carregado.")
        self.lbl_arquivo_selecionado.setStyleSheet("color: #64748b; font-style: italic;")

        btn_selecionar_arquivo = QPushButton("📂  Carregar Ontologia Existente")
        btn_selecionar_arquivo.setStyleSheet("background-color: #0284c7;")
        btn_selecionar_arquivo.clicked.connect(self.selecionar_arquivo_owl)

        layout_card.addWidget(btn_selecionar_arquivo)
        layout_card.addWidget(self.lbl_arquivo_selecionado)
        col_esquerda.addWidget(card_arquivo)

        lbl_texto = QLabel("Novas Evidências Clínicas (Para expansão do Grafo):")
        self.texto_entrada_atualizador = QTextEdit()

        self.btn_atualizar = QPushButton("🔄  Extrair e Mesclar Conhecimento")
        self.btn_atualizar.setStyleSheet("background-color: #0d9488;")
        self.btn_atualizar.clicked.connect(self.atualizar_ontologia_existente)

        col_esquerda.addWidget(lbl_texto)
        col_esquerda.addWidget(self.texto_entrada_atualizador)
        col_esquerda.addWidget(self.btn_atualizar)
        workspace.addLayout(col_esquerda, stretch=4)

        col_direita = QVBoxLayout()
        col_direita.setSpacing(8)

        lbl_log = QLabel("Log do Processo de Alinhamento Semântico:")
        self.log_atualizador = QTextEdit()
        self.log_atualizador.setReadOnly(True)
        self.log_atualizador.setStyleSheet("background-color: #0f172a; color: #fbbf24; font-family: 'Consolas', monospace; font-size: 12px; border: none; padding: 12px;")

        col_direita.addWidget(lbl_log)
        col_direita.addWidget(self.log_atualizador)
        workspace.addLayout(col_direita, stretch=3)

        layout_geral.addLayout(workspace)
        pagina.setLayout(layout_geral)

    def selecionar_arquivo_owl(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Selecione a Ontologia", "", "Ontologia OWL (*.owl)")
        if caminho:
            self.caminho_owl_atual = caminho
            self.lbl_arquivo_selecionado.setText(caminho)

    def atualizar_ontologia_existente(self):
        if not hasattr(self, 'caminho_owl_atual') or not self.caminho_owl_atual:
            QMessageBox.warning(self, "Aviso", "Selecione um arquivo .owl primeiro.")
            return

        texto = self.texto_entrada_atualizador.toPlainText().strip()
        api_key = self.settings.api_key()

        if not texto:
            QMessageBox.warning(self, "Aviso", "Preencha o texto das novas evidências.")
            return

        # Prepara a interface para o processamento
        self.btn_atualizar.setEnabled(False)
        self.log_atualizador.clear()
        QApplication.processEvents()

        try:
            # --- MANTÉM O PROCESSAMENTO (O Core precisa rodar!) ---
            resultado = HybridEngine.atualizar_ontologia(
                caminho_owl=self.caminho_owl_atual,
                texto=texto,
                api_key=api_key,
                modelo_llm=self.settings.modelo(),
                temp_llm=self.settings.temperatura(),
                protege_exe=self.settings.caminho_protege(),
                log_callback=lambda msg: [self.log_atualizador.append(msg), QApplication.processEvents()]
            )

            nivel, titulo, mensagem = completion_message(resultado)
            aviso = QMessageBox.information if nivel == "info" else QMessageBox.warning
            aviso(self, titulo, mensagem)
            self.log_atualizador.append(f"\n> [INFO] Atualização gravada (raciocinador: {resultado.reasoner.value}).")

        except Exception as e:  # noqa: BLE001  slot da GUI: mostra o erro ao usuário em vez de derrubar o app
            self.log_atualizador.append(f"\n> [CRITICAL ERROR] {str(e)}")
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro crítico:\n{str(e)}")

        finally:
            self.btn_atualizar.setEnabled(True)
