"""Página Sinônimos: agrupa conceitos equivalentes com Sentence-BERT."""
import os

from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from omaker.ontology.builder import add_equivalences
from omaker.paths import package_resource
from omaker.ui.workers import SynonymWorker


class SynonymsPage(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._montar()

    def _montar(self):
        pagina = self
        layout_geral = QVBoxLayout(pagina)
        layout_geral.setContentsMargins(25, 25, 25, 25)
        layout_geral.setSpacing(15)

        header = QLabel("Fusão Semântica de Sinônimos (SiMHOMer)")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #0f172a;")
        layout_geral.addWidget(header)

        workspace = QHBoxLayout()
        col_esquerda = QVBoxLayout()

        # 1. Seleção do arquivo .owl base
        card_arquivo = QFrame()
        card_arquivo.setObjectName("CardPane")
        layout_card = QVBoxLayout(card_arquivo)
        self.lbl_arquivo_sinonimos = QLabel("Ontologia selecionada: symp.owl")
        self.caminho_owl_sinonimos = str(package_resource("symp.owl"))
        btn_sel = QPushButton("📂 Selecionar Ontologia (.owl)")
        btn_sel.clicked.connect(self.selecionar_arquivo_owl_sinonimos)
        layout_card.addWidget(btn_sel)
        layout_card.addWidget(self.lbl_arquivo_sinonimos)
        col_esquerda.addWidget(card_arquivo)

        # 2. Entrada de Conceitos para Agrupar
        lbl_conceitos = QLabel("Conceitos Clínicos para Análise (separados por vírgula):")
        self.input_conceitos_sinonimos = QLineEdit("doença, enfermidade, patologia, carro, automóvel")
        col_esquerda.addWidget(lbl_conceitos)
        col_esquerda.addWidget(self.input_conceitos_sinonimos)

        # 3. Botão de Execução do Worker (Passo 1 + Passo 2)
        self.btn_rodar_sinonimos = QPushButton("🚀 Detectar Sinônimos")
        self.btn_rodar_sinonimos.setStyleSheet("background-color: #6366f1; color: white;")
        self.btn_rodar_sinonimos.clicked.connect(self.executar_worker_sinonimos)
        col_esquerda.addWidget(self.btn_rodar_sinonimos)

        # Console de Log Direito
        col_direita = QVBoxLayout()
        self.log_sinonimos = QTextEdit()
        self.log_sinonimos.setReadOnly(True)
        self.log_sinonimos.setStyleSheet("background-color: #0f172a; color: #a855f7; font-family: 'Consolas', monospace;")
        col_direita.addWidget(QLabel("Log do Processo de Agrupamento Semântico:"))
        col_direita.addWidget(self.log_sinonimos)

        workspace.addLayout(col_esquerda, stretch=4)
        workspace.addLayout(col_direita, stretch=3)
        layout_geral.addLayout(workspace)


    def executar_worker_sinonimos(self):
        caminho_onto = self.caminho_owl_sinonimos
        texto = self.input_conceitos_sinonimos.text()
        conceitos = [c.strip() for c in texto.split(",") if c.strip()]

        if not conceitos:
            QMessageBox.warning(self, "Aviso", "Insira pelo menos dois conceitos.")
            return

        self.btn_rodar_sinonimos.setEnabled(False)
        self.log_sinonimos.clear()

        # Dispara a Thread em segundo plano
        self.worker = SynonymWorker(caminho_onto, conceitos)
        self.worker.progresso.connect(lambda msg: self.log_sinonimos.append(f"> {msg}"))
        self.worker.concluido.connect(self.ao_concluir_sinonimos)
        self.worker.erro.connect(self.ao_falhar_sinonimos)
        self.worker.start()

    def ao_falhar_sinonimos(self, msg: str):
        self.btn_rodar_sinonimos.setEnabled(True)
        QMessageBox.critical(self, "Erro", msg)

    def ao_concluir_sinonimos(self, grupos, caminho_saida):
        self.btn_rodar_sinonimos.setEnabled(True)
        if not grupos:
            return
        lista = "\n".join(f"- {', '.join(termos)}" for termos in grupos.values())
        nome = os.path.splitext(os.path.basename(self.caminho_owl_sinonimos))[0]
        destino = os.path.join(self.settings.pasta_exportacao(), f"{nome}_sinonimos.owl")
        resposta = QMessageBox.question(
            self, "Gravar equivalências?",
            f"Grupos de sinônimos detectados:\n\n{lista}\n\n"
            f"Gravar como owl:equivalentClass numa cópia da ontologia?\n{destino}\n\n"
            "(o arquivo original não é alterado)")
        if resposta != QMessageBox.Yes:
            self.log_sinonimos.append("> Equivalências não gravadas (cancelado pelo usuário).")
            return
        try:
            relatorio = add_equivalences(self.caminho_owl_sinonimos, grupos, destino,
                                         log=lambda msg: self.log_sinonimos.append(msg))
        except Exception as e:  # noqa: BLE001  slot da GUI: mostra o erro ao usuário em vez de derrubar o app
            QMessageBox.critical(self, "Erro", f"Não foi possível gravar as equivalências:\n{e}")
            return
        texto = f"{relatorio.added} equivalência(s) gravada(s) em:\n{relatorio.path}"
        if relatorio.not_found:
            texto += "\n\nTermos sem classe correspondente na ontologia: " + ", ".join(relatorio.not_found)
        QMessageBox.information(self, "Equivalências gravadas", texto)

    def selecionar_arquivo_owl_sinonimos(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Selecione a Ontologia", "", "Ontologia OWL (*.owl)")
        if caminho:
            self.caminho_owl_sinonimos = caminho
            self.lbl_arquivo_sinonimos.setText(f"Ontologia selecionada: {caminho}")
