from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .mssql_connection import get_connection, transaction


BASE_TABLE = "dbo.Analises"
LOG_TABLE = "dbo.Analises_Log"


SCHEMA_SQL = f"""
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID(N'{BASE_TABLE}') AND type in (N'U'))
BEGIN
    CREATE TABLE {BASE_TABLE} (
        ID_ANALISE INT IDENTITY(1,1) PRIMARY KEY,
        NOTA DECIMAL(18,4) NULL,
        OBSERVACAO_JUIZ NVARCHAR(MAX) NULL,
        DATA_CRIACAO DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        DATA_ATUALIZACAO DATETIME2 NULL,
        STATUS NVARCHAR(50) NULL,
        JUIZ NVARCHAR(150) NULL
    );
END

IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID(N'{LOG_TABLE}') AND type in (N'U'))
BEGIN
    CREATE TABLE {LOG_TABLE} (
        LOG_ID INT IDENTITY(1,1) PRIMARY KEY,
        ID_ANALISE INT NOT NULL,
        ACTION NVARCHAR(20) NOT NULL, -- CREATE/UPDATE/DELETE
        FIELD_NAME NVARCHAR(128) NULL,
        OLD_VALUE NVARCHAR(MAX) NULL,
        NEW_VALUE NVARCHAR(MAX) NULL,
        CHANGED_AT DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        CHANGED_BY NVARCHAR(150) NULL,
        CONSTRAINT FK_AnalisesLog_Analises FOREIGN KEY (ID_ANALISE)
            REFERENCES {BASE_TABLE}(ID_ANALISE)
    );
END

-- Helper procedure to add columns dynamically
IF OBJECT_ID('dbo.AddColumnIfNotExists', 'P') IS NULL
    EXEC('CREATE PROCEDURE dbo.AddColumnIfNotExists AS RETURN 0');
GO
ALTER PROCEDURE dbo.AddColumnIfNotExists
    @TableName SYSNAME,
    @ColumnName SYSNAME,
    @ColumnType NVARCHAR(200)
AS
BEGIN
    SET NOCOUNT ON;
    IF NOT EXISTS (
        SELECT 1 FROM sys.columns c
        JOIN sys.objects o ON o.object_id = c.object_id
        WHERE o.type = 'U' AND o.name = @TableName AND c.name = @ColumnName
    )
    BEGIN
        DECLARE @sql NVARCHAR(MAX) = N'ALTER TABLE ' + QUOTENAME(@TableName) +
            N' ADD ' + QUOTENAME(@ColumnName) + N' ' + @ColumnType + N' NULL';
        EXEC sp_executesql @sql;
    END
END
"""


def _infer_sql_type(value: Any) -> str:
    if value is None:
        return "NVARCHAR(MAX)"
    if isinstance(value, bool):
        return "BIT"
    if isinstance(value, int):
        return "INT"
    if isinstance(value, float):
        return "DECIMAL(18,4)"
    if isinstance(value, (dt.datetime, dt.date)):
        return "DATETIME2"
    return "NVARCHAR(MAX)"


