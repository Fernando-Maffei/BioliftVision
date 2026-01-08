import os
import sys
from typing import Optional

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QColor, QFont, QIcon
from PyQt5.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QAction,
    QSizePolicy,
    QScrollArea,
    QFileDialog,
    QStyle,
    QProgressDialog,
    QMessageBox,
    QGraphicsBlurEffect,
    QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import QProcess, QSettings

from common.logger import log_info, log_error, log_warning
from common.paths import logs_dir, results_dir, model_file, app_root, resource_path



class MainMenu(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Menu Principal - Análise de Vídeo")
        self.setGeometry(200, 120, 1100, 800)
        try:
           
            from PyQt5.QtGui import QPixmap
            ico_path = resource_path(os.path.join('ui', 'icon_hotbar.ico'))
            png_path = resource_path(os.path.join('ui', 'icon_hotbar.png'))
            if not os.path.exists(ico_path) and os.path.exists(png_path):
                try:
                    pix = QPixmap(png_path)
                    if not pix.isNull():
                        pix.save(ico_path, "ICO")
                except Exception:
                    pass
            if os.path.exists(ico_path):
                self.setWindowIcon(QIcon(ico_path))
            else:
                self.setWindowIcon(QIcon(png_path))
        except Exception:
            pass
        try:
            self.ui_scale = float(os.environ.get('POWERLIFT_UI_SCALE', '0.90'))
            self.ui_scale = max(0.75, min(1.0, self.ui_scale))
        except Exception:
            self.ui_scale = 0.90
        self.analysis_running = False
        self._training_window = None
        self.dataset_process: Optional[QProcess] = None
        self.progress: Optional[QProgressDialog] = None
        self.current_theme = os.environ.get('POWERLIFT_THEME', 'AuroraDark')
        app = QApplication.instance()
        if app:
            from ui.style import get_global_styles
            app.setStyleSheet(get_global_styles())
        from ui.style import get_global_styles
        self.setStyleSheet(get_global_styles())

       

        self._init_ui()
        self._check_model_availability()

    def _init_ui(self):
        scroll_area = QScrollArea()
        scroll_area.setObjectName("mainScroll")
        scroll_area.setWidgetResizable(True)
        try:
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        except Exception:
            pass
        try:
            scroll_area.setFrameShape(QFrame.NoFrame)
            scroll_area.setStyleSheet(
                "QScrollArea{background: transparent; border: none;}")
        except Exception:
            pass
        central = QWidget()
        central.setObjectName("mainCentral")
        try:
            central.setStyleSheet("#mainCentral{background: transparent;}")
        except Exception:
            pass
        try:
            scroll_area.viewport().setStyleSheet("background: transparent;")
        except Exception:
            pass
        scroll_area.setWidget(central)
        self.setCentralWidget(scroll_area)
        bg_path = resource_path(os.path.join(
            'ui', 'background.png')).replace('\\', '/')
        self._bg_label = QLabel(self)
        try:
            app = QApplication.instance()
            if app is not None and hasattr(app, '_biolift_bg_pixmap') and isinstance(app._biolift_bg_pixmap, QPixmap):
                self._bg_pixmap = app._biolift_bg_pixmap
            else:
                self._bg_pixmap = QPixmap(bg_path)
        except Exception:
            self._bg_pixmap = QPixmap(bg_path)
        self._bg_label.setScaledContents(True)
        try:
            self._bg_blur = QGraphicsBlurEffect(self._bg_label)
            self._bg_blur.setBlurRadius(6)
            self._bg_label.setGraphicsEffect(self._bg_blur)
        except Exception:
            self._bg_blur = None
        self._bg_label.setGeometry(self.rect())
        self._bg_label.lower()
        try:
            self._bg_label.setVisible(True)
        except Exception:
            pass
        try:
            self._bg_overlay = QLabel(self)
            self._bg_overlay.setStyleSheet(
                "background-color: rgba(14, 17, 22, 110);")
            self._bg_overlay.setGeometry(self.rect())
            self._bg_overlay.setAttribute(
                Qt.WA_TransparentForMouseEvents, True)
            self._bg_overlay.show()
        except Exception:
            self._bg_overlay = None
        outer = QVBoxLayout(central)
        self.outer_layout = outer
        self.main_layout = outer
        outer.setContentsMargins(int(
            64*self.ui_scale), int(64*self.ui_scale), int(64*self.ui_scale), int(64*self.ui_scale))
        outer.setSpacing(int(24*self.ui_scale))
        try:
            if hasattr(self, '_bg_overlay') and self._bg_overlay is not None:
                self._bg_overlay.stackUnder(scroll_area)
        except Exception:
            pass

        app_icon_label = QLabel()
        try:
            icon_path = resource_path(os.path.join('ui', 'icon_hotbar.png'))
            pix = QPixmap(icon_path)
            if not pix.isNull():
                size = int(112 * getattr(self, 'ui_scale', 1.0))
                app_icon_label.setPixmap(pix.scaled(
                    size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                app_icon_label.setAlignment(Qt.AlignCenter)
        except Exception:
            app_icon_label.setText("BioLiftVision")
            app_icon_label.setObjectName("heroTitle")
            app_icon_label.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("mainCard")
        try:
            card.setFrameShape(QFrame.NoFrame)
            card.setFrameShadow(QFrame.Plain)
        except Exception:
            pass
        card_layout = QVBoxLayout(card)
        self.card_layout = card_layout
        card_layout.setContentsMargins(int(
            28*self.ui_scale), int(28*self.ui_scale), int(28*self.ui_scale), int(28*self.ui_scale))
        card_layout.setSpacing(int(20*self.ui_scale))
        card.setMaximumWidth(int(860*self.ui_scale))
        try:
            self._card_shadow = QGraphicsDropShadowEffect(self)
            self._card_shadow.setBlurRadius(28)
            self._card_shadow.setXOffset(0)
            self._card_shadow.setYOffset(10)
            self._card_shadow.setColor(QColor(0, 0, 0, 110))
            card.setGraphicsEffect(self._card_shadow)
        except Exception:
            self._card_shadow = None
        self.main_card = card

        card_layout.addWidget(app_icon_label, alignment=Qt.AlignHCenter)
        title = QLabel("Ferramentas e Funcionalidades")
        title.setObjectName("heroTitle")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        actions_card = QFrame()
        actions_card.setObjectName("sectionCard")
        try:
            actions_card.setFrameShape(QFrame.NoFrame)
            actions_card.setFrameShadow(QFrame.Plain)
        except Exception:
            pass
        actions_card_layout = QVBoxLayout(actions_card)
        self.actions_card_layout = actions_card_layout
        actions_card_layout.setContentsMargins(16, 16, 16, 16)
        actions_card_layout.setSpacing(12)
        actions_title = QLabel("Ações Principais")
        actions_title.setObjectName("sectionTitle")
        actions_title.setAlignment(Qt.AlignCenter)
        actions_card_layout.addWidget(actions_title)

        actions = QVBoxLayout()
        self.actions_layout = actions
        actions.setSpacing(24)
        actions.setContentsMargins(0, 0, 0, 0)
        actions_card_layout.addLayout(actions)
        card_layout.addWidget(actions_card)
        self.card_layout = card_layout
        self.main_card = card

        button_width = int(480*self.ui_scale)
        button_height = int(40*self.ui_scale)

        icon_size = QSize(int(20*self.ui_scale), int(20*self.ui_scale))
        btn_run = QPushButton("Executar Software de Análise")
        btn_run.setObjectName("primary")
        btn_run.setAccessibleName("Executar Software de Análise")
        btn_run.setToolTip("Abrir a aplicação de análise")
        btn_run.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        btn_run.setIconSize(icon_size)
        btn_run.clicked.connect(self.run_software)
        btn_run.setMinimumHeight(button_height)
        btn_run.setFixedWidth(button_width)
        btn_run.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn_run.setStyleSheet(
            """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3B82F6, stop:1 #1E40AF);
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border-radius: 12px;
                border: 2px solid #2563EB;
                font-size: 15px;
                min-height: 50px;
                min-width: 140px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #60A5FA, stop:1 #3B82F6);
                border-color: #3B82F6;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1E40AF, stop:1 #1E3A8A);
                border-color: #1E40AF;
            }
        """
        )
        actions.addWidget(btn_run, alignment=Qt.AlignHCenter)
        self.btn_run = btn_run

        # Botão para abrir a Tela de Processamento
        btn_unified = QPushButton("Processar Vídeos")
        btn_unified.setObjectName("primary")
        btn_unified.setAccessibleName("Processar Vídeos")
        btn_unified.setToolTip("Abrir a tela de processamento")
        try:
            btn_unified.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
            btn_unified.setIconSize(icon_size)
        except Exception:
            pass
        btn_unified.clicked.connect(self.open_unified_processing)
        btn_unified.setMinimumHeight(button_height)
        btn_unified.setFixedWidth(button_width)
        btn_unified.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn_unified.setStyleSheet(
            """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10B981, stop:1 #047857);
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border-radius: 12px;
                border: 2px solid #059669;
                font-size: 15px;
                min-height: 50px;
                min-width: 140px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34D399, stop:1 #10B981);
                border-color: #10B981;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #047857, stop:1 #065F46);
                border-color: #047857;
            }
        """
        )
        
        btn_register_judge = QPushButton("Cadastrar Usuário")
        btn_register_judge.setObjectName("primary")
        btn_register_judge.setAccessibleName("Cadastrar Usuário")
        btn_register_judge.setToolTip("Cadastrar novo usuário (apenas admin)")
        try:
            btn_register_judge.setIcon(self.style().standardIcon(QStyle.SP_DialogOkButton))
            btn_register_judge.setIconSize(icon_size)
        except Exception:
            pass
        btn_register_judge.clicked.connect(self.open_admin_register_judge)
        btn_register_judge.setMinimumHeight(button_height)
        btn_register_judge.setFixedWidth(button_width)
        btn_register_judge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn_register_judge.setStyleSheet(
            """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3B82F6, stop:1 #1E40AF);
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border-radius: 12px;
                border: 2px solid #2563EB;
                font-size: 15px;
                min-height: 50px;
                min-width: 140px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #60A5FA, stop:1 #3B82F6);
                border-color: #3B82F6;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1E40AF, stop:1 #1E3A8A);
                border-color: #1E40AF;
            }
        """
        )
       
        try:
            settings = QSettings("BioLiftVision", "PowerliftApp")
            role = settings.value("auth/role", "judge", type=str) or "judge"
            is_admin = "admin" in role.lower()
            btn_register_judge.setVisible(is_admin)
        except Exception:
            pass
        row = QHBoxLayout()
        row.setSpacing(24)
        row.addStretch(1)
        row.addWidget(btn_unified)
        row.addWidget(btn_register_judge)
        row.addStretch(1)
        actions.addLayout(row)
        self.btn_register_judge = btn_register_judge
        self.btn_unified = btn_unified

        utils_card = QFrame()
        utils_card.setObjectName("sectionCard")
        utils_layout = QVBoxLayout(utils_card)
        utils_layout.setContentsMargins(16, 16, 16, 16)
        utils_layout.setSpacing(12)
        utils_title = QLabel("Utilitários")
        utils_title.setObjectName("sectionTitle")
        utils_title.setAlignment(Qt.AlignCenter)
        utils_layout.addWidget(utils_title)

        utils_grid = QGridLayout()
        self.utils_grid = utils_grid
        utils_grid.setHorizontalSpacing(16)
        utils_grid.setVerticalSpacing(16)
        utils_layout.addLayout(utils_grid)
        card_layout.addWidget(utils_card)

        utils_button_width = int(360*self.ui_scale)
    
        utils_button_height = int(46*self.ui_scale)

        secondary_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #475569, stop:1 #334155);
                color: white;
                border: 2px solid #64748B;
                font-weight: 600;
                padding: 12px 18px;
                border-radius: 12px;
                font-size: 14px;
                min-height: 48px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #64748B, stop:1 #475569);
                border-color: #94A3B8;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #334155, stop:1 #1E293B);
                border-color: #475569;
            }
        """


        btn_open_logs = QPushButton("Abrir Pasta de Logs")
        btn_open_logs.setObjectName("secondary")
        btn_open_logs.setToolTip("Abrir pasta de logs da aplicação")
        btn_open_logs.setIcon(self.style().standardIcon(QStyle.SP_DirIcon))
        btn_open_logs.setIconSize(icon_size)
        btn_open_logs.clicked.connect(self.open_logs_folder)
        btn_open_logs.setMinimumHeight(utils_button_height)
        btn_open_logs.setFixedWidth(utils_button_width)
        btn_open_logs.setStyleSheet(secondary_style)
        self.btn_open_logs = btn_open_logs
        # Posicionar à esquerda para simetria
        utils_grid.addWidget(btn_open_logs, 1, 0)

        btn_open_results = QPushButton("Abrir Pasta de Resultados")
        btn_open_results.setObjectName("secondary")
        btn_open_results.setToolTip("Abrir pasta de resultados do modelo")
        btn_open_results.setIcon(
            self.style().standardIcon(QStyle.SP_DirOpenIcon))
        btn_open_results.setIconSize(icon_size)
        btn_open_results.clicked.connect(self.open_results_folder)
        btn_open_results.setMinimumHeight(utils_button_height)
        btn_open_results.setFixedWidth(utils_button_width)
        btn_open_results.setStyleSheet(secondary_style)
        self.btn_open_results = btn_open_results
        # Posicionar à direita para simetria
        utils_grid.addWidget(btn_open_results, 1, 1)

        logs_card = QFrame()
        logs_card.setObjectName("sectionCard")
        logs_layout = QVBoxLayout(logs_card)
        self.logs_layout = logs_layout
        logs_layout.setContentsMargins(24, 24, 24, 24)
        logs_layout.setSpacing(20)
        logs_title = QLabel("Logs de Execução")
        logs_title.setObjectName("sectionTitle")
        logs_title.setAlignment(Qt.AlignCenter)
        logs_layout.addWidget(logs_title)

        logs_actions = QHBoxLayout()
        logs_actions.setSpacing(16)
        btn_clear_logs = QPushButton("Limpar Logs")
        btn_clear_logs.setObjectName("secondary")
        btn_clear_logs.setMinimumHeight(int(40*self.ui_scale))
        btn_clear_logs.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        btn_clear_logs.setIconSize(icon_size)
        btn_clear_logs.clicked.connect(self.clear_logs)
        btn_clear_logs.setStyleSheet(secondary_style)
        logs_actions.addStretch(1)
        logs_actions.addWidget(btn_clear_logs)

        btn_export_logs = QPushButton("Exportar Logs (.txt)")
        btn_export_logs.setObjectName("secondary")
        btn_export_logs.setIcon(
            self.style().standardIcon(QStyle.SP_DialogSaveButton))
        btn_export_logs.setIconSize(icon_size)
        btn_export_logs.setMinimumHeight(int(40*self.ui_scale))
        btn_export_logs.clicked.connect(self.export_logs_to_txt)
        btn_export_logs.setStyleSheet(secondary_style)
        logs_actions.addWidget(btn_export_logs)
        logs_actions.addStretch(1)
        logs_layout.addLayout(logs_actions)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(int(160*self.ui_scale))
        self.log_view.setFont(QFont("Consolas", 10))
        logs_layout.addWidget(self.log_view)
        card_layout.addWidget(logs_card)
        outer.addStretch(1)
        outer.addWidget(card, alignment=Qt.AlignCenter)
        outer.addStretch(1)
        try:
            self.menuBar().setVisible(False)
        except Exception:
            pass

        # Removido menu superior de Administração; cadastro será acessível por botão dedicado
        self.update_tools_state()
        footer = QHBoxLayout()
        outer.addLayout(footer)
        lbl_status = QLabel("Modelo treinado: ")
        self.lbl_model_status_dot = QLabel("●")
        self.lbl_model_status_dot.setStyleSheet(
            "color: #95a5a6; font-size: 14px;")
        self.lbl_model_status = QLabel("Desconhecido")
        footer.addWidget(lbl_status)
        footer.addWidget(self.lbl_model_status_dot)
        footer.addWidget(self.lbl_model_status)
        footer.addStretch()
        self._update_background_pixmap()
        self._update_responsive_spacing()
        try:
            self._check_model_availability()
        except Exception:
            pass

    def clear_logs(self):
        try:
            if hasattr(self, 'log_view') and self.log_view is not None:
                self.log_view.clear()
        except Exception as e:
            log_warning(f"Falha ao limpar logs: {e}")

    def export_logs_to_txt(self):
        try:
            content = self.log_view.toPlainText() if hasattr(self, 'log_view') else ''
            if not content.strip():
                QMessageBox.information(
                    self, "Exportar Logs", "Não há conteúdo para exportar.")
                return
            fname, _ = QFileDialog.getSaveFileName(
                self, "Salvar Logs", "logs.txt", "Text Files (*.txt)")
            if fname:
                with open(fname, 'w', encoding='utf-8') as f:
                    f.write(content)
                QMessageBox.information(
                    self, "Exportar Logs", "Logs salvos com sucesso.")
        except Exception as e:
            log_error(f"Erro ao exportar logs: {e}")

    def _update_background_pixmap(self):
        if hasattr(self, '_bg_pixmap') and not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self._bg_label.setPixmap(scaled)
            self._bg_label.setGeometry(self.rect())

    def resizeEvent(self, event):
        try:
            self._update_background_pixmap()
            self._apply_window_mode_styles()
            try:
                if hasattr(self, '_bg_overlay') and self._bg_overlay is not None:
                    self._bg_overlay.setGeometry(self.rect())
            except Exception:
                pass
            self._apply_responsive_background()
            self._update_ui_scale_for_viewport()
            self._update_responsive_spacing()
            self._update_responsive_button_sizes()
        finally:
            super().resizeEvent(event)

    def _apply_window_mode_styles(self):
        try:
            if hasattr(self, '_bg_label') and getattr(self, '_bg_blur', None):
                self._bg_label.setGraphicsEffect(self._bg_blur)
            if hasattr(self, 'main_card') and self.main_card is not None:
                self.main_card.setStyleSheet("")
                if getattr(self, '_card_shadow', None):
                    self.main_card.setGraphicsEffect(self._card_shadow)
        except Exception:
            pass

    def _apply_responsive_background(self):
        try:
            w = self.width()
            if hasattr(self, '_bg_label') and self._bg_label is not None:
                if w < 900:
                    self._bg_label.setVisible(False)
                else:
                    self._bg_label.setVisible(True)
                    if hasattr(self, '_bg_blur') and self._bg_blur is not None:
                        self._bg_blur.setBlurRadius(4 if w < 1200 else 6)
        except Exception:
            pass

    def _update_responsive_spacing(self):
        h = self.height()
        actions_sp = int(max(20, min(52, (h // 30))) * self.ui_scale)
        card_sp = int(max(20, min(44, (h // 36))) * self.ui_scale)
        grid_sp = int(max(14, min(26, (h // 50))) * self.ui_scale)
        logs_sp = int(max(10, min(22, (h // 70))) * self.ui_scale)
        try:
            if hasattr(self, 'actions_layout'):
                self.actions_layout.setSpacing(actions_sp)
            if hasattr(self, 'actions_card_layout'):
                self.actions_card_layout.setSpacing(actions_sp)
            if hasattr(self, 'actions_row'):
                self.actions_row.setSpacing(
                    int(max(10, min(24, (h // 48))) * self.ui_scale))
            if hasattr(self, 'card_layout'):
                self.card_layout.setSpacing(card_sp)
            if hasattr(self, 'utils_grid'):
                self.utils_grid.setHorizontalSpacing(grid_sp)
                self.utils_grid.setVerticalSpacing(grid_sp)
            if hasattr(self, 'logs_layout'):
                self.logs_layout.setSpacing(logs_sp)
            if hasattr(self, 'main_layout'):
                margin = int(max(12, min(36, (h // 60))) * self.ui_scale)
                try:
                    self.main_layout.setContentsMargins(
                        margin, margin, margin, margin)
                except Exception:
                    pass
        except Exception:
            pass

    def _update_responsive_button_sizes(self):
        try:
            card_w = self.main_card.width() if hasattr(
                self, 'main_card') and self.main_card is not None else self.width()
            inner_padding = int(120 * self.ui_scale)
            spacing = 16

            # Botão principal: ocupar largura confortável, mantendo hierarquia visual
            run_w = max(int(440*self.ui_scale),
                        min(int(520*self.ui_scale), int(card_w - inner_padding)))
            if hasattr(self, 'btn_run') and self.btn_run is not None:
                self.btn_run.setFixedWidth(int(run_w))

            # Utilitários: dois botões lado a lado com largura simétrica
            utils_spacing = self.utils_grid.horizontalSpacing() if hasattr(self,
                                                                           'utils_grid') else 16
            utils_each = max(int(320*self.ui_scale), min(int(360*self.ui_scale),
                             (card_w - inner_padding - utils_spacing) / 2))
            for attr in ('btn_open_logs', 'btn_open_results'):
                btn = getattr(self, attr, None)
                if btn:
                    btn.setFixedWidth(int(utils_each))
        except Exception:
            pass

    def _update_ui_scale_for_viewport(self):
        try:
            base_w, base_h = 1100, 800
            vw, vh = max(1, self.width()), max(1, self.height())
            ratio_w = vw / float(base_w)
            ratio_h = vh / float(base_h)
            target = max(0.75, min(1.0, min(ratio_w, ratio_h)))
            if abs(target - getattr(self, 'ui_scale', 1.0)) > 0.02:
                self.ui_scale = target
        except Exception:
            pass

    def change_theme(self, theme_name: str):
        try:
            from ui.style import apply_theme, get_global_styles
            apply_theme(theme_name)
            app = QApplication.instance()
            if app:
                app.setStyleSheet(get_global_styles())
            self.setStyleSheet(get_global_styles())
            self.current_theme = theme_name
            os.environ['POWERLIFT_THEME'] = theme_name
            log_info(f"Tema alterado para: {theme_name}")
        except Exception as e:
            log_error(f"Falha ao aplicar tema: {str(e)}")

    def open_settings_dialog(self):
        return

    def run_software(self):
        if getattr(self, 'analysis_process', None) and self.analysis_process.state() != QProcess.NotRunning:
            QMessageBox.information(
                self, "Análise", "A análise já está em execução.")
            return
        self.analysis_process = QProcess(self)
        try:
            # Use a raiz do projeto como diretório de trabalho
            root = app_root()
            self.analysis_process.setWorkingDirectory(root)
        except Exception:
            pass
        try:
            self.analysis_process.readyReadStandardOutput.connect(
                self._on_process_output)
            self.analysis_process.readyReadStandardError.connect(
                self._on_process_output)

            def _on_error(err):
                try:
                    QMessageBox.critical(
                        self, "Erro ao iniciar análise", f"Falha ao iniciar processo: {err}")
                except Exception:
                    pass
            self.analysis_process.errorOccurred.connect(_on_error)
        except Exception:
            pass
        if getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS'):
            exe_path = sys.executable
            self.analysis_process.started.connect(self._on_analysis_started)
            self.analysis_process.finished.connect(self._on_analysis_finished)
            self.analysis_process.start(exe_path, ["--analysis"])
        else:
            # Caminhos corretos na raiz do projeto
            root = app_root()
            script_path = os.path.join(root, 'main.py')
            py310 = os.path.join(root, 'venv310', 'Scripts', 'python.exe')
            pyvenv = os.path.join(root, 'venv', 'Scripts', 'python.exe')
            python_cmd = sys.executable
            try:
                if os.path.exists(py310):
                    python_cmd = py310
                elif os.path.exists(pyvenv):
                    python_cmd = pyvenv
            except Exception:
                python_cmd = sys.executable
            self.analysis_process.started.connect(self._on_analysis_started)
            self.analysis_process.finished.connect(self._on_analysis_finished)
            # Executa main.py em modo análise
            self.analysis_process.start(
                python_cmd, [script_path, "--analysis"])

    def _on_analysis_started(self):
        self.analysis_running = True
        self.update_tools_state()

    def _on_analysis_finished(self):
        self.analysis_running = False
        self.update_tools_state()

    # Removido: diálogo de treinamento

    def open_unified_processing(self):
        try:
            from ui.training import TrainingWindow
            if getattr(self, '_training_window', None) is None:
                self._training_window = TrainingWindow()
            self._training_window.show()
            self._training_window.raise_()
            self._training_window.activateWindow()
        except Exception as e:
            try:
                QMessageBox.information(self, "Processamento", f"Falha ao abrir a tela de treinamento.\n\nDetalhes: {e}")
            except Exception:
                pass

    def refresh_admin_visibility(self):
        """Atualiza a visibilidade de controles administrativos de acordo com a role atual salva."""
        try:
            settings = QSettings("BioLiftVision", "PowerliftApp")
            role = settings.value("auth/role", "judge", type=str) or "judge"
            is_admin = "admin" in role.lower()
            if hasattr(self, 'btn_register_judge') and self.btn_register_judge is not None:
                self.btn_register_judge.setVisible(is_admin)
        except Exception:
            pass

    # ==== Administração ====
    def open_admin_register_judge(self):
        try:
            # Import tardio para evitar ciclo entre módulos
            from ui.login import AdminAuthDialog, RegisterUserDialog
        except Exception as e:
            try:
                QMessageBox.critical(self, "Administração", f"Falha ao carregar diálogos: {e}")
            except Exception:
                pass
            return

        try:
            gate = AdminAuthDialog(parent=self)
            if gate.exec_() != gate.Accepted:
                return
            dlg = RegisterUserDialog(parent=self)
            if dlg.exec_() == dlg.Accepted:
                data = getattr(dlg, 'data', {})
                from db.user_repository import UserRepository
                repo = UserRepository()
                try:
                    admin_user = getattr(gate, 'auth_user', None)
                    admin_pw = getattr(gate, 'auth_password', None)
                    ok, msg = repo.create_user_as_admin(
                        admin_username=admin_user or "",
                        admin_password=admin_pw or "",
                        name=data.get("name", ""),
                        username=data.get("username", ""),
                        email=data.get("email"),
                        password=data.get("password", ""),
                        role=data.get("role", "judge"),
                    )
                finally:
                    repo.close()
                if ok:
                    QMessageBox.information(self, "Administração", "Usuário cadastrado com sucesso.")
                else:
                    QMessageBox.warning(self, "Administração", msg or "Não foi possível cadastrar.")
        except Exception as e:
            try:
                QMessageBox.critical(self, "Administração", f"Falha ao cadastrar usuário: {e}")
            except Exception:
                pass

    def _show_progress(self, text: str):
        try:
            if getattr(self, 'progress', None):
                self.progress.close()
            self.progress = QProgressDialog(text, "Cancelar", 0, 0, self)
            self.progress.setWindowModality(Qt.ApplicationModal)
            self.progress.setAutoClose(True)
            self.progress.setMinimumDuration(0)
            self._progress_is_determinate = False
            try:
                self.progress.canceled.connect(self._on_progress_canceled)
            except Exception:
                pass
            self.progress.show()
        except Exception:
            pass

    def _close_progress(self):
        try:
            if getattr(self, 'progress', None):
                self.progress.close()
                self.progress = None
                self._progress_is_determinate = False
        except Exception:
            pass

    def _append_log(self, msg: str):
        try:
            if hasattr(self, 'log_view') and self.log_view:
                self.log_view.appendPlainText(msg)
        except Exception:
            pass

    def _verify_prereqs(self, dataset_dir: str, out_dir: str):
        try:
            from core.env_check import print_summary
            print_summary()
        except Exception:
            pass
        try:
            import os
            if not os.path.exists(dataset_dir):
                QMessageBox.warning(self, "Verificação", "Pasta de vídeos inválida.")
            if not os.path.exists(out_dir):
                try:
                    os.makedirs(out_dir, exist_ok=True)
                except Exception:
                    QMessageBox.warning(self, "Verificação", "Não foi possível criar a pasta de saída.")
            test_file = os.path.join(out_dir, "_perm_test.tmp")
            try:
                open(test_file, 'w').write('ok')
                os.remove(test_file)
            except Exception:
                QMessageBox.warning(self, "Verificação", "Sem permissão de escrita na pasta de saída.")
        except Exception:
            pass

    def _validate_dataset(self, dir_path: str) -> list:
        try:
            import os
            vids = {'.mp4', '.avi', '.mov', '.mkv'}
            exercises = []
            for name in os.listdir(dir_path):
                p = os.path.join(dir_path, name)
                if os.path.isdir(p):
                    has_video = False
                    for root, _, files in os.walk(p):
                        if any(os.path.splitext(f)[1].lower() in vids for f in files):
                            has_video = True
                            break
                    if has_video:
                        exercises.append(name)
            return exercises
        except Exception:
            return []

    def _start_extraction(self, dir_path: str, force: bool = False):
        try:
            exs = self._validate_dataset(dir_path)
            if not exs:
                QMessageBox.warning(self, "Processamento", "Nenhuma subpasta com vídeos encontrada.")
                return
            self._show_progress("Processando vídeos e gerando parquet...")
            from common.paths import app_root
            root = app_root()
            py310 = os.path.join(root, 'venv310', 'Scripts', 'python.exe')
            pyvenv = os.path.join(root, 'venv', 'Scripts', 'python.exe')
            python_cmd = py310 if os.path.exists(py310) else pyvenv if os.path.exists(pyvenv) else os.sys.executable
            code = (
                "import os, json, time;"
                "from pathlib import Path;"
                "from core.keypoints import process_correct_movements;"
                f"base=Path(r'{root}');inp=Path(r'{dir_path}');out=base/'dataset'/'processed_oneclass';"
                "out.mkdir(parents=True, exist_ok=True);"
                "man=out/'manifest.json';hist=[];"
                "\nfor d in inp.iterdir():\n"
                "    if d.is_dir():\n"
                "        ex=d.name\n"
                "        vid_ext={'.mp4','.avi','.mov','.mkv'}\n"
                "        has=False\n"
                "        for r,_,fs in os.walk(str(d)):\n"
                "            if any(os.path.splitext(f)[1].lower() in vid_ext for f in fs):\n"
                "                has=True;break\n"
                "        if not has: continue\n"
                "        dest=out/ex\n"
                "        dest.mkdir(parents=True, exist_ok=True)\n"
                "        df=process_correct_movements(str(d), str(dest))\n"
                "        pq=dest/'correct_movements.parquet'\n"
                "        if pq.exists():\n"
                "            new=dest/(ex+'.parquet')\n"
                "            try:\n"
                "                if new.exists():\n"
                "                    new.unlink()\n"
                "            except Exception: pass\n"
                "            pq.replace(new)\n"
                "            hist.append({'exercise':ex,'path':str(new),'ts':time.strftime('%Y%m%d-%H%M%S')})\n"
                "\ntry:\n"
                "    old=[]\n"
                "    if man.exists(): old=json.load(open(man,'r',encoding='utf-8'))\n"
                "    old.extend(hist)\n"
                "    open(man,'w',encoding='utf-8').write(json.dumps(old,ensure_ascii=False,indent=2))\n"
                "except Exception: pass\n"
            )
            proc = QProcess(self)
            try:
                proc.setWorkingDirectory(root)
            except Exception:
                pass
            self._attach_process(proc, "Processando vídeos e gerando parquet...", lambda: None)
            proc.start(python_cmd, ['-c', code])
        except Exception as e:
            try:
                QMessageBox.critical(self, "Processamento", f"Falha ao iniciar extração.\n\n{e}")
            except Exception:
                pass

    def _train_from_latest_parquet(self):
        try:
            from common.paths import app_root
            import glob, os
            root = app_root()
            base = self._output_dir if getattr(self, '_output_dir', None) else os.path.join(root, 'dataset', 'processed_oneclass')
            pats = glob.glob(os.path.join(base, '**', '*.parquet'), recursive=True)
            if not pats:
                QMessageBox.information(self, "Treinamento", "Nenhum parquet encontrado.")
                return
            pats.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            latest = pats[0]
            self._show_progress("Treinando modelo...")
            py310 = os.path.join(root, 'venv310', 'Scripts', 'python.exe')
            pyvenv = os.path.join(root, 'venv', 'Scripts', 'python.exe')
            python_cmd = py310 if os.path.exists(py310) else pyvenv if os.path.exists(pyvenv) else os.sys.executable
            script = os.path.join(root, 'core', 'train_model.py')
            proc = QProcess(self)
            try:
                proc.setWorkingDirectory(root)
            except Exception:
                pass
            self._attach_process(proc, "Treinando modelo...", lambda: None)
            proc.start(python_cmd, [script, '--dataset-file', latest])
        except Exception as e:
            try:
                QMessageBox.critical(self, "Treinamento", f"Falha ao iniciar treinamento.\n\n{e}")
            except Exception:
                pass

    def _train_from_file(self, file_path: str):
        try:
            from common.paths import app_root
            import os
            root = app_root()
            self._show_progress("Treinando modelo...")
            py310 = os.path.join(root, 'venv310', 'Scripts', 'python.exe')
            pyvenv = os.path.join(root, 'venv', 'Scripts', 'python.exe')
            python_cmd = py310 if os.path.exists(py310) else pyvenv if os.path.exists(pyvenv) else os.sys.executable
            script = os.path.join(root, 'core', 'train_model.py')
            proc = QProcess(self)
            try:
                proc.setWorkingDirectory(root)
            except Exception:
                pass
            self._attach_process(proc, "Treinando modelo...", lambda: None)
            proc.start(python_cmd, [script, '--dataset-file', file_path])
        except Exception as e:
            try:
                QMessageBox.critical(self, "Treinamento", f"Falha ao iniciar treinamento.\n\n{e}")
            except Exception:
                pass

    def _on_process_output(self):
        try:
            proc = self.sender()
            out = bytes(proc.readAllStandardOutput()).decode('utf-8', 'ignore')
            err = bytes(proc.readAllStandardError()).decode('utf-8', 'ignore')
            if out:
                self._append_log(out.strip())
                try:
                    import re as _re
                    m = _re.search(r"(\d{1,3})\s*%", out)
                    if m:
                        pct = max(0, min(100, int(m.group(1))))
                        if getattr(self, 'progress', None):
                            if not getattr(self, '_progress_is_determinate', False):
                                self.progress.setRange(0, 100)
                                self._progress_is_determinate = True
                            self.progress.setValue(pct)
                except Exception:
                    pass
            if err:
                self._append_log(err.strip())
        except Exception:
            pass

    def _attach_process(self, proc: QProcess, start_text: str, finished_cb):
        try:
            proc.setProcessChannelMode(QProcess.MergedChannels)
            proc.started.connect(lambda: self._show_progress(start_text))
            proc.readyReadStandardOutput.connect(self._on_process_output)
            proc.readyReadStandardError.connect(self._on_process_output)
            proc.finished.connect(
                lambda *args: (self._on_process_finished_wrapper(finished_cb)))
            self._current_process = proc
            self._set_actions_enabled(False)
        except Exception:
            pass

    def _on_process_finished_wrapper(self, finished_cb):
        try:
            self._close_progress()
            self._set_actions_enabled(True)
            self._current_process = None
        except Exception:
            pass
        try:
            finished_cb()
        except Exception:
            pass

    def _set_actions_enabled(self, enabled: bool):
        try:
            if hasattr(self, 'btn_run') and self.btn_run:
                self.btn_run.setEnabled(enabled)
            if hasattr(self, 'btn_dataset') and self.btn_dataset:
                self.btn_dataset.setEnabled(enabled)
            if hasattr(self, 'btn_train') and self.btn_train:
                self.btn_train.setEnabled(enabled)
            if hasattr(self, 'act_export') and self.act_export:
                self.act_export.setEnabled(enabled)
            if hasattr(self, 'act_save_frame') and self.act_save_frame:
                self.act_save_frame.setEnabled(enabled)
            if hasattr(self, 'act_snapshot') and self.act_snapshot:
                self.act_snapshot.setEnabled(enabled)
        except Exception:
            pass

    def _on_progress_canceled(self):
        try:
            if getattr(self, '_current_process', None):
                self._current_process.kill()
                self._append_log("[Processo] Cancelado pelo usuário.")
        except Exception:
            pass


    def open_logs_folder(self):
        folder = logs_dir()
        if os.path.exists(folder):
            try:
                os.startfile(folder)
            except Exception:
                QMessageBox.information(self, "Logs", folder)
        else:
            QMessageBox.warning(self, "Logs", "Pasta de logs não encontrada.")

    def open_results_folder(self):
        folder = results_dir()
        if os.path.exists(folder):
            try:
                os.startfile(folder)
            except Exception:
                QMessageBox.information(self, "Resultados", folder)
        else:
            QMessageBox.warning(self, "Resultados",
                                "Pasta de resultados não encontrada.")

    def update_tools_state(self):
        enabled = bool(self.analysis_running)
        try:
            self.act_save_frame.setEnabled(enabled)
            self.act_snapshot.setEnabled(enabled)
            self.act_export.setEnabled(enabled)
        except Exception:
            pass

    def _set_model_status(self, state: str):
        try:
            mapping = {
                'ready': ("Disponível", "#2ecc71"),
                'missing': ("Indisponível", "#e74c3c"),
                'training': ("Treinando...", "#f39c12"),
            }
            text, color = mapping.get(state, ("Desconhecido", "#95a5a6"))
            if hasattr(self, 'lbl_model_status'):
                self.lbl_model_status.setText(text)
            if hasattr(self, 'lbl_model_status_dot'):
                self.lbl_model_status_dot.setStyleSheet(
                    f"color: {color}; font-size: 14px;")
        except Exception:
            pass

    def _check_model_availability(self):
        model_path = model_file()
        exists = os.path.exists(model_path)
        self._set_model_status('ready' if exists else 'missing')

    def save_frame(self):
        QMessageBox.information(
            self, "Salvar Frame", "Disponível quando a análise está em execução.")

    def snapshot_analysis(self):
        QMessageBox.information(
            self, "Snapshot", "Disponível quando a análise está em execução.")

    def export_history(self):
        QMessageBox.information(
            self, "Exportar Histórico", "Disponível quando a análise está em execução.")

    # Removido: seleção de pasta/parquet para treinamento
