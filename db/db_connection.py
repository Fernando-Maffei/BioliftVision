from typing import Optional, Any, List, Dict

from common.logger import log_info, log_error
from config.database import connect_mssql


class DatabaseConnection:
    def __init__(self, server_ip: Optional[str] = None):
        self.connection = None

    def connect(self):
        try:
            self.connection = connect_mssql()
            return self.connection
        except Exception as e:
            log_error(f"Falha na conexão MSSQL: {e}")
            return None

    def disconnect(self):
        if self.connection:
            self.connection.close()
            pass

    def execute_query(self, query: str, params: Optional[List[Any]] = None):
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
            else:
                self.connection.commit()
                return True
        except Exception as e:
            log_error(f"Erro na query: {e}")
            return None

    def ensure_schema(self):
        if not self.connection:
            if not self.connect():
                return False
        cursor = self.connection.cursor()
        cursor.execute(
            """
            IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Analises') AND type in (N'U'))
            BEGIN
                CREATE TABLE dbo.Analises (
                    ID_ANALISE INT IDENTITY(1,1) PRIMARY KEY,
                    NOTA DECIMAL(18,4) NULL,
                    OBSERVACAO_JUIZ NVARCHAR(MAX) NULL,
                    DATA_CRIACAO DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
                    DATA_ATUALIZACAO DATETIME2 NULL,
                    STATUS NVARCHAR(50) NULL,
                    JUIZ NVARCHAR(150) NULL
                );
            END
            """
        )
        for col, dtype in [
            ("ATLETA", "NVARCHAR(150)"),
            ("EXERCICIO", "NVARCHAR(100)"),
            ("TENTATIVA", "INT"),
            ("AUTO_VALIDO", "BIT"),
            ("AUTO_RESUMO_JSON", "NVARCHAR(MAX)"),
            ("ANGULOS_JSON", "NVARCHAR(MAX)")
        ]:
            cursor.execute(
                f"IF COL_LENGTH('dbo.Analises','{col}') IS NULL ALTER TABLE dbo.Analises ADD [{col}] {dtype}"
            )
        self.connection.commit()
        return True

    def save_analysis(self, data):
        if not self.connection:
            if not self.connect():
                return None
        self.ensure_schema()
        cursor = self.connection.cursor()
        cols = [
            "NOTA", "OBSERVACAO_JUIZ", "STATUS", "JUIZ",
            "ATLETA", "EXERCICIO", "TENTATIVA", "AUTO_VALIDO",
            "AUTO_RESUMO_JSON", "ANGULOS_JSON"
        ]
        values = [
            data.get("NOTA"), data.get("OBSERVACAO_JUIZ"), data.get("STATUS"), data.get("JUIZ"),
            data.get("ATLETA"), data.get("EXERCICIO"), data.get("TENTATIVA"), 1 if data.get("AUTO_VALIDO") else 0,
            data.get("AUTO_RESUMO_JSON"), data.get("ANGULOS_JSON")
        ]
        placeholders = ", ".join("?" for _ in cols)
        cursor.execute(
            f"INSERT INTO dbo.Analises ({', '.join('['+c+']' for c in cols)}) VALUES ({placeholders})",
            tuple(values)
        )
        cursor.execute("SELECT CAST(SCOPE_IDENTITY() AS INT)")
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT CAST(IDENT_CURRENT('dbo.Analises') AS INT)")
            row = cursor.fetchone()
        self.connection.commit()
        return int(row[0]) if row and row[0] is not None else None

    def list_latest(self, top=200):
        if not self.connection:
            if not self.connect():
                return []
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT TOP {int(top)} * FROM dbo.Analises ORDER BY ID_ANALISE DESC")
        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]
        result = []
        for r in rows:
            result.append({cols[i]: r[i] for i in range(len(cols))})
        return result

if __name__ == "__main__":
    db = DatabaseConnection(server_ip="26.18.4.206")
    if db.connect():
        result = db.execute_query("SELECT @@VERSION;")
        db.disconnect()
