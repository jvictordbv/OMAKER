# omaker/ui/main_window.py
from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QWidget

# Imports modulares das dependências locais
import omaker.ui.recursos_rc  # noqa: F401  registra os recursos Qt (ícones); não remover
from omaker.ui.pages.about import AboutPage
from omaker.ui.pages.generator import GeneratorPage
from omaker.ui.pages.home import HomePage
from omaker.ui.pages.metadata import MetadataPage
from omaker.ui.pages.settings import SettingsPage
from omaker.ui.pages.synonyms import SynonymsPage
from omaker.ui.pages.updater import UpdaterPage


class OntoApp(QMainWindow):
    def __init__(self, configuracoes: QSettings | None = None):
        super().__init__()
        self.setWindowTitle("OMAKER • Engenharia de Ontologias Semânticas")
        self.resize(1180, 780)
        self.setWindowIcon(QIcon(":/icone_janela.png"))

        self._configuracoes = configuracoes  # None: QSettings do usuário (criado pela SettingsPage)
        self._fechando = False
        self.setup_ui()

    def setup_ui(self):
        widget_central = QWidget()
        layout_principal = QHBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)

        # --- BARRA LATERAL ---
        self.menu_lateral = QListWidget()
        self.menu_lateral.setFixedWidth(240)
        self.menu_lateral.addItems([
            "🏠  Início",
            "🧠  Gerador de Ontologia",
            "🔄  Atualizador (Mescla)",
            "🧬 Fusão de Sinônimos (SiMHOMer)",
            "📂  Metadados do Projeto",
            "⚙️  Configurações",
            "ℹ️  Sobre o OMAKER"
        ])
        self.menu_lateral.currentRowChanged.connect(self.mudar_pagina)
        layout_principal.addWidget(self.menu_lateral)

        # --- ÁREA DE CONTEÚDO ---
        self.area_conteudo = QStackedWidget()
        layout_principal.addWidget(self.area_conteudo)

        self.pagina_metadados = MetadataPage()
        self.pagina_configuracoes = SettingsPage(self.pagina_metadados, self._configuracoes)
        self.pagina_metadados.btn_salvar.clicked.connect(self.pagina_configuracoes.salvar_configuracoes)
        self.pagina_gerador = GeneratorPage(self.pagina_configuracoes)
        self.pagina_atualizador = UpdaterPage(self.pagina_configuracoes)
        self.pagina_sinonimos = SynonymsPage(self.pagina_configuracoes)
        for pagina in (HomePage(), self.pagina_gerador, self.pagina_atualizador, self.pagina_sinonimos,
                       self.pagina_metadados, self.pagina_configuracoes, AboutPage()):
            self.area_conteudo.addWidget(pagina)

        self.menu_lateral.setCurrentRow(0)

        # --- STYLESHEET ---
        self.setStyleSheet("""
            QMainWindow { background-color: #f8fafc; }
            QListWidget { font-size: 14px; background-color: #0f172a; color: #94a3b8; border: none; padding: 15px 10px; }
            QListWidget::item { padding: 12px 15px; border-radius: 8px; margin-bottom: 4px; }
            QListWidget::item:hover { background-color: #1e293b; color: #f8fafc; }
            QListWidget::item:selected { background-color: #312e81; color: #e0e7ff; font-weight: bold; }
            QLabel { font-size: 13px; color: #334155; font-weight: 500; }
            QLineEdit, QTextEdit, QComboBox { background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; font-size: 13px; }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #4f46e5; }
            QPushButton { background-color: #4f46e5; color: white; padding: 11px; border-radius: 6px; font-size: 13px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #4338ca; }
            QFrame#CardPane { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }
        """)

    def mudar_pagina(self, index): self.area_conteudo.setCurrentIndex(index)

    def closeEvent(self, event):  # noqa: N802  nome exigido pelo Qt
        """Fechar durante uma execução não bloqueia a interface: pede o cancelamento, recusa o fechamento
        e fecha sozinha quando a thread terminar (uma chamada ao Ollama ou ao HermiT pode levar minutos).
        Sem isso, o Python encerraria com a thread ainda rodando."""
        rodando = [p for p in (self.pagina_gerador, self.pagina_atualizador) if p.worker is not None]
        sinonimos = self.pagina_sinonimos.worker
        sinonimos_rodando = sinonimos is not None and sinonimos.isRunning()
        if not rodando and not sinonimos_rodando:
            super().closeEvent(event)
            return
        event.ignore()
        if self._fechando:
            return
        self._fechando = True
        self.setWindowTitle("OMAKER • Cancelando... a janela fecha ao fim da etapa atual")
        for pagina in rodando:
            pagina.silencioso = True          # sem caixas de diálogo depois do pedido de fechar
            pagina.cancelar()
            pagina.worker.finished.connect(self.close)   # depois de _finalizar, que zera o worker
        if sinonimos_rodando:                 # sem cancelamento: espera o agrupamento terminar
            self.pagina_sinonimos.silencioso = True
            sinonimos.finished.connect(self.close)
