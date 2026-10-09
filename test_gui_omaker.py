import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QTextEdit, QLabel, QLineEdit, QProgressBar)
from core.worker import SynonymWorker

class OMAKERWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OMAKER - Módulo de Fusão de Ontologias (SiMHOMer)")
        self.setGeometry(200, 200, 700, 500)

        # Layout Principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 1. Campo de Seleção da Ontologia
        layout.addWidget(QLabel("<b>Caminho da Ontologia (.owl):</b>"))
        self.input_onto = QLineEdit("symp.owl")
        layout.addWidget(self.input_onto)

        # 2. Campo de Conceitos para Analisar
        layout.addWidget(QLabel("<b>Conceitos para Agrupar (separados por vírgula):</b>"))
        self.input_conceitos = QLineEdit("doença, enfermidade, patologia, carro, automóvel")
        layout.addWidget(self.input_conceitos)

        # 3. Botão de Ação
        self.btn_processar = QPushButton("🚀 Detectar Sinônimos & Injetar Axiomas (ML)")
        self.btn_processar.setStyleSheet("font-weight: bold; padding: 10px; background-color: #0d6efd; color: white;")
        self.btn_processar.clicked.connect(self.iniciar_processamento)
        layout.addWidget(self.btn_processar)

        # 4. Status e Barra de Progresso
        self.lbl_status = QLabel("Status: Aguardando início...")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) 
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # 5. Área de Exibição dos Resultados
        layout.addWidget(QLabel("<b>Log de Saída e Axiomas Gerados:</b>"))
        self.txt_resultado = QTextEdit()
        self.txt_resultado.setReadOnly(True)
        layout.addWidget(self.txt_resultado)

    def iniciar_processamento(self):
        caminho_onto = self.input_onto.text().strip()
        texto_conceitos = self.input_conceitos.text()
        lista_conceitos = [c.strip() for c in texto_conceitos.split(",") if c.strip()]

        if not lista_conceitos:
            self.lbl_status.setText("Erro: Insira ao menos dois conceitos para analisar.")
            return

        # Prepara a Interface para o Carregamento
        self.btn_processar.setEnabled(False)
        self.progress_bar.show()
        self.txt_resultado.clear()

        # Instancia e Inicia a Thread em Segundo Plano
        self.worker = SynonymWorker(caminho_onto, lista_conceitos, threshold=0.25)
        self.worker.progresso.connect(self.atualizar_status)
        self.worker.concluido.connect(self.processamento_finalizado)
        self.worker.erro.connect(self.exibir_erro)
        self.worker.start()

    def atualizar_status(self, mensagem):
        self.lbl_status.setText(f"Status: {mensagem}")
        self.txt_resultado.append(f"ℹ️ {mensagem}")

    def processamento_finalizado(self, grupos, caminho_salvo):
        self.progress_bar.hide()
        self.btn_processar.setEnabled(True)

        if grupos:
            self.txt_resultado.append("\n<b>=== GRUPOS DE SINÔNIMOS IDENTIFICADOS ===</b>")
            for gid, termos in grupos.items():
                self.txt_resultado.append(f"• Grupo {gid + 1}: {', '.join(termos)}")

            self.txt_resultado.append(f"\n<b> AXIOMAS INJETADOS COM SUCESSO!</b>")
            self.txt_resultado.append(f"Arquivo salvo em: <i>{caminho_salvo}</i>")

    def exibir_erro(self, mensagem_erro):
        self.progress_bar.hide()
        self.btn_processar.setEnabled(True)
        self.lbl_status.setText("Erro no processamento!")
        self.txt_resultado.append(f"\n❌ {mensagem_erro}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = OMAKERWindow()
    janela.show()
    sys.exit(app.exec())
