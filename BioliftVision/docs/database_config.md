# Configuração de Banco de Dados

- Suporte a Microsoft SQL Server via `pyodbc` com drivers ODBC 17/18.
- Portável entre ambientes por meio de variáveis de ambiente e arquivos `.env`.

## Dependências e Requisitos
- `SQL Server` em execução com TCP/IP habilitado.
- `ODBC Driver 17` ou `ODBC Driver 18` para SQL Server instalado.
- `pyodbc` instalado no ambiente Python.
- Windows recomenda `Visual C++ Redistributable x64`.

## Variáveis de Ambiente
- `APP_ENV`: seleciona o ambiente (`dev`, `test`, `prod`).
- `MSSQL_SERVER`: host/instância (ex.: `localhost\\SQLEXPRESS`).
- `MSSQL_DB`: nome do banco.
- `MSSQL_TRUSTED`: usa conexão integrada do Windows (`true`/`false`).
- `MSSQL_USER`/`MSSQL_PASSWORD`: credenciais quando `MSSQL_TRUSTED=false`.
- `MSSQL_DRIVER`: driver ODBC (auto detectado se não definido).
- `MSSQL_ENCRYPT`: `yes`/`no`.
- `MSSQL_TRUST_SERVER_CERT`: `yes`/`no`.
- `MSSQL_TIMEOUT`: segundos de timeout.

## Arquivos `.env`
- `.env` na raiz do projeto.
- `.env.dev`, `.env.test`, `.env.prod` para ambientes específicos.
- `APP_ENV` controla qual arquivo será lido primeiro.

## Mensagens de Erro
- Driver ausente: solicitar instalação de ODBC 17/18.
- Falha de login: verificar `MSSQL_USER`/`MSSQL_PASSWORD` ou `MSSQL_TRUSTED`.
- Timeout: checar rede, serviço do SQL Server e firewall.

## Logs
- Centralizados em `logs/AAAA/MM/powerlifting_app.log`.
- Eventos: tentativa de conexão, sucesso/erro, mensagens de diagnóstico.

## Inicialização Segura
- Use `python app/start.py` para validar a conexão antes de abrir a aplicação.
- O script carrega `.env`, testa `SELECT 1` e inicia `main.py`.

## Integração no Código
- Módulo: `config/database.py`.
- Funções: `load_env()`, `connect_mssql()`, `test_connection()`.
- Repositórios podem obter conexão via `db/mssql_connection.get_connection()`.

## Ambientes
- `dev`: máquina local, `.env.dev`.
- `test`: CI/QA, `.env.test`.
- `prod`: servidor, `.env.prod`.
- Não há necessidade de modificar código entre ambientes; configure apenas variáveis.