class AnalysisRepository:
    """CRUD e utilitários para a tabela de Análises com log e campos dinâmicos."""

    def __init__(self):
        self.conn = get_connection(autocommit=False)

    # --- schema management ---
    def create_schema(self) -> None:
        with transaction(self.conn) as conn:
            cur = conn.cursor()
            cur.execute(SCHEMA_SQL)

    def backup_tables(self) -> List[str]:
        ts = dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        names = [f"Analises_backup_{ts}", f"AnalisesLog_backup_{ts}"]
        with transaction(self.conn) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * INTO dbo.{names[0]} FROM {BASE_TABLE}")
            cur.execute(f"SELECT * INTO dbo.{names[1]} FROM {LOG_TABLE}")
        return names

    def add_column_if_not_exists(self, column: str, sql_type: str) -> None:
        with transaction(self.conn) as conn:
            cur = conn.cursor()
            cur.execute("EXEC dbo.AddColumnIfNotExists @TableName=?, @ColumnName=?, @ColumnType=?",
                        (BASE_TABLE.split('.')[-1], column, sql_type))

    # --- validation ---
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(data)
        nota = out.get("NOTA")
        if nota is not None:
            try:
                out["NOTA"] = float(nota)
            except Exception:
                raise ValueError("NOTA deve ser um número (float).")
        obs = out.get("OBSERVACAO_JUIZ")
        if obs is not None:
            out["OBSERVACAO_JUIZ"] = str(obs)
        status = out.get("STATUS")
        if status is not None and len(str(status)) > 50:
            raise ValueError("STATUS deve ter até 50 caracteres.")
        juiz = out.get("JUIZ")
        if juiz is not None and len(str(juiz)) > 150:
            raise ValueError("JUIZ deve ter até 150 caracteres.")
        return out

    # --- logging helper ---
    def _log(self, analysis_id: int, action: str, field: Optional[str], old: Optional[Any], new: Optional[Any], changed_by: Optional[str]) -> None:
        with transaction(self.conn) as conn:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO {LOG_TABLE} (ID_ANALISE, ACTION, FIELD_NAME, OLD_VALUE, NEW_VALUE, CHANGED_BY) VALUES (?, ?, ?, ?, ?, ?)",
                (analysis_id, action, field, None if old is None else str(old), None if new is None else str(new), changed_by)
            )

    # --- CRUD ---
    def create(self, data: Dict[str, Any], changed_by: Optional[str] = None) -> int:
        data = self.validate(data)
        # Ensure dynamic columns exist
        base_cols = {"NOTA", "OBSERVACAO_JUIZ", "DATA_CRIACAO", "DATA_ATUALIZACAO", "STATUS", "JUIZ"}
        extra = {k: v for k, v in data.items() if k not in base_cols}
        for k, v in extra.items():
            self.add_column_if_not_exists(k, _infer_sql_type(v))

        # Build INSERT
        cols = list(base_cols | set(extra.keys()))
        # Always set DATA_CRIACAO if missing
        if "DATA_CRIACAO" not in data:
            data["DATA_CRIACAO"] = dt.datetime.utcnow()
        placeholders = ", ".join("?" for _ in cols)
        with transaction(self.conn) as conn:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO {BASE_TABLE} ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(data.get(c) for c in cols)
            )
            cur.execute("SELECT CAST(SCOPE_IDENTITY() AS INT)")
            new_id = cur.fetchone()[0]

        # Log all fields on CREATE
        for c in cols:
            self._log(new_id, "CREATE", c, None, data.get(c), changed_by)
        return new_id

    def read(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        with transaction(self.conn) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM {BASE_TABLE} WHERE ID_ANALISE = ?", (analysis_id,))
            row = cur.fetchone()
            if not row:
                return None
            columns = [c[0] for c in cur.description]
        return dict(zip(columns, row))

    def list(self, top: int = 100, where: Optional[str] = None, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        sql = f"SELECT TOP {top} * FROM {BASE_TABLE}"
        if where:
            sql += f" WHERE {where}"
        with transaction(self.conn) as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            columns = [c[0] for c in cur.description]
        return [dict(zip(columns, r)) for r in rows]

    def update(self, analysis_id: int, changes: Dict[str, Any], changed_by: Optional[str] = None) -> None:
        changes = self.validate(changes)
        # Ensure dynamic columns exist
        for k, v in changes.items():
            if k not in {"NOTA", "OBSERVACAO_JUIZ", "DATA_CRIACAO", "DATA_ATUALIZACAO", "STATUS", "JUIZ"}:
                self.add_column_if_not_exists(k, _infer_sql_type(v))
        # Fetch current for logging
        current = self.read(analysis_id) or {}
        changes["DATA_ATUALIZACAO"] = dt.datetime.utcnow()
        sets = ", ".join(f"{k} = ?" for k in changes.keys())
        with transaction(self.conn) as conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE {BASE_TABLE} SET {sets} WHERE ID_ANALISE = ?",
                tuple(changes.values()) + (analysis_id,)
            )
        # Log each change
        for k, v in changes.items():
            self._log(analysis_id, "UPDATE", k, current.get(k), v, changed_by)

    def delete(self, analysis_id: int, changed_by: Optional[str] = None) -> None:
        snapshot = self.read(analysis_id)
        with transaction(self.conn) as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {BASE_TABLE} WHERE ID_ANALISE = ?", (analysis_id,))
        # Log deletion (snapshot reference)
        self._log(analysis_id, "DELETE", None, snapshot, None, changed_by)
from typing import Any, Dict, Iterable, Optional, Tuple

from db.mssql_connection import get_connection, transaction


class AnalysisRepository:
    """Repositório para gerenciar análises judiciais no SQL Server.

    Funcionalidades:
    - CRUD completo
    - Campos dinâmicos: adicionados sob demanda
    - Log de alterações por campo
    - Validação e normalização de dados
    - Backups de tabelas
    """

    def __init__(self, schema: str = 'dbo', table: str = 'Analises', log_table: str = 'Analises_Log'):
        self.schema = schema
        self.table = table
        self.log_table = log_table
        self.base_columns = {
            'ID_ANALISE', 'NOTA', 'OBSERVACAO_JUIZ', 'DATA_CRIACAO', 'DATA_ATUALIZACAO', 'STATUS', 'JUIZ'
        }

    # --------------------- UTIL ---------------------
    def _infer_sql_type(self, value: Any) -> str:
        import datetime as dt
        if isinstance(value, bool):
            return 'BIT'
        if isinstance(value, int):
            return 'INT'
        if isinstance(value, float):
            return 'DECIMAL(18,4)'
        if isinstance(value, (dt.datetime, dt.date)):
            return 'DATETIME2'
        return 'NVARCHAR(MAX)'

    def _procedure_exists(self, cur, proc_name: str) -> bool:
        cur.execute("SELECT 1 FROM sys.objects WHERE type = 'P' AND name = ?", (proc_name,))
        return cur.fetchone() is not None

    def add_column_if_not_exists(self, column: str, sql_type: str) -> None:
        conn = get_connection()
        with transaction(conn) as (conn, cur):
            full_table = f"{self.schema}.{self.table}"
            if self._procedure_exists(cur, 'AddColumnIfNotExists'):
                cur.execute(f"EXEC {self.schema}.AddColumnIfNotExists @table_name=?, @column_name=?, @type=?",
                            (full_table, column, sql_type))
            else:
                cur.execute(
                    "SELECT 1 FROM sys.columns WHERE Name = ? AND Object_ID = Object_ID(?)",
                    (column, full_table)
                )
                exists = cur.fetchone() is not None
                if not exists:
                    cur.execute(f"ALTER TABLE {full_table} ADD [{column}] {sql_type}")

    def create_schema(self) -> None:
        conn = get_connection()
        with transaction(conn) as (conn, cur):
            # Create Analises
            cur.execute(f"""
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = '{self.table}' AND schema_id = SCHEMA_ID('{self.schema}'))
            BEGIN
                EXEC('CREATE TABLE {self.schema}.{self.table} (
                    ID_ANALISE INT IDENTITY(1,1) PRIMARY KEY,
                    NOTA DECIMAL(18,4) NULL,
                    OBSERVACAO_JUIZ NVARCHAR(MAX) NULL,
                    DATA_CRIACAO DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
                    DATA_ATUALIZACAO DATETIME2 NULL,
                    STATUS NVARCHAR(50) NULL,
                    JUIZ NVARCHAR(150) NULL
                )')
            END
            """)

            # Create Analises_Log
            cur.execute(f"""
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = '{self.log_table}' AND schema_id = SCHEMA_ID('{self.schema}'))
            BEGIN
                EXEC('CREATE TABLE {self.schema}.{self.log_table} (
                    LOG_ID INT IDENTITY(1,1) PRIMARY KEY,
                    ID_ANALISE INT NOT NULL,
                    ACTION NVARCHAR(20) NOT NULL,
                    FIELD_NAME NVARCHAR(128) NULL,
                    OLD_VALUE NVARCHAR(MAX) NULL,
                    NEW_VALUE NVARCHAR(MAX) NULL,
                    CHANGED_AT DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
                    CHANGED_BY NVARCHAR(150) NULL,
                    CONSTRAINT FK_{self.log_table}_{self.table} FOREIGN KEY (ID_ANALISE)
                        REFERENCES {self.schema}.{self.table}(ID_ANALISE)
                )')
            END
            """)

            # Create procedure AddColumnIfNotExists
            cur.execute(f"""
            IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE type = 'P' AND name = 'AddColumnIfNotExists' AND schema_id = SCHEMA_ID('{self.schema}'))
            BEGIN
                EXEC('CREATE PROCEDURE {self.schema}.AddColumnIfNotExists
                    @table_name NVARCHAR(128),
                    @column_name NVARCHAR(128),
                    @type NVARCHAR(128)
                AS
                BEGIN
                    SET NOCOUNT ON;
                    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE Name = @column_name AND Object_ID = Object_ID(@table_name))
                    BEGIN
                        DECLARE @sql NVARCHAR(MAX) = ''ALTER TABLE '' + @table_name + '' ADD ['' + @column_name + ''] '' + @type;
                        EXEC sp_executesql @sql;
                    END
                END')
            END
            """)

    # --------------------- VALIDAÇÃO ---------------------
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(data)
        if 'NOTA' in out and out['NOTA'] is not None:
            try:
                out['NOTA'] = float(out['NOTA'])
            except Exception:
                raise ValueError('NOTA deve ser um número.')
        for key in ['STATUS', 'JUIZ', 'OBSERVACAO_JUIZ']:
            if key in out and out[key] is not None:
                out[key] = str(out[key])
        return out

    # --------------------- CRUD ---------------------
    def _ensure_dynamic_columns(self, cur, data: Dict[str, Any]) -> None:
        full_table = f"{self.schema}.{self.table}"
        for k, v in data.items():
            if k.upper() not in self.base_columns:
                sql_type = self._infer_sql_type(v)
                # Try to call stored procedure if exists
                if self._procedure_exists(cur, 'AddColumnIfNotExists'):
                    cur.execute(f"EXEC {self.schema}.AddColumnIfNotExists @table_name=?, @column_name=?, @type=?",
                                (full_table, k, sql_type))
                else:
                    cur.execute(
                        "SELECT 1 FROM sys.columns WHERE Name = ? AND Object_ID = Object_ID(?)",
                        (k, full_table)
                    )
                    exists = cur.fetchone() is not None
                    if not exists:
                        cur.execute(f"ALTER TABLE {full_table} ADD [{k}] {sql_type}")

    def create(self, data: Dict[str, Any], changed_by: Optional[str] = None) -> int:
        data = self.validate(data)
        conn = get_connection()
        with transaction(conn) as (conn, cur):
            self._ensure_dynamic_columns(cur, data)
            cols = []
            vals = []
            params = []
            for k, v in data.items():
                cols.append(f"[{k}]")
                vals.append('?')
                params.append(v)
            # Always set DATA_ATUALIZACAO on create
            cols.append('[DATA_ATUALIZACAO]')
            vals.append('SYSUTCDATETIME()')
            sql = f"INSERT INTO {self.schema}.{self.table} ({', '.join(cols)}) VALUES ({', '.join(vals)})"
            cur.execute(sql, tuple(params))
            cur.execute("SELECT CAST(SCOPE_IDENTITY() AS INT)")
            analysis_id = cur.fetchone()[0]

            # Log create per field
            for k, v in data.items():
                cur.execute(
                    f"INSERT INTO {self.schema}.{self.log_table} (ID_ANALISE, ACTION, FIELD_NAME, OLD_VALUE, NEW_VALUE, CHANGED_BY) VALUES (?,?,?,?,?,?)",
                    (analysis_id, 'CREATE', k, None, str(v) if v is not None else None, changed_by)
                )

            return analysis_id

    def read(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        with transaction(conn) as (conn, cur):
            cur.execute(f"SELECT * FROM {self.schema}.{self.table} WHERE ID_ANALISE = ?", (analysis_id,))
            row = cur.fetchone()
            if not row:
                return None
            columns = [c[0] for c in cur.description]
            return {columns[i]: row[i] for i in range(len(columns))}

    def list(self, top: int = 100, where: Optional[str] = None, params: Iterable[Any] = ()) -> Iterable[Dict[str, Any]]:
        conn = get_connection()
        with transaction(conn) as (conn, cur):
            where_sql = f" WHERE {where}" if where else ""
            sql = f"SELECT TOP {int(top)} * FROM {self.schema}.{self.table}{where_sql} ORDER BY ID_ANALISE DESC"
            cur.execute(sql, tuple(params))
            columns = [c[0] for c in cur.description]
            for row in cur.fetchall():
                yield {columns[i]: row[i] for i in range(len(columns))}

    def update(self, analysis_id: int, changes: Dict[str, Any], changed_by: Optional[str] = None) -> None:
        changes = self.validate(changes)
        conn = get_connection()
        with transaction(conn) as (conn, cur):
            current = self.read(analysis_id)
            if not current:
                raise ValueError(f'Análise {analysis_id} não encontrada')

            self._ensure_dynamic_columns(cur, changes)

            set_parts = []
            params = []
            for k, v in changes.items():
                set_parts.append(f"[{k}] = ?")
                params.append(v)
            # bump updated at
            set_parts.append("[DATA_ATUALIZACAO] = SYSUTCDATETIME()")
            sql = f"UPDATE {self.schema}.{self.table} SET {', '.join(set_parts)} WHERE ID_ANALISE = ?"
            params.append(analysis_id)
            cur.execute(sql, tuple(params))

            # log per changed field
            for k, v in changes.items():
                old_val = current.get(k)
                new_val = v
                if str(old_val) != str(new_val):
                    cur.execute(
                        f"INSERT INTO {self.schema}.{self.log_table} (ID_ANALISE, ACTION, FIELD_NAME, OLD_VALUE, NEW_VALUE, CHANGED_BY) VALUES (?,?,?,?,?,?)",
                        (analysis_id, 'UPDATE', k, str(old_val) if old_val is not None else None,
                         str(new_val) if new_val is not None else None, changed_by)
                    )

    def delete(self, analysis_id: int, changed_by: Optional[str] = None) -> None:
        conn = get_connection()
        with transaction(conn) as (conn, cur):
            current = self.read(analysis_id)
            if not current:
                return
            # log snapshot per field
            for k, v in current.items():
                if k == 'ID_ANALISE':
                    continue
                cur.execute(
                    f"INSERT INTO {self.schema}.{self.log_table} (ID_ANALISE, ACTION, FIELD_NAME, OLD_VALUE, NEW_VALUE, CHANGED_BY) VALUES (?,?,?,?,?,?)",
                    (analysis_id, 'DELETE', k, str(v) if v is not None else None, None, changed_by)
                )
            cur.execute(f"DELETE FROM {self.schema}.{self.table} WHERE ID_ANALISE = ?", (analysis_id,))

    # --------------------- BACKUP ---------------------
    def backup_tables(self) -> Tuple[str, str]:
        import datetime as dt
        stamp = dt.datetime.utcnow().strftime('%Y%m%d%H%M%S')
        backup_a = f"{self.schema}.{self.table}_backup_{stamp}"
        backup_l = f"{self.schema}.{self.log_table}_backup_{stamp}"
        conn = get_connection()
        with transaction(conn) as (conn, cur):
            cur.execute(f"SELECT * INTO {backup_a} FROM {self.schema}.{self.table}")
            cur.execute(f"SELECT * INTO {backup_l} FROM {self.schema}.{self.log_table}")
        return backup_a, backup_l