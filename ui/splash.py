# ui/splash.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGraphicsDropShadowEffect, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QLinearGradient, QPen

class GlowShimmerLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._shimmer_pos = -1.0  
        self.shimmer_timer = QTimer(self)
        self.shimmer_timer.timeout.connect(self.animar_shimmer)
        self.shimmer_timer.start(15) 

    def animar_shimmer(self):
        self._shimmer_pos += 0.008  
        if self._shimmer_pos > 2.5:  
            self._shimmer_pos = -1.5 
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(max(0.0, min(1.0, self._shimmer_pos - 0.5)), QColor("#ffffff"))
        gradient.setColorAt(max(0.0, min(1.0, self._shimmer_pos)), QColor("#0736c3")) 
        gradient.setColorAt(max(0.0, min(1.0, self._shimmer_pos + 0.5)), QColor("#ffffff"))
        painter.setFont(self.font())
        painter.setPen(QColor(0,0,0,0)) 
        painter.setBrush(gradient)
        rect = self.rect()
        painter.setPen(Qt.NoPen)
        gradient_pen = QPen(gradient, 0)
        painter.setPen(gradient_pen)
        painter.drawText(rect, Qt.AlignCenter, self.text())
        painter.end()


class OperaGXSplash(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window 
        self.setWindowFlags(Qt.WindowFlags.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(550, 350)
        
        tela = QApplication.primaryScreen().geometry()
        self.move((tela.width() - self.width()) // 2, (tela.height() - self.height()) // 2)
        self.setup_ui()
        self.iniciar_animacoes()

    def setup_ui(self):
        layout_externo = QVBoxLayout(self)
        layout_externo.setContentsMargins(15, 15, 15, 15)

        self.container = QWidget()
        self.container.setStyleSheet("background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 16px;")
        layout_interno = QVBoxLayout(self.container)
        layout_interno.setAlignment(Qt.AlignCenter)
        layout_interno.setSpacing(10)

        self.lbl_titulo = GlowShimmerLabel("OMAKER")
        self.lbl_titulo.setAlignment(Qt.AlignCenter)
        font = QFont("Inter", 56, QFont.Black)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 6)
        self.lbl_titulo.setFont(font)
        self.lbl_titulo.setFixedHeight(90)
        
        self.efeito_glow = QGraphicsDropShadowEffect()
        self.efeito_glow.setBlurRadius(35)
        self.efeito_glow.setColor(QColor(6, 182, 212, 180)) 
        self.efeito_glow.setOffset(0, 0)
        self.lbl_titulo.setGraphicsEffect(self.efeito_glow)

        self.lbl_status = QLabel("INICIALIZANDO CORE SEMÂNTICO...")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold; letter-spacing: 2px; margin-top: 15px; background: transparent;")

        self.barra_progresso = QProgressBar()
        self.barra_progresso.setFixedHeight(4)
        self.barra_progresso.setTextVisible(False)
        self.barra_progresso.setStyleSheet("""
            QProgressBar { background-color: #1e293b; border-radius: 2px; border: none; max-width: 300px; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #06b6d4); border-radius: 2px; }
        """)

        layout_interno.addStretch()
        layout_interno.addWidget(self.lbl_titulo)
        layout_interno.addWidget(self.lbl_status)
        layout_interno.addSpacing(15)
        layout_interno.addWidget(self.barra_progresso, alignment=Qt.AlignCenter)
        layout_interno.addStretch()
        layout_externo.addWidget(self.container)

    def iniciar_animacoes(self):
        self.valor_progresso = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.atualizar_carregamento)
        self.timer.start(20) 

    def atualizar_carregamento(self):
        self.valor_progresso += 1
        self.barra_progresso.setValue(self.valor_progresso)

        if self.valor_progresso == 25:
            self.lbl_status.setText("CARREGANDO DIRETRIZES DE SEGURANÇA...")
        elif self.valor_progresso == 55:
            self.lbl_status.setText("CONSTRUINDO FRAMEWORK OWLREADY2...")
        elif self.valor_progresso == 80:
            self.lbl_status.setText("MODO TURBO")

        if self.valor_progresso >= 100:
            self.timer.stop()
            self.main_window.show() 
            self.close()