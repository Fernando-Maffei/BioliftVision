from contextlib import contextmanager
from typing import Iterator, Tuple

from common.logger import log_info, log_error
from config.database import connect_mssql


def get_connection(autocommit: bool = False):
    try:
        return connect_mssql(autocommit=autocommit)
    except Exception as e:
        log_error(f"Não foi possível obter conexão MSSQL: {e}")
        raise


@contextmanager
def transaction(conn) -> Iterator[Tuple[object, object]]:
    cur = None
    try:
        cur = conn.cursor()
        yield conn, cur
        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        log_error(f"Transação MSSQL falhou: {e}")
        raise
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
