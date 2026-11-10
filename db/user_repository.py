import hashlib
import secrets
from typing import Tuple, Optional

from .db_connection import DatabaseConnection


class UserRepository:
    """Persistência de usuários em SQL Server usando pyodbc."""

    def __init__(self):
        self.db = DatabaseConnection()
        self.conn = None

    def connect(self):
        if self.conn is None:
            self.conn = self.db.connect()
        return self.conn is not None

    def close(self):
        try:
            self.db.disconnect()
        except Exception:
            pass
        self.conn = None

    def ensure_users_table(self) -> bool:
        if not self.connect():
            return False
        sql = (
            "IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[users]') AND type in (N'U')) "
            "BEGIN "
            "CREATE TABLE [dbo].[users] ("
            " id INT IDENTITY(1,1) PRIMARY KEY,"
            " name NVARCHAR(120) NOT NULL,"
            " username NVARCHAR(64) NOT NULL UNIQUE,"
            " email NVARCHAR(255) NULL,"
            " password_hash NVARCHAR(256) NOT NULL,"
            " salt NVARCHAR(64) NOT NULL,"
            " role NVARCHAR(32) NOT NULL DEFAULT 'judge',"
            " is_admin BIT NOT NULL DEFAULT 0,"
            " is_active BIT NOT NULL DEFAULT 1,"
            " created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()"
            ")"
            " END;"
            # Adiciona coluna is_admin se tabela já existir e faltar
            " IF COL_LENGTH('dbo.users','is_admin') IS NULL BEGIN "
            " ALTER TABLE dbo.users ADD is_admin BIT NOT NULL DEFAULT 0; "
            " END;"
        )
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def _hash_password(password: str, salt_hex: str) -> str:
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return dk.hex()

    def create_user(self, name: str, username: str, email: Optional[str], password: str, role: str = "judge") -> Tuple[bool, Optional[str]]:
        """Cria usuário no banco. Retorna (ok, mensagem_erro)."""
        if not self.ensure_users_table():
            return False, "Conexão indisponível ou falha ao garantir tabela."

        try:
            # Verificar se usuário já existe
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(1) FROM [dbo].[users] WHERE username = ?", (username,))
            exists = cur.fetchone()[0] > 0
            if exists:
                return False, "Usuário já cadastrado."

            salt = secrets.token_hex(16)
            password_hash = self._hash_password(password, salt)
            is_admin = 1 if (role or "judge").lower() == "admin" else 0
            cur.execute(
                "INSERT INTO [dbo].[users] (name, username, email, password_hash, salt, role, is_active, is_admin)"
                " VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
                (name, username, email, password_hash, salt, role, is_admin),
            )
            self.conn.commit()
            return True, None
        except Exception as e:
            return False, str(e)

    def create_user_as_admin(
        self,
        admin_username: str,
        admin_password: str,
        *,
        name: str,
        username: str,
        email: Optional[str],
        password: str,
        role: str = "judge",
    ) -> Tuple[bool, Optional[str]]:
        """Cria usuário apenas se credenciais de admin forem válidas.
        Retorna (ok, mensagem_erro).
        """
        # Verifica tabela e autenticação de admin
        if not self.ensure_users_table():
            return False, "Conexão indisponível ou falha ao garantir tabela."
        ok_admin, msg_admin = self.authenticate_admin(admin_username, admin_password)
        if not ok_admin:
            return False, msg_admin or "Permissão negada: somente administradores podem cadastrar usuários."

        # Regras mínimas de segurança de senha (defesa em profundidade)
        if password is None or len(password) < 8:
            return False, "Senha muito curta (mínimo 8 caracteres)."
        try:
            import re as _re
            has_upper = bool(_re.search(r"[A-Z]", password))
            has_lower = bool(_re.search(r"[a-z]", password))
            has_digit = bool(_re.search(r"\d", password))
            if not (has_upper and has_lower and has_digit):
                return False, "Senha deve conter maiúsculas, minúsculas e números."
        except Exception:
            pass

        # Cria usuário usando fluxo padrão
        return self.create_user(name=name, username=username, email=email, password=password, role=role)

    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Autentica usuário por usuário/senha."""
        if not self.ensure_users_table():
            return False, "Conexão indisponível ou tabela ausente."
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT id, password_hash, salt, is_active FROM [dbo].[users] WHERE username = ?",
                (username,),
            )
            row = cur.fetchone()
            if not row:
                return False, "Usuário não encontrado."
            _, stored_hash, salt, is_active = row
            if not is_active:
                return False, "Usuário inativo."
            calc_hash = self._hash_password(password, salt)
            if calc_hash == stored_hash:
                return True, None
            return False, "Senha incorreta."
        except Exception as e:
            return False, str(e)

    def authenticate_admin(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Autentica e valida privilégios de administrador (role = 'admin')."""
        if not self.ensure_users_table():
            return False, "Conexão indisponível ou tabela ausente."
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT id, password_hash, salt, is_active, role, is_admin FROM [dbo].[users] WHERE username = ?",
                (username,),
            )
            row = cur.fetchone()
            if not row:
                return False, "Usuário não encontrado."
            _, stored_hash, salt, is_active, role, is_admin = row
            if not is_active:
                return False, "Usuário inativo."
            is_admin_flag = bool(is_admin) or ("admin" in (role or "judge").lower())
            if not is_admin_flag:
                return False, "Usuário não possui privilégios de administrador."
            calc_hash = self._hash_password(password, salt)
            if calc_hash == stored_hash:
                return True, None
            return False, "Senha incorreta."
        except Exception as e:
            return False, str(e)

    def get_user_role(self, username: str) -> Optional[str]:
        """Obtém a role do usuário. Retorna None em caso de erro ou usuário inexistente."""
        if not self.ensure_users_table():
            return None
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT role FROM [dbo].[users] WHERE username = ?",
                (username,),
            )
            row = cur.fetchone()
            if not row:
                return None
            role = row[0] or "judge"
            return role
        except Exception:
            return None
