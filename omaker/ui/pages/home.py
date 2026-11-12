"""Página inicial."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)


class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        self._montar()

    def _montar(self):
        pagina = self
        layout_centralizado = QVBoxLayout()
        layout_centralizado.setAlignment(Qt.AlignCenter)
        layout_centralizado.setSpacing(15)

        self.lbl_logo = QLabel()
        pixmap = QPixmap(":/logo_home.png")
        if not pixmap.isNull():
            pixmap_redimensionado = pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_logo.setPixmap(pixmap_redimensionado)
        else:
            self.lbl_logo.setText("[ LOGO OMAKER ]")
            self.lbl_logo.setStyleSheet("font-size: 18px; font-weight: bold; color: #64748b;")

        self.lbl_logo.setAlignment(Qt.AlignCenter)

        lbl_welcome = QLabel("Bem-vindo ao OMAKER\nAmbiente Inteligente de Engenharia e Mapeamento de Ontologias.")
        lbl_welcome.setStyleSheet("font-size: 15px; color: #475569; font-weight: bold; line-height: 1.5; margin-top: 10px;")
        lbl_welcome.setAlignment(Qt.AlignCenter)

        layout_centralizado.addStretch()
        layout_centralizado.addWidget(self.lbl_logo, alignment=Qt.AlignCenter)
        layout_centralizado.addWidget(lbl_welcome)
        layout_centralizado.addStretch()

        pagina.setLayout(layout_centralizado)
