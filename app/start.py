import sys
import os

_base_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.abspath(os.path.join(_base_dir, '..'))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

from common.logger import log_info, log_error
from config.database import load_env, test_connection


def main():
    load_env()
    ok, err = test_connection()
    if not ok:
        log_error(err or "Falha de conexão MSSQL")
        sys.exit(2)
    log_info("Conexão MSSQL validada")
    import main as _app
    _app.main()


if __name__ == "__main__":
    main()
