import os
import socket
from typing import Optional, Tuple

from common.logger import log_info, log_warning, log_error


def _read_env_file(path: str) -> None:
    try:
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k, v)
    except Exception as e:
        log_warning(f"Falha ao carregar env file '{path}': {e}")


def load_env() -> None:
    env = os.environ.get("APP_ENV", "dev").strip().lower()
    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
    base = os.path.join(root, ".env")
    env_file = os.path.join(root, f".env.{env}")
    _read_env_file(base)
    _read_env_file(env_file)
    # Aplicar configuração salva (se houver) para MSSQL
    try:
        cfg_path = os.path.join(root, 'storage', 'db_connections.json')
        if os.path.exists(cfg_path):
            import json as _json
            with open(cfg_path, 'r', encoding='utf-8') as f:
                items = _json.load(f) or []
            if items:
                cfg = items[0]
                if (cfg.get('provider') or '').lower() == 'sql server':
                    os.environ.setdefault('MSSQL_SERVER', cfg.get('server', 'localhost'))
                    os.environ.setdefault('MSSQL_DB', cfg.get('database', 'bioliftvisionDB'))
                    auth = (cfg.get('auth') or 'SQL Server').lower()
                    if auth == 'windows':
                        os.environ.setdefault('MSSQL_TRUSTED', 'true')
                    else:
                        os.environ.setdefault('MSSQL_TRUSTED', 'false')
                        import keyring as _keyring  # type: ignore
                        key_id = f"{cfg.get('provider')}|{cfg.get('server')}|{cfg.get('database')}|{cfg.get('username') or 'windows'}"
                        try:
                            pw = _keyring.get_password("BioLiftVision-DB", key_id)
                        except Exception:
                            pw = None
                        if cfg.get('username'):
                            os.environ.setdefault('MSSQL_USER', cfg.get('username'))
                        if pw:
                            os.environ.setdefault('MSSQL_PASSWORD', pw)
    except Exception:
        pass

    try:
        if not os.environ.get('MSSQL_SERVER'):
            import socket as _socket
            import winreg
            names = []
            for path in (
                r"SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL",
                r"SOFTWARE\WOW6432Node\Microsoft\Microsoft SQL Server\Instance Names\SQL",
            ):
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                    i = 0
                    while True:
                        try:
                            name, _, _ = winreg.EnumValue(key, i)
                            names.append(name)
                            i += 1
                        except OSError:
                            break
                except Exception:
                    pass
            if names:
                host = _socket.gethostname()
                uniq = sorted(set(names))
                if 'MSSQLSERVER' in uniq:
                    os.environ.setdefault('MSSQL_SERVER', host)
                else:
                    os.environ.setdefault('MSSQL_SERVER', f"{host}\\{uniq[0]}")
    except Exception:
        pass


def _detect_driver() -> Optional[str]:
    try:
        import pyodbc  # type: ignore
        available = [d.strip() for d in pyodbc.drivers()]
        for cand in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server"):
            if cand in available:
                return cand
        return None
    except Exception as e:
        log_warning(f"Detecção de driver ODBC falhou: {e}")
        return None


def _resolve_driver() -> str:
    drv = os.environ.get("MSSQL_DRIVER")
    if drv:
        return drv
    det = _detect_driver()
    if det:
        os.environ["MSSQL_DRIVER"] = det
        return det
    return "ODBC Driver 17 for SQL Server"


def _trusted_connection_enabled() -> bool:
    return os.environ.get("MSSQL_TRUSTED", "false").strip().lower() in ("1", "true", "yes")


def _conn_params() -> dict:
    host = os.environ.get("MSSQL_SERVER", "localhost")
    db = os.environ.get("MSSQL_DB", "bioliftvisionDB")
    user = os.environ.get("MSSQL_USER")
    pwd = os.environ.get("MSSQL_PASSWORD")
    enc = os.environ.get("MSSQL_ENCRYPT", "yes")
    tsc = os.environ.get("MSSQL_TRUST_SERVER_CERT", "yes")
    timeout = os.environ.get("MSSQL_TIMEOUT", "30")
    return {
        "driver": _resolve_driver(),
        "server": host,
        "database": db,
        "username": user,
        "password": pwd,
        "encrypt": enc,
        "trust_server_certificate": tsc,
        "timeout": timeout,
        "trusted": _trusted_connection_enabled(),
    }


def _build_connection_string() -> str:
    p = _conn_params()
    parts = [
        f"DRIVER={{{p['driver']}}}",
        f"SERVER={p['server']}",
        f"DATABASE={p['database']}",
    ]
    if p["trusted"]:
        parts.append("Trusted_Connection=yes")
    else:
        if not p["username"] or not p["password"]:
            raise ValueError("Credenciais MSSQL ausentes: defina MSSQL_USER e MSSQL_PASSWORD ou MSSQL_TRUSTED=true")
        parts.append(f"UID={p['username']}")
        parts.append(f"PWD={p['password']}")
    parts.append(f"Encrypt={p['encrypt']}")
    parts.append(f"TrustServerCertificate={p['trust_server_certificate']}")
    parts.append(f"Connection Timeout={p['timeout']}")
    return ";".join(parts)


