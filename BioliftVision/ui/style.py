import os

# Paleta padrão (será sobrescrita por apply_theme)
PRIMARY_COLOR = "#38BDF8"
PRIMARY_HOVER = "#2CA3D9"
PRIMARY_ACTIVE = "#1F84AD"
DANGER_COLOR = "#e74c3c"
DANGER_HOVER = "#c0392b"
SUCCESS_COLOR = "#2ecc71"
WARNING_COLOR = "#f39c12"
MUTED_COLOR = "#7f8c8d"
TEXT_COLOR = "#EAEAEA"
BG_COLOR = "#0F172A"
SURFACE_COLOR = "#1E293B"
BORDER_COLOR = "#334155"
HEADER_COLOR = "#e74c3c"
FONT_FAMILY = "Segoe UI"
BASE_FONT_SIZE = 13

# Temas disponíveis como exemplo
THEMES = {
    "AuroraDark": {
        "PRIMARY_COLOR": "#0EA5E9",   # Azul
        "PRIMARY_HOVER": "#23B5F5",
        "PRIMARY_ACTIVE": "#0284C7",
        "DANGER_COLOR": "#e74c3c",
        "DANGER_HOVER": "#c0392b",
        "SUCCESS_COLOR": "#2ecc71",
        "WARNING_COLOR": "#f39c12",
        "MUTED_COLOR": "#7f8c8d",
        "TEXT_COLOR": "#EAEAEA",
        "BG_COLOR": "#0B1020",
        "SURFACE_COLOR": "#121A2A",
        "BORDER_COLOR": "#1F2A44",
        "HEADER_COLOR": "#e74c3c",
        "FONT_FAMILY": "Segoe UI",
        "BASE_FONT_SIZE": 13,
    },
    "OceanBlue": {
        "PRIMARY_COLOR": "#0EA5E9", 
        "PRIMARY_HOVER": "#0284C7",
        "PRIMARY_ACTIVE": "#0369A1",
        "DANGER_COLOR": "#e74c3c",
        "DANGER_HOVER": "#c0392b",
        "SUCCESS_COLOR": "#2ecc71",
        "WARNING_COLOR": "#f39c12",
        "MUTED_COLOR": "#7f8c8d",
        "TEXT_COLOR": "#EAEAEA",
        "BG_COLOR": "#0A1426",
        "SURFACE_COLOR": "#0F1B33",
        "BORDER_COLOR": "#1E3A8A",
        "HEADER_COLOR": "#e74c3c",
        "FONT_FAMILY": "Segoe UI",
        "BASE_FONT_SIZE": 13,
    },
    "LightDefault": {
        "PRIMARY_COLOR": "#2563EB",   # Azul vivo
        "PRIMARY_HOVER": "#1D4ED8",
        "PRIMARY_ACTIVE": "#1E40AF",
        "DANGER_COLOR": "#DC2626",
        "DANGER_HOVER": "#B91C1C",
        "SUCCESS_COLOR": "#16A34A",
        "WARNING_COLOR": "#D97706",
        "MUTED_COLOR": "#6B7280",
        "TEXT_COLOR": "#1F2937",
        "BG_COLOR": "#F5F7FA",
        "SURFACE_COLOR": "#FFFFFF",
        "BORDER_COLOR": "#D1D5DB",
        "HEADER_COLOR": "#DC2626",
        "FONT_FAMILY": "Segoe UI",
        "BASE_FONT_SIZE": 13,
    }
}


def apply_theme(theme_name: str = "AuroraDark"):
    """Aplica um tema atualizando variáveis globais de cor e tipografia."""
    global PRIMARY_COLOR, PRIMARY_HOVER, PRIMARY_ACTIVE, DANGER_COLOR, DANGER_HOVER
    global SUCCESS_COLOR, WARNING_COLOR, MUTED_COLOR, TEXT_COLOR, BG_COLOR
    global SURFACE_COLOR, BORDER_COLOR, HEADER_COLOR, FONT_FAMILY, BASE_FONT_SIZE
    theme = THEMES.get(theme_name)
    if not theme:
        return  # mantém padrão
    PRIMARY_COLOR = theme["PRIMARY_COLOR"]
    PRIMARY_HOVER = theme["PRIMARY_HOVER"]
    PRIMARY_ACTIVE = theme["PRIMARY_ACTIVE"]
    DANGER_COLOR = theme["DANGER_COLOR"]
    DANGER_HOVER = theme["DANGER_HOVER"]
    SUCCESS_COLOR = theme["SUCCESS_COLOR"]
    WARNING_COLOR = theme["WARNING_COLOR"]
    MUTED_COLOR = theme["MUTED_COLOR"]
    TEXT_COLOR = theme["TEXT_COLOR"]
    BG_COLOR = theme["BG_COLOR"]
    SURFACE_COLOR = theme["SURFACE_COLOR"]
    BORDER_COLOR = theme["BORDER_COLOR"]
    HEADER_COLOR = theme["HEADER_COLOR"]
    FONT_FAMILY = theme["FONT_FAMILY"]
    BASE_FONT_SIZE = theme["BASE_FONT_SIZE"]


