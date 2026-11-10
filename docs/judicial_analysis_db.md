# SQL Server – Análises Judiciais (IPF)

Este módulo adiciona persistência completa no SQL Server para análises judiciais, suportando:
- CRUD (Create, Read, Update, Delete)
- Campos dinâmicos (adicionados em tempo de execução)
- Log de alterações por operação e campo
- Validação de dados e controle de transações
- Backup automático antes de alterações estruturais

## 1. Esquema

Tabela principal: `dbo.Analises`
- `ID_ANALISE` INT IDENTITY PK
- `NOTA` DECIMAL(18,4)
- `OBSERVACAO_JUIZ` NVARCHAR(MAX)
- `DATA_CRIACAO` DATETIME2 DEFAULT `SYSUTCDATETIME()`
- `DATA_ATUALIZACAO` DATETIME2
- `STATUS` NVARCHAR(50)
- `JUIZ` NVARCHAR(150)

Tabela de log: `dbo.Analises_Log`
- `LOG_ID` INT IDENTITY PK
- `ID_ANALISE` INT FK -> `Analises(ID_ANALISE)`
- `ACTION` NVARCHAR(20) (CREATE/UPDATE/DELETE)
- `FIELD_NAME` NVARCHAR(128)
- `OLD_VALUE`/`NEW_VALUE` NVARCHAR(MAX)
- `CHANGED_AT` DATETIME2 DEFAULT `SYSUTCDATETIME()`
- `CHANGED_BY` NVARCHAR(150)

Stored procedure utilitária: `dbo.AddColumnIfNotExists(table, column, type)`.

Script completo: `db/sqlserver/judicial_analyses_schema.sql`.

## 2. Configuração de Conexão

Variáveis de ambiente usadas:
- `MSSQL_DRIVER` (padrão: `ODBC Driver 17 for SQL Server`)
- `MSSQL_SERVER`
- `MSSQL_DB`
- `MSSQL_USER`, `MSSQL_PASSWORD` ou `MSSQL_TRUSTED=true` para conexão integrada

Arquivo: `db/mssql_connection.py` fornece `get_connection()` e o context manager `transaction(conn)`.

## 3. API de Repositório

Arquivo: `db/analysis_repository.py`

### Métodos principais
- `create_schema()` – cria tabelas/procedures necessárias
- `backup_tables()` – cria cópias com timestamp (`SELECT INTO`)
- `add_column_if_not_exists(column, type)` – adiciona coluna dinâmica
- `validate(data)` – valida e normaliza campos
- `create(data, changed_by=None)` – insere uma análise e loga todos os campos
- `read(analysis_id)` – busca uma análise
- `list(top=100, where=None, params=())` – lista análises
- `update(analysis_id, changes, changed_by=None)` – atualiza campos e registra log por campo
- `delete(analysis_id, changed_by=None)` – apaga e registra snapshot em log

Campos extras (não base) são adicionados automaticamente, com tipo inferido:
- `str -> NVARCHAR(MAX)`
- `int -> INT`, `float -> DECIMAL(18,4)`, `bool -> BIT`
- `datetime/date -> DATETIME2`

## 4. Uso

```
from db.analysis_repository import AnalysisRepository

repo = AnalysisRepository()
repo.create_schema()

# CREATE
analysis_id = repo.create({
    'NOTA': 87.5,
    'OBSERVACAO_JUIZ': 'Profundidade adequada, ligeira instabilidade final.',
    'STATUS': 'FINAL',
    'JUIZ': 'Maria Souza',
    'HIP_ANGLE_PEAK': 112.3,  # campo dinâmico
}, changed_by='admin')

# READ
item = repo.read(analysis_id)

# UPDATE
repo.update(analysis_id, {'NOTA': 90.0, 'STATUS': 'AMENDED'}, changed_by='admin')

# DELETE
repo.delete(analysis_id, changed_by='admin')

# LIST
items = repo.list(top=50, where='STATUS = ?', params=('FINAL',))
```

## 5. Integração Opcional

Você pode acionar o `create(...)` ao salvar a tentativa em `ui/interface.py` (quando o juiz registra observações), sem alterar a lógica de avaliação.

## 6. Testes

O arquivo de testes unitários (`db/test_analysis_repository.py`) usa `unittest` e mocks de `pyodbc` para validar:
- normalização/validação
- geração de SQL de backup e inserção
- logging por campo
- adição de colunas dinâmicas

Para executar:
```
venv\Scripts\python.exe -m pytest db/test_analysis_repository.py -q
```

## 7. Backups

Antes de alterações estruturais, use `backup_tables()`; você também pode executar os comandos comentados no `.sql` para criar cópias.

## 8. Tratamento de Erros

Todas as operações rodam em transações; em caso de exceção, `rollback` é acionado e a exceção é propagada. Erros de validação levantam `ValueError` com mensagens claras.

## 9. Relatório de Modificações

- Adicionados arquivos: `db/mssql_connection.py`, `db/analysis_repository.py`, `db/sqlserver/judicial_analyses_schema.sql`, `docs/judicial_analysis_db.md`, `db/test_analysis_repository.py`.
- Nenhuma alteração em módulos existentes de UI ou lógica de avaliação.