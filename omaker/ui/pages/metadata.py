"""Página de metadados (autor, URI base). Os valores são gravados pela SettingsPage."""

from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MetadataPage(QWidget):
    def __init__(self):
        super().__init__()
        self._montar()

    def _montar(self):
        pagina = self
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)

        header = QLabel("Metadados do Projeto W3C")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #0f172a; margin-bottom: 20px;")
        layout.addWidget(header)

        card = QFrame()
        card.setObjectName("CardPane")
        form_layout = QFormLayout(card)
        form_layout.setContentsMargins(25, 25, 25, 25)
        form_layout.setSpacing(15)

        self.input_autor = QLineEdit()
        self.input_uri = QLineEdit()

        form_layout.addRow(QLabel("Nome do Pesquisador Principal:"), self.input_autor)
        form_layout.addRow(QLabel("URI Base da Ontologia (Namespace):"), self.input_uri)
        # Dentro do seu método salvar_configuracoes(self):

        self.btn_salvar = QPushButton("💾  Salvar Metadados Estruturais")  # ligado à SettingsPage pelo OntoApp
        form_layout.addRow(self.btn_salvar)

        layout.addWidget(card)
        layout.addStretch()
        pagina.setLayout(layout)
