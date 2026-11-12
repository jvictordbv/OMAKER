"""Página de configurações e o QSettings do programa, com leitores para as outras páginas."""
import os

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from omaker.ontology.iri import DEFAULT_URI_BASE


def default_settings() -> QSettings:
    """As configurações do usuário (registro do Windows). Os testes trocam esta função por um .ini temporário."""
    return QSettings("MeuMestrado", "OntoGenApp")


class SettingsPage(QWidget):
    def __init__(self, metadados, configuracoes: QSettings | None = None):
        super().__init__()
        self.metadados = metadados
        self.configuracoes = configuracoes if configuracoes is not None else default_settings()
        self._montar()
        self.carregar_configuracoes()

    def _montar(self):
        pagina = self
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)

        header = QLabel("Configurações Avançadas do Sistema")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #0f172a; margin-bottom: 20px;")
        layout.addWidget(header)

        card = QFrame()
        card.setObjectName("CardPane")
        form_layout = QFormLayout(card)
        form_layout.setContentsMargins(25, 25, 25, 25)
        form_layout.setSpacing(18)

        layout_inputs_modelo = QHBoxLayout()
        self.combo_modelo = QComboBox()
        self.input_novo_modelo = QLineEdit()
        self.input_novo_modelo.setPlaceholderText("Digitar ID de novo modelo...")

        btn_add_modelo = QPushButton("➕")
        btn_add_modelo.setFixedWidth(45)
        btn_add_modelo.clicked.connect(self.adicionar_modelo_customizado)

        layout_inputs_modelo.addWidget(self.combo_modelo, stretch=2)
        layout_inputs_modelo.addWidget(self.input_novo_modelo, stretch=3)
        layout_inputs_modelo.addWidget(btn_add_modelo)
        form_layout.addRow(QLabel("Modelo LLM de Processamento:"), layout_inputs_modelo)

        layout_temp = QHBoxLayout()
        self.slider_temp = QSlider(Qt.Horizontal)
        self.slider_temp.setRange(0, 100)
        self.slider_temp.setValue(10)
        self.lbl_valor_temp = QLabel("0.1")
        self.lbl_valor_temp.setFixedWidth(30)
        self.slider_temp.valueChanged.connect(lambda v: self.lbl_valor_temp.setText(f"{v/100:.2f}"))
        layout_temp.addWidget(self.slider_temp)
        layout_temp.addWidget(self.lbl_valor_temp)
        form_layout.addRow(QLabel("Temperatura (Criatividade vs Rigor):"), layout_temp)

        layout_dir = QHBoxLayout()
        self.input_diretorio = QLineEdit()
        self.input_diretorio.setReadOnly(True)
        btn_procurar_dir = QPushButton("📂")
        btn_procurar_dir.setFixedWidth(40)
        btn_procurar_dir.clicked.connect(self.escolher_diretorio_padrao)
        layout_dir.addWidget(self.input_diretorio)
        layout_dir.addWidget(btn_procurar_dir)
        form_layout.addRow(QLabel("Pasta de Destino dos Arquivos OWL:"), layout_dir)

        # --- NOVO: CAMINHO DO EXECUTÁVEL DO PROTÉGÉ ---
        layout_protege = QHBoxLayout()
        self.input_protege = QLineEdit()
        self.input_protege.setPlaceholderText("Ex: C:\\Program Files\\Protege-5.6.4\\Protege.exe")
        btn_procurar_protege = QPushButton("🔍")
        btn_procurar_protege.setFixedWidth(40)
        btn_procurar_protege.clicked.connect(self.escolher_executavel_protege)
        layout_protege.addWidget(self.input_protege)
        layout_protege.addWidget(btn_procurar_protege)
        form_layout.addRow(QLabel("Executável do Protégé (.exe):"), layout_protege)
        # ----------------------------------------------

        btn_salvar = QPushButton("💾  Gravar Todas as Configurações")
        btn_salvar.clicked.connect(self.salvar_configuracoes)
        form_layout.addRow(btn_salvar)

        layout.addWidget(card)
        layout.addStretch()
        pagina.setLayout(layout)

    def escolher_executavel_protege(self):
        # Abre a janela do Windows já filtrando para encontrar o executável mais facilmente
        caminho, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Executável do Protégé",
            "",
            "Executáveis (*.exe);;Todos os Arquivos (*)"
        )
        if caminho:
            self.input_protege.setText(caminho)

    def escolher_diretorio_padrao(self):
        diretorio = QFileDialog.getExistingDirectory(self, "Selecione a Pasta de Exportação")
        if diretorio:
            self.input_diretorio.setText(diretorio)

    def adicionar_modelo_customizado(self):
        novo_modelo = self.input_novo_modelo.text().strip()
        if not novo_modelo:
            return
        if self.combo_modelo.findText(novo_modelo) == -1:
            self.combo_modelo.addItem(novo_modelo)
            self.combo_modelo.setCurrentText(novo_modelo)
            self.input_novo_modelo.clear()

    def salvar_configuracoes(self):
        self.configuracoes.remove("api_key")   # sobra da versão com Gemini; o motor local não usa chave
        self.configuracoes.setValue("autor", self.metadados.input_autor.text().strip())
        self.configuracoes.setValue("uri_base", self.metadados.input_uri.text().strip())
        self.configuracoes.setValue("temperatura", self.slider_temp.value())
        self.configuracoes.setValue("diretorio_exportacao", self.input_diretorio.text().strip())

        # --- SALVANDO O CAMINHO DO PROTÉGÉ ---
        self.configuracoes.setValue("caminho_protege", self.input_protege.text().strip().strip('"'))
        # -------------------------------------

        self.configuracoes.setValue("modelo", self.combo_modelo.currentText())
        lista_modelos = [self.combo_modelo.itemText(i) for i in range(self.combo_modelo.count())]
        self.configuracoes.setValue("lista_modelos_disponiveis", lista_modelos)

        QMessageBox.information(self, "Sucesso", "Configurações persistidas localmente no sistema!")

    def carregar_configuracoes(self):
        self.metadados.input_autor.setText(self.configuracoes.value("autor", ""))
        self.metadados.input_uri.setText(self.configuracoes.value("uri_base", "") or DEFAULT_URI_BASE)
        self.input_diretorio.setText(self.configuracoes.value("diretorio_exportacao", os.path.abspath(".")))

        # --- CARREGA O CAMINHO DO PROTÉGÉ ---
        self.input_protege.setText(self.configuracoes.value("caminho_protege", ""))
        # ------------------------------------

        temp_salva = int(self.configuracoes.value("temperatura", 10))
        self.slider_temp.setValue(temp_salva)
        self.lbl_valor_temp.setText(f"{temp_salva/100:.2f}")

        modelos_padrao = ["qwen3:8b"]
        lista_modelos = self.configuracoes.value("lista_modelos_disponiveis", modelos_padrao)
        # Modelos do Gemini gravados por versões antigas não rodam no Ollama.
        lista_modelos = [m for m in lista_modelos if not m.lower().startswith("gemini")] or modelos_padrao
        self.combo_modelo.clear()
        self.combo_modelo.addItems(lista_modelos)

        modelo_salvo = self.configuracoes.value("modelo", "qwen3:8b")
        index_modelo = self.combo_modelo.findText(modelo_salvo)
        if index_modelo >= 0:
            self.combo_modelo.setCurrentIndex(index_modelo)

    # ---- leitores usados pelas páginas de trabalho
    def uri_base(self) -> str:
        return self.configuracoes.value("uri_base", "") or DEFAULT_URI_BASE

    def modelo(self) -> str:
        return self.combo_modelo.currentText()

    def temperatura(self) -> float:
        return self.slider_temp.value() / 100

    def pasta_exportacao(self) -> str:
        return self.input_diretorio.text()

    def caminho_protege(self) -> str:
        return self.configuracoes.value("caminho_protege", "")
