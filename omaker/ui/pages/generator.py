"""Página Gerador: texto para uma nova ontologia OWL."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from omaker.ontology.protege import abrir_no_protege
from omaker.pipeline.engine import HybridEngine
from omaker.ui.messages import completion_message
from omaker.ui.pages.runner import PipelineRunnerMixin


class GeneratorPage(PipelineRunnerMixin, QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.caminho_owl_gerado = ""
        self._montar()

    def _montar(self):
        pagina = self
        layout_geral = QVBoxLayout()
        layout_geral.setContentsMargins(25, 25, 25, 25)
        layout_geral.setSpacing(15)

        header = QLabel("Gerador de Ontologias")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #0f172a; margin-bottom: 5px;")
        layout_geral.addWidget(header)

        workspace = QHBoxLayout()
        workspace.setSpacing(20)

        col_esquerda = QVBoxLayout()
        col_esquerda.setSpacing(12)

        lbl_nome = QLabel("Identificador da Ontologia (Nome do arquivo):")
        self.input_nome_arquivo = QLineEdit()
        self.input_nome_arquivo.setPlaceholderText("Ex: ontologia_dengue_medicina")

        lbl_texto = QLabel("Texto Médico de Entrada (Base de Conhecimento):")
        self.texto_entrada = QTextEdit()
        self.texto_entrada.setPlaceholderText("Cole aqui artigos científicos ou diretrizes clínicas para extração semântica...")


        self.btn_gerar = QPushButton("⚡  Processar Inteligência Semântica e Criar OWL")
        self.btn_gerar.setCursor(Qt.PointingHandCursor)
        self.btn_gerar.clicked.connect(self.processar_ontologia)


        col_esquerda.addWidget(lbl_nome)
        col_esquerda.addWidget(self.input_nome_arquivo)
        col_esquerda.addWidget(lbl_texto)
        col_esquerda.addWidget(self.texto_entrada)
        col_esquerda.addWidget(self.btn_gerar)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setEnabled(False)
        self.btn_cancelar.clicked.connect(self.cancelar)
        col_esquerda.addWidget(self.btn_cancelar)

        self.btn_abrir_protege = QPushButton("Abrir no Protégé")
        self.btn_abrir_protege.setEnabled(False)
        self.btn_abrir_protege.clicked.connect(self.abrir_protege_clicado)
        col_esquerda.addWidget(self.btn_abrir_protege)
        workspace.addLayout(col_esquerda, stretch=4)

        col_direita = QVBoxLayout()
        col_direita.setSpacing(8)

        lbl_log = QLabel("Console de Engenharia de Conhecimento:")
        self.texto_log = QTextEdit()
        self.texto_log.setReadOnly(True)
        self.texto_log.setStyleSheet("background-color: #0f172a; color: #38bdf8; font-family: 'Consolas', monospace; font-size: 12px; border: none; padding: 12px;")

        col_direita.addWidget(lbl_log)
        col_direita.addWidget(self.texto_log)
        workspace.addLayout(col_direita, stretch=3)

        layout_geral.addLayout(workspace)
        pagina.setLayout(layout_geral)

    def abrir_protege_clicado(self):
        try:
            abrir_no_protege(self.caminho_owl_gerado,
                             self.settings.caminho_protege())
        except OSError as e:
            QMessageBox.warning(self, "Protégé", str(e))

    def processar_ontologia(self):
        api_key = self.settings.api_key()
        texto = self.texto_entrada.toPlainText().strip()
        nome_arquivo = self.input_nome_arquivo.text().strip()
        uri_base = self.settings.uri_base()
        modelo_llm = self.settings.modelo()
        temp_llm = self.settings.temperatura()
        pasta_destino = self.settings.pasta_exportacao()

        if not texto or not nome_arquivo:
            QMessageBox.warning(self, "Erro", "Campos obrigatórios ausentes: Texto ou Nome do Arquivo.")
            return

        if self.em_execucao():
            return

        self.btn_abrir_protege.setEnabled(False)
        self.caminho_owl_gerado = ""
        self.texto_log.clear()
        self.texto_log.append("> [INIT] Inicializando ciclo de compilação semântica...")
        self._rodar(
            HybridEngine.gerar_ontologia,
            texto=texto, nome_arquivo=nome_arquivo, api_key=api_key,
            modelo_llm=modelo_llm, temp_llm=temp_llm, pasta_destino=pasta_destino,
            uri_base=uri_base,
            protege_exe=self.settings.caminho_protege(),
        )

    # ---- execução em segundo plano (PipelineRunnerMixin)
    MSG_CANCELADO = ("> [CANCELADO] Geração interrompida pelo usuário. As etapas já concluídas não são desfeitas; "
                     "confira a pasta de destino antes de usar algum arquivo.")

    def _log_widget(self):
        return self.texto_log

    def _run_button(self):
        return self.btn_gerar

    def _ao_concluir(self, resultado):
        caminho_saida = str(getattr(resultado, "path", "") or "")
        if caminho_saida and os.path.isfile(caminho_saida):
            self.caminho_owl_gerado = caminho_saida
            self.btn_abrir_protege.setEnabled(True)

        nivel, titulo, mensagem = completion_message(resultado)
        aviso = QMessageBox.information if nivel == "info" else QMessageBox.warning
        aviso(self, titulo, mensagem)
        self.texto_log.append(f"\n> [INFO] Processo finalizado (raciocinador: {resultado.reasoner.value}).")
