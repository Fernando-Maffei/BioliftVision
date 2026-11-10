from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QRadioButton, QDialogButtonBox, QHBoxLayout, QWidget, QFrame, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from ui.style import get_button_style 
import os
class SettingsDialog(QDialog):
    def __init__(self, current_theme: str = "AuroraDark", on_apply=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.setModal(True)
        # Define tamanho compacto similar à tela de login
        self.setGeometry(400, 200, 500, 400)
        self.setFixedSize(500, 400)
        self.current_theme = current_theme or "AuroraDark"
        self.on_apply = on_apply
        self._build_ui()

    def _build_ui(self):
        # Layout principal compacto
        outer = QVBoxLayout(self)
        outer.setContentsMargins(15, 15, 15, 15)
        outer.setSpacing(12)

        # Card centralizado compacto
        card = QFrame()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card.setMaximumWidth(450)

        # Efeito de sombra sutil para destacar o card
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 100))
        card.setGraphicsEffect(shadow)

        # Título principal
        title = QLabel("⚙️ Configurações")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("Personalize as preferências do sistema")
        subtitle.setAlignment(Qt.AlignCenter)
        # Deixar cor a cargo do tema global
        subtitle.setStyleSheet("font-size: 12px;")
        card_layout.addWidget(subtitle)

        # Seção de tema
        theme_section = QFrame()
        theme_section_layout = QVBoxLayout(theme_section)
        theme_section_layout.setSpacing(8)
        theme_section_layout.setContentsMargins(12, 12, 12, 12)

        theme_title = QLabel("Aparência")
        # Deixar cor a cargo do tema global
        theme_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        theme_section_layout.addWidget(theme_title)

        # Alternância de tema
        theme_box = QWidget()
        theme_layout = QHBoxLayout(theme_box)
        theme_layout.setContentsMargins(0, 0, 0, 0)
        theme_layout.setSpacing(16)

        self.dark_radio = QRadioButton("🌙 Tema Escuro")
        self.dark_radio.setChecked(True)
        

        theme_layout.addWidget(self.dark_radio)
        theme_layout.addStretch()
        
        theme_section_layout.addWidget(theme_box)
        card_layout.addWidget(theme_section)

        # Botões
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        
        # Estilizar botões
        save_btn = buttons.button(QDialogButtonBox.Save)
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        # Escala responsiva
        try:
            scale = float(os.environ.get('POWERLIFT_UI_SCALE', '0.90'))
            scale = max(0.75, min(1.0, scale))
        except Exception:
            scale = 0.90
        btn_w_primary = int(160 * scale)
        btn_w_secondary = int(140 * scale)
        btn_h = int(46 * scale)

        if save_btn:
            save_btn.setText("Salvar")
            save_btn.setObjectName("primary")
            save_btn.setMinimumHeight(btn_h)
            save_btn.setFixedWidth(btn_w_primary)
            save_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if cancel_btn:
            cancel_btn.setText("Cancelar")
            cancel_btn.setObjectName("secondary")
            cancel_btn.setMinimumHeight(btn_h)
            cancel_btn.setFixedWidth(btn_w_secondary)
            cancel_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            
        card_layout.addWidget(buttons, alignment=Qt.AlignCenter)

        # Adicionar card ao layout principal
        outer.addStretch(1)
        outer.addWidget(card, alignment=Qt.AlignCenter)
        outer.addStretch(1)

    def _apply(self):
        theme = "AuroraDark"
        if callable(self.on_apply):
            self.on_apply(theme)
        self.accept()
