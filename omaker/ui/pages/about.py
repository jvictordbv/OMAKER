"""Página Sobre."""

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        self._montar()

    def _montar(self):
        pagina = self
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

    # --- MÉTODOS AUXILIARES E CHANCE DE COMPORTAMENTO DA UI ---
