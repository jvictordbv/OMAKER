# ui/main_window.py
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTextEdit, QPushButton, QLineEdit, QMessageBox, 
                               QStackedWidget, QListWidget, QFormLayout, QFrame, 
                               QComboBox, QSlider, QFileDialog, QApplication)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont, QIcon, QPixmap

# Imports modulares das dependências locais
import ui.recursos_rc as recursos_rc
from core.semantic_engine import SemanticEngine

from PySide6.QtWidgets import QMessageBox # (ou PyQt6, dependendo de qual usa)
import subprocess
import os

class OntoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OMAKER • Engenharia de Ontologias Semânticas")
        self.resize(1180, 780) 
        self.setWindowIcon(QIcon(":/icone_janela.png"))
        
        self.configuracoes = QSettings("MeuMestrado", "OntoGenApp")
        self.setup_ui()
        self.carregar_configuracoes()

    
    def abrir_no_protege(self, caminho_owl, protege_exe, log_callback):
        pass
        """
        import os
        import subprocess

        if not protege_exe or not os.path.exists(protege_exe):
            log_callback(f"\n> [ERRO] Executável do Protégé não encontrado em: '{protege_exe}'")
            log_callback("> [DICA] Vá na aba de Configurações e aponte para o local correto do seu Protege.exe.")
            return False

        try:
            log_callback(f"\n> [PROTÉGÉ] Inicializando e forçando janela para o primeiro plano...")
            
            # Normaliza os caminhos para o padrão do Windows (barras invertidas)
            protege_exe = os.path.normpath(protege_exe)
            caminho_owl = os.path.normpath(caminho_owl)
            
            # O comando 'start "" "caminho"' faz o Windows gerenciar o foco da nova GUI.
            # Roda em segundo plano sem travar o OMAKER, mas joga o Protégé na frente!
            comando = f'start "" "{protege_exe}" "{caminho_owl}"'
            subprocess.Popen(comando, shell=True)
            
            log_callback("> [PROTÉGÉ] Instância aberta com foco total!")
            return True
        except Exception as e:
            log_callback(f"> [ERRO] Falha ao iniciar o subprocesso do Protégé: {e}")
            return False"""

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
            "📂  Metadados do Projeto", 
            "⚙️  Configurações",
            "ℹ️  Sobre o OMAKER"
        ])
        self.menu_lateral.currentRowChanged.connect(self.mudar_pagina)
        layout_principal.addWidget(self.menu_lateral)

        # --- ÁREA DE CONTEÚDO ---
        self.area_conteudo = QStackedWidget()
        layout_principal.addWidget(self.area_conteudo)

        self.criar_pagina_home()
        self.criar_pagina_gerador()
        self.criar_pagina_atualizador()
        self.criar_pagina_metadados()
        self.criar_pagina_configuracoes()
        self.criar_pagina_sobre()

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

    def criar_pagina_home(self):
        pagina = QWidget()
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
        self.area_conteudo.addWidget(pagina)

    def criar_pagina_gerador(self):
        pagina = QWidget()
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
        self.area_conteudo.addWidget(pagina)
    
    def criar_pagina_atualizador(self):
        pagina = QWidget()
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
        self.area_conteudo.addWidget(pagina)

    def criar_pagina_metadados(self):
        pagina = QWidget()
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
        
        btn = QPushButton("💾  Salvar Metadados Estruturais")
        btn.clicked.connect(self.salvar_configuracoes)
        form_layout.addRow(btn)

        layout.addWidget(card)
        layout.addStretch()
        pagina.setLayout(layout)
        self.area_conteudo.addWidget(pagina)

    def criar_pagina_configuracoes(self):
        pagina = QWidget()
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

        self.input_api = QLineEdit()
        self.input_api.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_api.setPlaceholderText("Cole sua AI_API_KEY do Google AI Studio...")
        form_layout.addRow(QLabel("Chave de Autenticação API Gemini:"), self.input_api)

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
        self.area_conteudo.addWidget(pagina)
    
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

    def criar_pagina_sobre(self): 
        pagina = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header = QLabel("Sobre o OMAKER")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #0f172a;")
        layout.addWidget(header)

        card = QFrame()
        card.setObjectName("CardPane")
        card.setStyleSheet("background-color: #0f172a; border-radius: 12px; border: 1px solid #1e293b;")
        layout_card = QVBoxLayout(card)
        layout_card.setContentsMargins(30, 30, 30, 30)
        layout_card.setSpacing(12)

        lbl_nome_app = QLabel("OMAKER v1.0.0")
        lbl_nome_app.setStyleSheet("color: #06b6d4; font-size: 24px; font-weight: 900; letter-spacing: 1px;")
        
        lbl_desc = QLabel("<b>OMAKER</b> (Ontology Mapping & Knowledge Engineering Resource) é um ambiente computacional "
                          "inteligente projetado para automatizar a modelagem e extração de ontologias formais. "
                          "O sistema otimiza o fluxo de trabalho do pesquisador ao converter bases de conhecimento textuais "
                          "em axiomas estruturados in Lógica de Descrição (DL), utilizando Large Language Models (LLMs) "
                          "em estrita conformidade com as diretrizes de padronização do W3C.")
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.6;")
        lbl_desc.setWordWrap(True)

        linha_divisora = QFrame()
        linha_divisora.setFrameShape(QFrame.HLine)
        linha_divisora.setStyleSheet("background-color: #1e293b; max-height: 1px; margin: 8px 0;")

        lbl_creditos = QLabel(
            "🏛️ <b>CRÉDITOS ACADÊMICOS</b><br>"
            "<b>Desenvolvedor Principal:</b> João Victor Ferreira Barbosa<br>"
            "<b>Instituição:</b> Universidade Federal de Pernambuco(UFPE)<br>"
            "<b>Orientação Acadêmica:</b> Prof. Dr. Fred Freitas / Prof. Dr. Rinaldo Lima<br><br>"
            "<b>Agradecimentos:<b> Aos meus companheiros de turma, que a todo momento"
            "me auxiliaram e não me permitiram desistir. <br><br> "
            "📬 <b>CONTATO & SUPORTE</b><br>"
            "<b>E-mail Profissional:</b> jvfb@cin.ufpe.br<br>"
            "<b>Lattes:</b> http://lattes.cnpq.br/6935490007251779<br>"
            "<b>Instagram:</b> @J.VictorDBV"
        )
        lbl_creditos.setStyleSheet("color: #cbd5e1; font-size: 13px; line-height: 1.8;")
        layout_card.addWidget(lbl_nome_app)
        layout_card.addWidget(lbl_desc)
        layout_card.addWidget(linha_divisora)
        layout_card.addWidget(lbl_creditos)

        layout.addWidget(card)
        layout.addStretch()
        pagina.setLayout(layout)
        self.area_conteudo.addWidget(pagina)

    # --- MÉTODOS AUXILIARES E CHANCE DE COMPORTAMENTO DA UI ---
    def escolher_diretorio_padrao(self):
        diretorio = QFileDialog.getExistingDirectory(self, "Selecione a Pasta de Exportação")
        if diretorio: self.input_diretorio.setText(diretorio)
            
    def adicionar_modelo_customizado(self):
        novo_modelo = self.input_novo_modelo.text().strip()
        if not novo_modelo: return
        if self.combo_modelo.findText(novo_modelo) == -1:
            self.combo_modelo.addItem(novo_modelo)
            self.combo_modelo.setCurrentText(novo_modelo)
            self.input_novo_modelo.clear()

    def selecionar_arquivo_owl(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Selecione a Ontologia", "", "Ontologia OWL (*.owl)")
        if caminho:
            self.caminho_owl_atual = caminho
            self.lbl_arquivo_selecionado.setText(caminho)

    def mudar_pagina(self, index): self.area_conteudo.setCurrentIndex(index)

    def salvar_configuracoes(self):
        self.configuracoes.setValue("api_key", self.input_api.text().strip())
        self.configuracoes.setValue("autor", self.input_autor.text().strip())
        self.configuracoes.setValue("uri_base", self.input_uri.text().strip())
        self.configuracoes.setValue("temperatura", self.slider_temp.value())
        self.configuracoes.setValue("diretorio_exportacao", self.input_diretorio.text().strip())
        
        # --- SALVANDO O CAMINHO DO PROTÉGÉ ---
        self.configuracoes.setValue("caminho_protege", self.input_protege.text().strip())
        # -------------------------------------
        
        self.configuracoes.setValue("modelo", self.combo_modelo.currentText())
        lista_modelos = [self.combo_modelo.itemText(i) for i in range(self.combo_modelo.count())]
        self.configuracoes.setValue("lista_modelos_disponiveis", lista_modelos)
        
        QMessageBox.information(self, "Sucesso", "Configurações persistidas localmente no sistema!")
    
    def carregar_configuracoes(self):
        self.input_api.setText(self.configuracoes.value("api_key", ""))
        self.input_autor.setText(self.configuracoes.value("autor", ""))
        self.input_uri.setText(self.configuracoes.value("uri_base", "http://www.mestrado.edu/ontologias/"))
        self.input_diretorio.setText(self.configuracoes.value("diretorio_exportacao", os.path.abspath(".")))
        
        # --- CARREGA O CAMINHO DO PROTÉGÉ ---
        # Usa o caminho padrão do Windows como fallback caso seja a primeira vez abrindo o app
        caminho_padrao = r"C:\Program Files\Protege-5.6.4\Protege.exe"
        self.input_protege.setText(self.configuracoes.value("caminho_protege", caminho_padrao))
        # ------------------------------------

        temp_salva = int(self.configuracoes.value("temperatura", 10))
        self.slider_temp.setValue(temp_salva)
        self.lbl_valor_temp.setText(f"{temp_salva/100:.2f}")
        
        modelos_padrao = ["gemini-2.5-flash", "gemini-2.5-pro"]
        lista_modelos = self.configuracoes.value("lista_modelos_disponiveis", modelos_padrao)
        self.combo_modelo.clear()
        self.combo_modelo.addItems(lista_modelos)
        
        modelo_salvo = self.configuracoes.value("modelo", "gemini-2.5-flash")
        index_modelo = self.combo_modelo.findText(modelo_salvo)
        if index_modelo >= 0: self.combo_modelo.setCurrentIndex(index_modelo)

    def processar_ontologia(self):
        api_key = self.configuracoes.value("api_key", "")
        texto = self.texto_entrada.toPlainText().strip()
        nome_arquivo = self.input_nome_arquivo.text().strip()
        uri_base = self.configuracoes.value("uri_base", "http://www.mestrado.edu/ontologias/")
        modelo_llm = self.combo_modelo.currentText()
        temp_llm = float(self.slider_temp.value() / 100)
        pasta_destino = self.input_diretorio.text()

        if not api_key or not texto or not nome_arquivo:
            QMessageBox.warning(self, "Erro", "Campos obrigatórios ausentes: Chave API, Texto ou Nome do Arquivo.")
            return

        self.btn_gerar.setEnabled(False)
        self.texto_log.clear()
        self.texto_log.append("> [INIT] Inicializando ciclo de compilação semântica...")
        QApplication.processEvents()

        try:
            # Encaminha o processamento pesado para o Core separado
            path_gerado = SemanticEngine.gerar_ontologia(
                texto=texto, nome_arquivo=nome_arquivo, api_key=api_key,
                modelo_llm=modelo_llm, temp_llm=temp_llm, pasta_destino=pasta_destino,
                uri_base=uri_base,
                log_callback=lambda msg: [self.texto_log.append(msg), QApplication.processEvents()]
            )
            
            # --- AVISO SIMPLES DE SUCESSO ---
            if path_gerado:
                QMessageBox.information(
                    self, 
                    "Ontologia Concluída!", 
                    f"Grafo gerado e auditado com sucesso!\n\nArquivo salvo em: {path_gerado}"
                )
                self.texto_log.append(f"\n> [INFO] Processo finalizado com sucesso.")

        except Exception as e:
            self.texto_log.append(f"\n> [CRITICAL ERROR] {str(e)}")
            QMessageBox.critical(self, "Erro", str(e))
        finally:
            self.btn_gerar.setEnabled(True)

    def atualizar_ontologia_existente(self):
        if not hasattr(self, 'caminho_owl_atual') or not self.caminho_owl_atual:
            QMessageBox.warning(self, "Aviso", "Selecione um arquivo .owl primeiro.")
            return
            
        texto = self.texto_entrada_atualizador.toPlainText().strip()
        api_key = self.configuracoes.value("api_key", "")
        
        if not texto or not api_key: 
            QMessageBox.warning(self, "Aviso", "Preencha o texto e configure a chave de API.")
            return

        # Prepara a interface para o processamento
        self.btn_atualizar.setEnabled(False)
        self.log_atualizador.clear()
        QApplication.processEvents()

        try:
            # --- MANTÉM O PROCESSAMENTO (O Core precisa rodar!) ---
            sucesso = SemanticEngine.atualizar_ontologia(
                caminho_owl=self.caminho_owl_atual, 
                texto=texto, 
                api_key=api_key,
                log_callback=lambda msg: [self.log_atualizador.append(msg), QApplication.processEvents()]
            )
            
            # --- AVISO SIMPLES DE SUCESSO (Protégé removido daqui) ---
            if sucesso:
                # Apenas avisa que deu certo e limpa o fluxo
                QMessageBox.information(
                    self, 
                    "Atualização Concluída!", 
                    "Novos axiomas mesclados e auditados pelo HermiT com sucesso!"
                )
                self.log_atualizador.append("\n> [INFO] Atualização gravada. Grafo pronto para o uso.")
            else:
                self.log_atualizador.append("\n> [ERRO] A atualização falhou no núcleo semântico. Verifique os logs acima.")

        except Exception as e:
            self.log_atualizador.append(f"\n> [CRITICAL ERROR] {str(e)}")
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro crítico:\n{str(e)}")
            
        finally:
            self.btn_atualizar.setEnabled(True)
            
import subprocess
import os

