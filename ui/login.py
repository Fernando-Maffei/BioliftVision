import os
import sys
import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
    QMessageBox, QLineEdit, QSizePolicy, QGraphicsDropShadowEffect,
    QGraphicsBlurEffect, QCheckBox, QDialog, QFormLayout, QDialogButtonBox
)
from PyQt5.QtGui import QPixmap, QColor, QIcon
from PyQt5.QtCore import Qt, QTimer, QSettings
from common.logger import log_info, log_warning
from ui.settings import SettingsDialog
from ui.style import get_global_styles, apply_theme
from common.paths import resource_path

# resource_path passa a ser importado de common.paths


class LoginWindow(QWidget):
    """Tela de login da aplicação"""

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        log_info("Inicializando tela de login")
        self.setWindowTitle("Login - Powerlifting Analysis System")
        self.setGeometry(200, 120, 1280, 720)
        try:
            # Preferir icon_hotbar.ico; gerar a partir do PNG se não existir
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

        self.setStyleSheet(get_global_styles())

        # Cache de pixmap de fundo no QApplication para evitar recarregar a cada instância
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        bg_path = resource_path(os.path.join(
            'ui', 'background.png')).replace('\\', '/')
        if app is not None and not hasattr(app, '_biolift_bg_pixmap'):
            try:
                app._biolift_bg_pixmap = QPixmap(bg_path)
            except Exception:
                app._biolift_bg_pixmap = QPixmap(bg_path)

        self.init_ui()

    def init_ui(self):
        # Criar painel esquerdo via função auxiliar
        left = self.build_login_panel()
        self._login_left_panel = left
        self._bg_label = QLabel(self)
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None and hasattr(app, '_biolift_bg_pixmap'):
            self._bg_pixmap = app._biolift_bg_pixmap
        else:
            bg_path = resource_path(os.path.join(
                'ui', 'background.png')).replace('\\', '/')
            self._bg_pixmap = QPixmap(bg_path)
        self._bg_label.setScaledContents(True)
        blur = QGraphicsBlurEffect(self._bg_label)
        blur.setBlurRadius(6)
        self._bg_label.setGraphicsEffect(blur)
        self._bg_blur_effect = blur
        self._bg_label.setGeometry(self.rect())
        self._bg_label.lower()

        # Dimmer/overlay para melhorar contraste em dark mode
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

        try:
            self._apply_responsive_background()
        except Exception:
            pass

        # Overlay: layout sobre o fundo com painel de login centralizado
        outer = QVBoxLayout(self)
        outer.setContentsMargins(64, 64, 64, 64)
        outer.setSpacing(24)
        outer.addStretch(1)
        outer.addWidget(left, alignment=Qt.AlignHCenter)
        outer.addStretch(1)

        self.setLayout(outer)
        self._update_background_pixmap()
        self._load_saved_credentials()

        # Timer para aplicar alterações após resize (throttle)
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._apply_responsive_background)
        self._apply_responsive_background()

    def build_login_panel(self) -> QFrame:
        """Monta o painel esquerdo do login e retorna o QFrame."""
        left = QFrame()
        left.setObjectName("loginCard")
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        max_w = 640 if self.width() >= 1280 else 520
        left.setMaximumWidth(max_w)
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(20)
        left_layout.setContentsMargins(32, 32, 32, 32)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 120))
        left.setGraphicsEffect(shadow)

        # Logo e títulos
        logo = QLabel()
        try:
            icon_path = resource_path(os.path.join('ui', 'icon_app.png'))
            pix = QPixmap(icon_path)
            if not pix.isNull():
                logo.setPixmap(pix.scaled(
                    72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                logo.setAlignment(Qt.AlignCenter)
                left_layout.addWidget(logo, alignment=Qt.AlignCenter)
        except Exception:
            pass

        app_title = QLabel("BioLiftVision")
        app_title.setObjectName("heroTitle")
        app_title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(app_title)

        subtitle = QLabel("Sistema Inteligente de Análise de Powerlifting")
        subtitle.setObjectName("caption")
        subtitle.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(subtitle)

        section_title = QLabel("LOGIN")
        section_title.setObjectName("sectionTitle")
        section_title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(section_title)

        # Campo usuário
        user_wrapper = QFrame()
        user_wrapper.setObjectName("gradientInput")
        user_layout = QVBoxLayout(user_wrapper)
        user_layout.setContentsMargins(10, 10, 10, 10)
        user_layout.setSpacing(0)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Usuário")
        self.username_input.setMinimumHeight(38)
        self.username_input.setStyleSheet(
            "QLineEdit{border: none; padding: 6px; color: black;} QLineEdit::placeholder{ color: #222;}"
        )
        user_layout.addWidget(self.username_input)
        left_layout.addWidget(user_wrapper)

        # Campo senha
        pw_wrapper = QFrame()
        pw_wrapper.setObjectName("gradientInput")
        pw_layout = QHBoxLayout(pw_wrapper)
        pw_layout.setContentsMargins(10, 10, 10, 10)
        pw_layout.setSpacing(4)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Senha")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(40)
        self.password_input.setStyleSheet(
            "QLineEdit{border: none; padding: 6px; color: black;} QLineEdit::placeholder{ color: #222;}"
        )
        pw_layout.addWidget(self.password_input)

        self.btn_toggle_pw = QPushButton("Mostrar")
        self.btn_toggle_pw.setObjectName("iconButton")
        self.btn_toggle_pw.setCheckable(True)
        self.btn_toggle_pw.clicked.connect(self.toggle_password_visibility)
        pw_layout.addWidget(self.btn_toggle_pw)
        left_layout.addWidget(pw_wrapper)

        # Lembrar login (usuário + senha)
        self.remember_login_checkbox = QCheckBox("Lembrar login")
        self.remember_login_checkbox.setToolTip("Salva usuário e senha (senha via Keyring seguro)")
        row = QHBoxLayout(); row.addWidget(self.remember_login_checkbox)
        wrap = QFrame(); wrap.setLayout(row)
        left_layout.addWidget(wrap, alignment=Qt.AlignLeft)

        # Ações
        forgot_btn = QPushButton("Esqueci minha senha")
        forgot_btn.setObjectName("linkButton")
        forgot_btn.setCursor(Qt.PointingHandCursor)
        forgot_btn.clicked.connect(self.on_forgot_password)
        left_layout.addWidget(forgot_btn, alignment=Qt.AlignLeft)

        # Configuração de Banco
        cfg_btn = QPushButton("Configurar Banco")
        cfg_btn.setObjectName("gradientButton")
        cfg_btn.setMinimumHeight(46)
        cfg_btn.setFixedWidth(220)
        cfg_btn.clicked.connect(self.open_db_config)

        # Cadastro de Usuário (restrito a admin via diálogo)
        register_btn = QPushButton("Cadastrar Usuário")
        register_btn.setObjectName("gradientButton")
        register_btn.setToolTip("Cadastrar novo usuário (apenas admin)")
        register_btn.setMinimumHeight(46)
        register_btn.setFixedWidth(220)
        register_btn.clicked.connect(self.open_register_dialog)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(16)
        buttons_row.addStretch(1)
        buttons_row.addWidget(cfg_btn)
        buttons_row.addWidget(register_btn)
        buttons_row.addStretch(1)
        wrap_buttons = QFrame()
        wrap_buttons.setLayout(buttons_row)
        left_layout.addWidget(wrap_buttons)

        
        self.btn_login = QPushButton("Entrar")
        self.btn_login.setObjectName("gradientButton")
        self.btn_login.setAccessibleName("Entrar no sistema")
        self.btn_login.setToolTip(
            "Validar credenciais e abrir o menu principal")
        self.btn_login.setMinimumHeight(46)
        self.btn_login.setFixedWidth(280)
        self.btn_login.clicked.connect(self.check_login)
        left_layout.addWidget(self.btn_login, alignment=Qt.AlignCenter)

        left_layout.addStretch(1)

        return left

    def _load_saved_credentials(self):
        try:
            settings = QSettings("BioLiftVision", "PowerliftApp")
            saved_user = settings.value("auth/username", "", type=str)
            remember_login_raw = settings.value("auth/remember_login", None)
            # Fallback para versões antigas
            if remember_login_raw is None:
                remember_login = settings.value("auth/remember_password", False, type=bool)
            else:
                try:
                    remember_login = bool(remember_login_raw) if isinstance(remember_login_raw, bool) else str(remember_login_raw).lower() in ("true","1","yes")
                except Exception:
                    remember_login = False
            if saved_user:
                self.username_input.setText(saved_user)
                if hasattr(self, 'remember_login_checkbox'):
                    self.remember_login_checkbox.setChecked(bool(remember_login))
            if remember_login and saved_user:
                try:
                    import keyring
                    pw = keyring.get_password("BioLiftVision", saved_user)
                    if pw:
                        self.password_input.setText(pw)
                except Exception:
                    pass
        except Exception:
            pass

    def _update_background_pixmap(self):
        if hasattr(self, '_bg_pixmap') and not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self._bg_label.setPixmap(scaled)
            self._bg_label.setGeometry(self.rect())
        try:
            if hasattr(self, '_bg_overlay') and self._bg_overlay is not None:
                self._bg_overlay.setGeometry(self.rect())
        except Exception:
            pass

    def _apply_responsive_background(self):
        """Ajusta blur/visibilidade do fundo e largura do painel conforme tamanho."""
        w = self.width()
        try:
            if w < 900:
                self._bg_label.setVisible(False)
            else:
                self._bg_label.setVisible(True)
                if hasattr(self, '_bg_blur_effect') and self._bg_blur_effect is not None:
                    blur_radius = 4 if w < 1200 else 6
                    self._bg_blur_effect.setBlurRadius(blur_radius)
        except Exception:
            pass

        try:
            if hasattr(self, '_login_left_panel') and self._login_left_panel is not None:
                max_w = 640 if w >= 1280 else 520
                self._login_left_panel.setMaximumWidth(max_w)
        except Exception:
            pass

    def resizeEvent(self, event):
        try:
            self._update_background_pixmap()
            if hasattr(self, '_resize_timer') and self._resize_timer is not None:
                self._resize_timer.start(120)
        finally:
            super().resizeEvent(event)

    def toggle_password_visibility(self):
        is_hidden = self.password_input.echoMode() == QLineEdit.Password
        self.password_input.setEchoMode(
            QLineEdit.Normal if is_hidden else QLineEdit.Password)
        if hasattr(self, 'btn_toggle_pw'):
            self.btn_toggle_pw.setText("Ocultar" if is_hidden else "Mostrar")
            self.btn_toggle_pw.setChecked(not is_hidden)

    def on_forgot_password(self):
        QMessageBox.information(self, "Recuperar senha",
                                "Funcionalidade em breve.")

    def open_settings(self):
        current = os.environ.get('POWERLIFT_THEME', 'AuroraDark')
        dlg = SettingsDialog(current_theme=current,
                             on_apply=self.change_theme, parent=self)
        dlg.exec_()

    def open_db_config(self):
        try:
            from ui.db_config import DatabaseConfigDialog
            dlg = DatabaseConfigDialog(self)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Configuração", f"Erro ao abrir configuração de banco: {e}")

    def change_theme(self, theme: str):
        os.environ.setdefault('POWERLIFT_THEME', 'AuroraDark')
        apply_theme(theme)
        os.environ['POWERLIFT_THEME'] = theme
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_global_styles())
        self.setStyleSheet(get_global_styles())

    def check_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Erro", "Informe usuário e senha.")
            self.username_input.setFocus()
            return

        self.btn_login.setEnabled(False)
        original_text = self.btn_login.text()
        self.btn_login.setText("Acessando...")

        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        log_info(f"Tentativa de login - Usuário: {username}")
        ok, message = self.authenticate_user(username, password)

        if ok:
            try:
                settings = QSettings("BioLiftVision", "PowerliftApp")
                remember = bool(getattr(self, 'remember_login_checkbox', None) and self.remember_login_checkbox.isChecked())
                settings.setValue("auth/remember_login", remember)
                if remember:
                    settings.setValue("auth/username", username)
                    # Armazenar senha com segurança
                    try:
                        import keyring
                        keyring.set_password("BioLiftVision", username, password)
                    except Exception:
                        QMessageBox.information(self, "Lembrar login", "Armazenamento seguro indisponível. Instale 'keyring' para lembrar a senha.")
                else:
                    settings.remove("auth/username")
                    # Remover senha do keyring
                    try:
                        import keyring
                        try:
                            keyring.delete_password("BioLiftVision", username)
                        except Exception:
                            pass
                    except Exception:
                        pass
                # Registrar role do usuário logado para controle de UI
                try:
                    from db.user_repository import UserRepository
                    repo = UserRepository()
                    role = repo.get_user_role(username)
                    repo.close()
                except Exception:
                    role = None
                settings.setValue("auth/role", role or "judge")
            except Exception:
                pass

            log_info("Login realizado com sucesso")
            self.open_main_menu()
        else:
            log_warning(f"Tentativa de login falhou - Usuário: {username}")
            QMessageBox.warning(
                self, "Erro", message or "Usuário ou senha incorretos!")
            try:
                settings = QSettings("BioLiftVision", "PowerliftApp")
                settings.remove("auth/role")
                settings.setValue("auth/remember_login", False)
            except Exception:
                pass

        self.btn_login.setText(original_text)
        self.btn_login.setEnabled(True)

    def authenticate_user(self, username: str, password: str):
        """Autenticação. Tenta autenticar via banco SQL Server; se indisponível, usa stub.
        Retorna (ok: bool, message: str).
        """
        # Tentativa via banco
        try:
            from db.user_repository import UserRepository
            repo = UserRepository()
            ok, msg = repo.authenticate_user(username=username, password=password)
            repo.close()
            if ok:
                return True, "OK"
        except Exception:
            pass
        return False, "Usuário ou senha incorretos!"

    def open_main_menu(self):
        # Import tardio para evitar ciclo entre módulos
        from ui.main_menu import MainMenu
        if self.parent:
            try:
                self.parent.show_main_menu()
            except Exception:
                win = MainMenu()
                win.showMaximized()
        else:
            win = MainMenu()
            win.showMaximized()
        self.close()

    # ==== Cadastro de Usuário (admin) ====
    def open_register_dialog(self):
        # Protegido por autenticação de administrador
        gate = AdminAuthDialog(parent=self)
        if gate.exec_() != QDialog.Accepted:
            return

        dlg = RegisterUserDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.data
            try:
                from db.user_repository import UserRepository
                repo = UserRepository()
                # Verificação de permissão também no backend
                admin_user = getattr(gate, 'auth_user', '')
                admin_pw = getattr(gate, 'auth_password', '')
                ok, msg = repo.create_user_as_admin(
                    admin_username=admin_user,
                    admin_password=admin_pw,
                    name=data.get("name", ""),
                    username=data.get("username", ""),
                    email=data.get("email"),
                    password=data.get("password", ""),
                    role=data.get("role", "judge"),
                )
                repo.close()
                if ok:
                    QMessageBox.information(self, "Sucesso", "Usuário cadastrado com sucesso.")
                else:
                    QMessageBox.warning(self, "Atenção", msg or "Não foi possível cadastrar.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao cadastrar: {e}")


class RegisterUserDialog(QDialog):
    """Diálogo de cadastro de Usuário (admin-restrito)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cadastrar Usuário")
        self.setModal(True)
        self.data = {}

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nome completo")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Usuário")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email (opcional)")
        self.pw_input = QLineEdit(); self.pw_input.setEchoMode(QLineEdit.Password)
        self.pw_input.setPlaceholderText("Senha")
        self.pw2_input = QLineEdit(); self.pw2_input.setEchoMode(QLineEdit.Password)
        self.pw2_input.setPlaceholderText("Confirmar senha")
        self.admin_checkbox = QCheckBox("Administrador")
        self.admin_checkbox.setToolTip("Marque para cadastrar como administrador")
        # Feedback de validação
        self.err_name = QLabel(""); self.err_name.setObjectName("errorLabel")
        self.err_user = QLabel(""); self.err_user.setObjectName("errorLabel")
        self.err_pw = QLabel(""); self.err_pw.setObjectName("errorLabel")
        self.err_pw2 = QLabel(""); self.err_pw2.setObjectName("errorLabel")
        form.addRow("Nome:", self.name_input)
        form.addRow("", self.err_name)
        form.addRow("Usuário:", self.username_input)
        form.addRow("", self.err_user)
        form.addRow("Email:", self.email_input)
        form.addRow("É admin?:", self.admin_checkbox)
        form.addRow("Senha:", self.pw_input)
        form.addRow("", self.err_pw)
        form.addRow("Confirmar:", self.pw2_input)
        form.addRow("", self.err_pw2)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._ok_button = buttons.button(QDialogButtonBox.Ok)
        self._ok_button.setEnabled(False)

        # Validação em tempo real
        self.name_input.textChanged.connect(self._validate)
        self.username_input.textChanged.connect(self._validate)
        self.pw_input.textChanged.connect(self._validate)
        self.pw2_input.textChanged.connect(self._validate)
        try:
            self._validate()
        except Exception:
            pass

    def _on_accept(self):
        name = self.name_input.text().strip()
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        pw = self.pw_input.text().strip()
        pw2 = self.pw2_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Erro", "Informe o nome completo.")
            return
        if not username or len(username) < 3:
            QMessageBox.warning(self, "Erro", "Informe um usuário válido (mín. 3 caracteres).")
            return
        # Email é opcional; se preenchido, valida formato
        if email:
            import re as _re
            if not _re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                QMessageBox.warning(self, "Erro", "Informe um email válido.")
                return
        if len(pw) < 8:
            QMessageBox.warning(self, "Erro", "A senha deve ter ao menos 8 caracteres.")
            return
        # Requisitos mínimos de segurança
        import re as _re
        has_upper = bool(_re.search(r"[A-Z]", pw))
        has_lower = bool(_re.search(r"[a-z]", pw))
        has_digit = bool(_re.search(r"\d", pw))
        if not (has_upper and has_lower and has_digit):
            QMessageBox.warning(self, "Erro", "Senha deve conter maiúsculas, minúsculas e números.")
            return
        if pw != pw2:
            QMessageBox.warning(self, "Erro", "As senhas não coincidem.")
            return

        role = "admin" if self.admin_checkbox.isChecked() else "judge"
        self.data = {"name": name, "username": username, "email": email, "password": pw, "role": role}
        self.accept()

    def _set_error(self, widget: QLineEdit, label: QLabel, msg: str):
        label.setText(msg)
        if msg:
            widget.setStyleSheet("QLineEdit{border: 1px solid #d9534f; padding: 6px; color: black;} QLineEdit::placeholder{ color: #222;}")
        else:
            widget.setStyleSheet("QLineEdit{border: none; padding: 6px; color: black;} QLineEdit::placeholder{ color: #222;}")

    def _validate(self):
        name = self.name_input.text().strip()
        username = self.username_input.text().strip()
        pw = self.pw_input.text()
        pw2 = self.pw2_input.text()

        import re as _re
        ok_name = len(name) >= 3
        ok_user = bool(_re.match(r"^[A-Za-z0-9_.-]{3,64}$", username))
        ok_pw_len = len(pw) >= 8
        ok_pw_comp = bool(_re.search(r"[A-Z]", pw)) and bool(_re.search(r"[a-z]", pw)) and bool(_re.search(r"\d", pw))
        ok_pw2 = pw == pw2

        self._set_error(self.name_input, self.err_name, "" if ok_name else "Informe ao menos 3 caracteres.")
        self._set_error(self.username_input, self.err_user, "" if ok_user else "Usuário inválido (3-64, letras/números/._-).")
        self._set_error(self.pw_input, self.err_pw, "" if (ok_pw_len and ok_pw_comp) else "Senha min. 8 c/ maiúscula, minúscula e número.")
        self._set_error(self.pw2_input, self.err_pw2, "" if ok_pw2 else "As senhas não coincidem.")

        all_ok = ok_name and ok_user and ok_pw_len and ok_pw_comp and ok_pw2
        if hasattr(self, '_ok_button') and self._ok_button is not None:
            self._ok_button.setEnabled(all_ok)


class AdminAuthDialog(QDialog):
    """Diálogo de autenticação para ações administrativas (ex.: cadastrar juiz)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Autenticação de Administrador")
        self.setModal(True)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.user_input = QLineEdit(); self.user_input.setPlaceholderText("Usuário admin")
        self.pw_input = QLineEdit(); self.pw_input.setEchoMode(QLineEdit.Password); self.pw_input.setPlaceholderText("Senha")
        form.addRow("Usuário:", self.user_input)
        form.addRow("Senha:", self.pw_input)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        username = self.user_input.text().strip()
        password = self.pw_input.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Erro", "Informe usuário e senha.")
            return
        try:
            from db.user_repository import UserRepository
            repo = UserRepository()
            ok, msg = repo.authenticate_admin(username=username, password=password)
            repo.close()
            if ok:
                # Guardar credenciais validadas para chamada backend posterior
                self.auth_user = username
                self.auth_password = password
                self.accept()
                return
            QMessageBox.warning(self, "Atenção", msg or "Credenciais de admin inválidas.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao autenticar: {e}")