def connect_mssql(autocommit: bool = False):
    try:
        import pyodbc  # type: ignore
        load_env()
        params = _conn_params()
        try:
            available = [d.strip() for d in pyodbc.drivers()]
        except Exception:
            available = []
        if params["driver"] not in available:
            log_error(f"Driver ODBC não encontrado: {params['driver']}. Instale ODBC Driver 17/18 for SQL Server.")
            raise RuntimeError(f"Driver ODBC ausente: {params['driver']}")
        cs = _build_connection_string()
        safe = cs.replace("PWD=", "PWD=***")
        log_info(f"Conectando MSSQL: {safe}")
        conn = pyodbc.connect(cs, autocommit=autocommit)
        return conn
    except Exception as e:
        msg = str(e)
        if "data source name not found" in msg.lower() or "driver" in msg.lower():
            log_error("Driver ODBC ausente ou inválido. Instale 'ODBC Driver 17/18 for SQL Server'.")
        elif "login failed" in msg.lower() or "28000" in msg:
            log_error("Falha de login no SQL Server (usuário/senha). Verifique MSSQL_USER/MSSQL_PASSWORD.")
        elif "timeout" in msg.lower() or "08001" in msg:
            log_error("Timeout de conexão. Verifique servidor, rede e porta do SQL Server.")
        else:
            log_error(f"Erro de conexão MSSQL: {e}")
        raise


# --------- PROVEDORES ADICIONAIS (opcionais) ---------

def connect_postgres(host: str, db: str, user: str, password: str):
    try:
        import psycopg2  # type: ignore
        return psycopg2.connect(host=host, dbname=db, user=user, password=password)
    except Exception as e:
        log_error(f"Erro ao conectar PostgreSQL: {e}")
        raise


def connect_mysql(host: str, db: str, user: str, password: str):
    try:
        import mysql.connector  # type: ignore
        return mysql.connector.connect(host=host, database=db, user=user, password=password)
    except Exception as e:
        log_error(f"Erro ao conectar MySQL: {e}")
        raise


def list_mssql_databases(server: str, auth: str, user: Optional[str], password: Optional[str]) -> list:
    try:
        import pyodbc  # type: ignore
        drv = _resolve_driver()
        parts = [f"DRIVER={{{drv}}}", f"SERVER={server}", "DATABASE=master"]
        if (auth or "").strip().lower() == "windows":
            parts.append("Trusted_Connection=yes")
        else:
            parts.append(f"UID={user or ''}")
            parts.append(f"PWD={password or ''}")
        parts.append("Encrypt=yes")
        parts.append("TrustServerCertificate=yes")
        parts.append("Connection Timeout=10")
        cs = ";".join(parts)
        conn = pyodbc.connect(cs, autocommit=True)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sys.databases WHERE state=0 ORDER BY name")
        rows = [r[0] for r in cur.fetchall()]
        try:
            cur.close(); conn.close()
        except Exception:
            pass
        return rows
    except Exception as e:
        log_warning(f"Falha ao listar bancos MSSQL: {e}")
        return []


def list_postgres_databases(host: str, user: str, password: str) -> list:
    try:
        import psycopg2  # type: ignore
        conn = psycopg2.connect(host=host, dbname="postgres", user=user, password=password)
        cur = conn.cursor()
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname")
        rows = [r[0] for r in cur.fetchall()]
        try:
            cur.close(); conn.close()
        except Exception:
            pass
        return rows
    except Exception as e:
        log_warning(f"Falha ao listar bancos Postgres: {e}")
        return []


def list_mysql_databases(host: str, user: str, password: str) -> list:
    try:
        import mysql.connector  # type: ignore
        conn = mysql.connector.connect(host=host, user=user, password=password)
        cur = conn.cursor()
        cur.execute("SHOW DATABASES")
        rows = [r[0] for r in cur.fetchall()]
        try:
            cur.close(); conn.close()
        except Exception:
            pass
        return rows
    except Exception as e:
        log_warning(f"Falha ao listar bancos MySQL: {e}")
        return []


def test_connection() -> Tuple[bool, Optional[str]]:
    try:
        conn = connect_mssql(autocommit=True)
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            _ = cur.fetchone()
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return True, None
    except Exception as e:
        host = os.environ.get("MSSQL_SERVER", "localhost")
        hn = socket.gethostname()
        return False, f"Conexão falhou para '{host}' em '{hn}': {e}"