def get_global_styles():
    """Retorna QSS global para uma aparência moderna e consistente."""
    # Escala responsiva (clamp entre 0.75 e 1.0)
    try:
        scale = float(os.environ.get('POWERLIFT_UI_SCALE', '0.90'))
        scale = max(0.75, min(1.0, scale))
    except Exception:
        scale = 0.90

    # Medidas padrão responsivas
    btn_primary_min_h = int(50 * scale)
    btn_secondary_min_h = int(46 * scale)
    btn_primary_min_w = int(440 * scale)
    btn_secondary_min_w = int(320 * scale)
    border_radius = int(12 * scale)
    base_font = max(12, int(BASE_FONT_SIZE * scale))

    return f"""
    QMainWindow {{
        background-color: {BG_COLOR};
    }}
    QDialog {{
        background-color: {BG_COLOR};
        border: none;
    }}
    QWidget {{
        background-color: {BG_COLOR};
        color: {TEXT_COLOR};
        font-family: '{FONT_FAMILY}';
        font-size: {base_font}px;
    }}
    QLabel {{
        background-color: transparent;
        color: {TEXT_COLOR};
        padding: 3px;
    }}
    /* QScrollArea e seu viewport transparentes para evitar painel visível */
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollArea > QWidget {{
        background-color: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}
    /* Título herói da tela de login */
    #heroTitle {{
        font-size: 28px;
        font-weight: 800;
        letter-spacing: 0.4px;
        color: #FFFFFF;
        background-color: transparent;
        padding: 0px;
        border: none;
    }}
    /* Card central do login (semi-transparente sobre o fundo) */
    #loginCard {{
        background-color: rgba(17, 24, 39, 160);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
    }}
    /* Card central do menu principal (mesmo estilo do login) */
    #mainCard {{
        background-color: rgba(17, 24, 39, 160);
        border: none;
        border-radius: 16px;
    }}
    /* Central do Main sem fundo para revelar a imagem */
    #mainCentral {{
        background-color: transparent;
    }}
    /* Scroll principal do Main */
    #mainScroll {{
        background-color: transparent;
        border: none;
    }}
    /* Overlay escuro sobre a imagem do painel direito */
    #loginRightOverlay {{
        background-color: rgba(0, 0, 0, 170);
    }}
    /* Cards de seções no Main (semi-transparente) */
    #sectionCard {{
        background-color: rgba(17, 24, 39, 140);
        border: none;
        border-radius: 12px;
    }}
    /* Título das seções, branco e sem borda */
    #sectionTitle {{
        color: #FFFFFF;
        background-color: transparent;
        border: none;
        padding: 0px;
        font-weight: 700;
    }}
    /* Wrapper com gradiente para inputs */
    #gradientInput {{
        background-color: white;
        border: 1px solid #D1D5DB;
        border-radius: 10px;
        padding: 6px 8px;
    }}
    #gradientInput QLineEdit {{
        background-color: transparent;
        color: #111827;
        border: none;
        padding: 6px 8px;
        font-size: 14px;
        min-height: 42px;
        selection-background-color: #93C5FD;
        selection-color: #0B0F12;
    }}
    #gradientInput QLineEdit::placeholder {{
        color: #6B7280;
    }}
    #gradientInput QLineEdit:focus {{
        outline: none;
    }}
    /* Botão ícone (mostrar/ocultar senha) */
    #iconButton {{
        background-color: transparent;
        color: #A1A7B3;
        border: none;
        padding: 6px 10px;
        min-height: 28px;
    }}
    #iconButton:hover {{ color: #2563EB; }}
    
    /* Botão de link para "Esqueci minha senha" */
    #linkButton {{
        background-color: transparent;
        color: #FFFFFF;
        border: none;
        padding: 0px;
        font-size: 12px;
        text-decoration: underline;
    }}
    #linkButton:hover {{
        color: #93C5FD;
    }}
    /* Botão de gradiente para login */
    #gradientButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #3B82F6, stop:1 #0EA5E9);
        color: white;
        border: 1px solid #1E40AF;
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: 0.3px;
        padding: 12px 18px;
        min-height: 46px;
    }}
    #gradientButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #60A5FA, stop:1 #23B5F5);
        border-color: #1D4ED8;
    }}
    #gradientButton:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #2563EB, stop:1 #0284C7);
        border-color: #1E40AF;
    }}
    QFrame {{
        background-color: {SURFACE_COLOR};
        border: 1px solid {BORDER_COLOR};
        border-radius: 10px;
    }}
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {PRIMARY_COLOR}, stop:1 {PRIMARY_HOVER});
        color: white;
        font-weight: bold;
        padding: 12px 18px;
        border-radius: {border_radius}px;
        border: 2px solid {PRIMARY_COLOR};
        font-size: {max(12,int(14*scale))}px;
        min-height: {btn_secondary_min_h}px;
        min-width: {int(140*scale)}px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {PRIMARY_HOVER}, stop:1 {PRIMARY_ACTIVE});
        border: 2px solid {PRIMARY_HOVER};
    }}
    QPushButton:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {PRIMARY_ACTIVE}, stop:1 {PRIMARY_ACTIVE});
        border: 2px solid {PRIMARY_ACTIVE};
    }}
    QPushButton:focus {{
        outline: none;
        border: 3px solid #7DD3FC;
    }}
    /* Variante primária explícita (para botões com objectName "primary") */
    QPushButton#primary {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #3B82F6, stop:1 #1E40AF);
        color: white;
        font-weight: bold;
        padding: 12px 20px;
        border-radius: {border_radius}px;
        border: 2px solid #2563EB;
        font-size: {max(12,int(15*scale))}px;
        min-height: {btn_primary_min_h}px;
        min-width: {btn_primary_min_w}px;
    }}
    QPushButton#primary:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #60A5FA, stop:1 #3B82F6);
        border-color: #3B82F6;
    }}
    QPushButton#primary:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #1E40AF, stop:1 #1E3A8A);
        border-color: #1E40AF;
    }}
    /* Botão secundário para ações neutras (ex.: Cancelar) */
    #secondaryButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #4B5563, stop:1 #374151);
        color: white;
        border: 2px solid #6B7280;
        font-weight: 600;
        padding: 10px 16px;
        border-radius: 10px;
        min-height: 44px;
    }}
    #secondaryButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #6B7280, stop:1 #4B5563);
        border-color: #9CA3AF;
    }}
    /* Variante secundária usada no Menu Principal */
    QPushButton#secondary {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #475569, stop:1 #334155);
        color: white;
        border: 2px solid #64748B;
        font-weight: 600;
        padding: 12px 18px;
        border-radius: {border_radius}px;
        font-size: {max(12,int(14*scale))}px;
        min-height: {btn_secondary_min_h}px;
        min-width: {btn_secondary_min_w}px;
    }}
    QPushButton#secondary:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #64748B, stop:1 #475569);
        border-color: #94A3B8;
    }}
    QPushButton#secondary:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #334155, stop:1 #1E293B);
        border-color: #475569;
    }}
    QComboBox, QSpinBox, QLineEdit {{
        background-color: {SURFACE_COLOR};
        color: {TEXT_COLOR};
        border: 1px solid {BORDER_COLOR};
        padding: 8px;
        border-radius: 8px;
        min-height: 34px;
        font-size: 13px;
    }}
    QLineEdit::placeholder {{
        color: #9CA3AF;
    }}
    /* Radio buttons estilizados */
    QRadioButton {{
        spacing: 8px;
    }}
    QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 9px;
        border: 2px solid {BORDER_COLOR};
        background: {SURFACE_COLOR};
        margin-right: 6px;
    }}
    QRadioButton::indicator:hover {{
        border-color: {PRIMARY_COLOR};
    }}
    QRadioButton::indicator:checked {{
        background-color: {PRIMARY_COLOR};
        border-color: {PRIMARY_COLOR};
    }}
    QTreeWidget {{
        background-color: {SURFACE_COLOR};
        alternate-background-color: #0B1220;
        color: {TEXT_COLOR};
        border-radius: 8px;
        border: 1px solid {BORDER_COLOR};
        font-size: 12px;
    }}
    QTreeWidget::item {{
        padding: 5px;
        border-bottom: 1px solid {BORDER_COLOR};
    }}
    QTreeWidget::item:selected {{
        background-color: {PRIMARY_COLOR};
    }}
    QHeaderView::section {{
        background-color: #273244;
        color: white;
        padding: 6px;
        border: none;
        font-size: 12px;
    }}
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QMessageBox {{
        background-color: {BG_COLOR};
    }}
    QMessageBox QLabel {{
        color: {TEXT_COLOR};
        font-size: 14px;
    }}
    QMessageBox QPushButton {{
        background-color: {PRIMARY_COLOR};
        color: white;
        border: none;
        padding: 10px 20px;
        font-size: 14px;
        border-radius: 8px;
        min-width: 88px;
    }}
    QMessageBox QPushButton:hover {{
        background-color: {PRIMARY_HOVER};
    }}
    QMessageBox QPushButton:pressed {{
        background-color: {PRIMARY_ACTIVE};
    }}
    #title {{
        font-size: 20px;
        font-weight: bold;
        color: {TEXT_COLOR};
    }}
    """


def get_button_style(kind: str = "primary"):
    """Retorna estilo específico para botões (primary, danger, success, warning, secondary)."""
    if kind == "danger":
        return f"""
        QPushButton {{ background-color: {DANGER_COLOR}; }}
        QPushButton:hover {{ background-color: {DANGER_HOVER}; }}
        """
    if kind == "success":
        return f"""
        QPushButton {{ background-color: {SUCCESS_COLOR}; }}
        QPushButton:hover {{ background-color: #27ae60; }}
        """
    if kind == "warning":
        return f"""
        QPushButton {{ background-color: {WARNING_COLOR}; }}
        QPushButton:hover {{ background-color: #d68910; }}
        """
    if kind == "secondary":
        return f"""
        QPushButton {{ background-color: {SURFACE_COLOR}; color: {TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; }}
        QPushButton:hover {{ background-color: {BG_COLOR}; }}
        """
    return ""  # primary usa o global
