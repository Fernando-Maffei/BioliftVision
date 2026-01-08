import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QPushButton, QLabel, QTextEdit, QDialogButtonBox, QMessageBox,
    QListWidget, QListWidgetItem, QFrame, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt

from common.logger import log_info, log_warning, log_error
from common.paths import app_root


def _storage_path() -> str:
    root = app_root()
    storage_dir = os.path.join(root, 'storage')
    os.makedirs(storage_dir, exist_ok=True)
    return os.path.join(storage_dir, 'db_connections.json')


def _load_history() -> List[Dict[str, Any]]:
    try:
        path = _storage_path()
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f) or []
    except Exception:
        pass
    return []


def _save_history(entry: Dict[str, Any]) -> None:
    try:
        items = _load_history()
        # remove duplicates (same provider/server/db)
        items = [i for i in items if not (i.get('provider') == entry.get('provider') and i.get('server') == entry.get('server') and i.get('database') == entry.get('database'))]
        entry['ts'] = datetime.utcnow().isoformat()
        items.insert(0, entry)
        items = items[:10]
        with open(_storage_path(), 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log_warning(f"Falha ao salvar histórico de conexões: {e}")


class DatabaseConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuração de Banco de Dados")
        self.setModal(True)
        self.setMinimumSize(720, 560)
        try:
            self.setSizeGripEnabled(True)
        except Exception:
            pass
        self._build_ui()
        self._bind_events()
        self._load_saved()
        self._refresh_state()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        form = QFormLayout()

        self.provider_input = QComboBox(); self.provider_input.addItems(["SQL Server", "PostgreSQL", "MySQL"])
        self.server_input = QLineEdit(); self.server_input.setPlaceholderText("ex.: localhost\\SQLEXPRESS ou 192.168.0.10")
        self.auth_input = QComboBox(); self.auth_input.addItems(["Windows", "SQL Server"])  # apenas para MSSQL
        self.user_input = QLineEdit(); self.user_input.setPlaceholderText("usuário")
        self.password_input = QLineEdit(); self.password_input.setEchoMode(QLineEdit.Password); self.password_input.setPlaceholderText("senha")
        self.dbname_input = QComboBox(); self.dbname_input.setEditable(True); self.dbname_input.setInsertPolicy(QComboBox.NoInsert)

        form.addRow("Provedor:", self.provider_input)
        form.addRow("Servidor:", self.server_input)
        form.addRow("Autenticação:", self.auth_input)
        form.addRow("Usuário:", self.user_input)
        form.addRow("Senha:", self.password_input)
        row_db = QHBoxLayout();
        row_db.addWidget(self.dbname_input)
        self.btn_list_db = QPushButton("Listar Bancos")
        row_db.addWidget(self.btn_list_db)
        container_db = QFrame(); container_db.setLayout(row_db)
        form.addRow("Banco:", container_db)

        layout.addLayout(form)

        self.conn_str_view = QTextEdit(); self.conn_str_view.setReadOnly(True); self.conn_str_view.setMaximumHeight(90)
        layout.addWidget(QLabel("String de conexão (somente leitura):"))
        layout.addWidget(self.conn_str_view)

        # Histórico
        layout.addWidget(QLabel("Conexões recentes:"))
        self.history_list = QListWidget(); self.history_list.setMaximumHeight(140)
        layout.addWidget(self.history_list)

        # Ações
        actions = QHBoxLayout()
        self.btn_test = QPushButton("Testar Conexão")
        self.btn_save = QPushButton("Salvar Configuração")
        self.btn_load = QPushButton("Carregar Selecionada")
        actions.addWidget(self.btn_test)
        actions.addWidget(self.btn_save)
        actions.addWidget(self.btn_load)
        layout.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _bind_events(self):
        for w in (self.provider_input, self.server_input, self.auth_input, self.user_input, self.password_input):
            try:
                if hasattr(w, 'textChanged'):
                    w.textChanged.connect(self._on_fields_changed)
            except Exception:
                pass
        try:
            self.provider_input.currentIndexChanged.connect(self._on_fields_changed)
            self.auth_input.currentIndexChanged.connect(self._on_fields_changed)
            try:
                self.dbname_input.editTextChanged.connect(self._on_fields_changed)
            except Exception:
                pass
            self.btn_test.clicked.connect(self._on_test)
            self.btn_save.clicked.connect(self._on_save)
            self.btn_load.clicked.connect(self._on_load_selected)
            self.history_list.itemDoubleClicked.connect(self._on_load_item)
            self.btn_list_db.clicked.connect(self._on_list_databases)
        except Exception:
            pass

    def _refresh_state(self):
        provider = self.provider_input.currentText()
        is_mssql = provider == "SQL Server"
        use_windows = self.auth_input.currentText() == "Windows"
        self.auth_input.setEnabled(is_mssql)
        self.user_input.setEnabled(not (is_mssql and use_windows))
        self.password_input.setEnabled(not (is_mssql and use_windows))
        self._update_conn_str_view()

    def _on_fields_changed(self):
        self._refresh_state()

    def _update_conn_str_view(self):
        provider = self.provider_input.currentText()
        server = self.server_input.text().strip()
        db = self.dbname_input.currentText().strip() or "bioliftvisionDB"
        user = self.user_input.text().strip()
        use_windows = self.auth_input.currentText() == "Windows"
        if provider == "SQL Server":
            parts = [f"DRIVER={{ODBC Driver 17 for SQL Server}}", f"SERVER={server}", f"DATABASE={db}"]
            if use_windows:
                parts.append("Trusted_Connection=yes")
            else:
                parts.append(f"UID={user or '<usuario>'}")
                parts.append("PWD=<protegida>")
            parts.append("Encrypt=yes"); parts.append("TrustServerCertificate=yes")
            self.conn_str_view.setPlainText(";".join(parts))
        elif provider == "PostgreSQL":
            self.conn_str_view.setPlainText(f"host={server} dbname={db} user={user or '<usuario>'} password=<protegida> sslmode=prefer")
        else:
            self.conn_str_view.setPlainText(f"mysql+connector://{user or '<usuario>'}:<protegida>@{server}/{db}")

    def _collect_params(self) -> Dict[str, Any]:
        return {
            'provider': self.provider_input.currentText(),
            'server': self.server_input.text().strip(),
            'database': (self.dbname_input.currentText().strip() or 'bioliftvisionDB'),
            'auth': self.auth_input.currentText(),
            'username': self.user_input.text().strip(),
            'password': self.password_input.text(),
        }

    def _validate(self, params: Dict[str, Any]) -> Optional[str]:
        if not params['server']:
            return "Informe o servidor (hostname/IP)."
        provider = params['provider']
        if provider == 'SQL Server' and params['auth'] == 'Windows':
            return None
        # Usuário e senha obrigatórios para as demais situações
        if not params['username']:
            return "Informe o usuário."
        if not params['password']:
            return "Informe a senha."
        return None

    def _on_test(self):
        params = self._collect_params()
        err = self._validate(params)
        if err:
            QMessageBox.warning(self, "Campos inválidos", err)
            return
        try:
            from config.database import test_connection, connect_mssql
            provider = params['provider']
            ok = False; msg = None
            if provider == 'SQL Server':
                os.environ['MSSQL_SERVER'] = params['server']
                os.environ['MSSQL_DB'] = params['database']
                if params['auth'] == 'Windows':
                    os.environ['MSSQL_TRUSTED'] = 'true'
                    for k in ('MSSQL_USER','MSSQL_PASSWORD'):
                        if k in os.environ: os.environ.pop(k)
                else:
                    os.environ['MSSQL_TRUSTED'] = 'false'
                    os.environ['MSSQL_USER'] = params['username']
                    os.environ['MSSQL_PASSWORD'] = params['password']
                ok, msg = test_connection()
            else:
                # Testes opcionais para outros provedores
                try:
                    if provider == 'PostgreSQL':
                        import psycopg2  # type: ignore
                        conn = psycopg2.connect(host=params['server'], dbname=params['database'], user=params['username'], password=params['password'])
                        conn.close(); ok = True
                    elif provider == 'MySQL':
                        import mysql.connector  # type: ignore
                        conn = mysql.connector.connect(host=params['server'], database=params['database'], user=params['username'], password=params['password'])
                        conn.close(); ok = True
                except Exception as e:
                    ok = False; msg = str(e)
            if ok:
                log_info("Teste de conexão bem-sucedido")
                QMessageBox.information(self, "Conexão", "Conexão validada com sucesso.")
            else:
                log_warning(f"Teste de conexão falhou: {msg}")
                QMessageBox.warning(self, "Conexão", f"Falha ao conectar: {msg}")
        except Exception as e:
            log_error(f"Erro ao testar conexão: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao testar conexão: {e}")

    def _on_save(self):
        params = self._collect_params()
        err = self._validate(params)
        if err:
            QMessageBox.warning(self, "Campos inválidos", err)
            return
        # Persistir sem senha (history) e senha via keyring
        try:
            _save_history({k: params[k] for k in ('provider','server','database','auth','username')})
            try:
                import keyring
                key_id = f"{params['provider']}|{params['server']}|{params['database']}|{params['username'] or 'windows'}"
                keyring.set_password("BioLiftVision-DB", key_id, params['password'])
            except Exception:
                QMessageBox.information(self, "Armazenamento", "Keyring indisponível. A senha não foi salva.")
            # Aplicar para uso corrente (MSSQL)
            if params['provider'] == 'SQL Server':
                os.environ['MSSQL_SERVER'] = params['server']
                os.environ['MSSQL_DB'] = params['database']
                if params['auth'] == 'Windows':
                    os.environ['MSSQL_TRUSTED'] = 'true'
                    for k in ('MSSQL_USER','MSSQL_PASSWORD'):
                        if k in os.environ: os.environ.pop(k)
                else:
                    os.environ['MSSQL_TRUSTED'] = 'false'
                    os.environ['MSSQL_USER'] = params['username']
                    os.environ['MSSQL_PASSWORD'] = params['password']
            QMessageBox.information(self, "Configuração", "Configuração salva com sucesso.")
        except Exception as e:
            log_error(f"Erro ao salvar configuração: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao salvar configuração: {e}")

    def _on_list_databases(self):
        try:
            provider = self.provider_input.currentText()
            server = self.server_input.text().strip()
            auth = self.auth_input.currentText()
            user = self.user_input.text().strip()
            password = self.password_input.text()
            if not server:
                QMessageBox.warning(self, "Listar", "Informe o servidor.")
                return
            items = []
            if provider == 'SQL Server':
                from config.database import list_mssql_databases
                items = list_mssql_databases(server, auth, user, password)
            elif provider == 'PostgreSQL':
                from config.database import list_postgres_databases
                if not user or not password:
                    QMessageBox.warning(self, "Listar", "Informe usuário e senha.")
                    return
                items = list_postgres_databases(server, user, password)
            else:
                from config.database import list_mysql_databases
                if not user or not password:
                    QMessageBox.warning(self, "Listar", "Informe usuário e senha.")
                    return
                items = list_mysql_databases(server, user, password)
            if not items:
                QMessageBox.information(self, "Listar", "Nenhum banco encontrado ou acesso negado.")
                return
            self.dbname_input.clear()
            self.dbname_input.addItems(items)
            self.dbname_input.setCurrentIndex(0)
        except Exception as e:
            log_error(f"Erro ao listar bancos: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao listar bancos: {e}")

    def _load_saved(self):
        try:
            items = _load_history()
            self.history_list.clear()
            for it in items:
                label = f"{it.get('provider')} - {it.get('server')} ({it.get('database')})"
                li = QListWidgetItem(label)
                li.setData(Qt.UserRole, it)
                self.history_list.addItem(li)
        except Exception:
            pass

    def _on_load_selected(self):
        item = self.history_list.currentItem()
        if item:
            self._apply_item(item)

    def _on_load_item(self, item: QListWidgetItem):
        self._apply_item(item)

    def _apply_item(self, item: QListWidgetItem):
        try:
            data = item.data(Qt.UserRole) or {}
            self.provider_input.setCurrentText(data.get('provider', 'SQL Server'))
            self.server_input.setText(data.get('server', ''))
            self.dbname_input.setText(data.get('database', ''))
            self.auth_input.setCurrentText(data.get('auth', 'SQL Server'))
            self.user_input.setText(data.get('username', ''))
            try:
                import keyring
                key_id = f"{data.get('provider')}|{data.get('server')}|{data.get('database')}|{data.get('username') or 'windows'}"
                pw = keyring.get_password("BioLiftVision-DB", key_id)
                if pw:
                    self.password_input.setText(pw)
            except Exception:
                pass
            self._refresh_state()
        except Exception:
            pass
