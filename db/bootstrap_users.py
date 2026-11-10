"""
Script de bootstrap para garantir a tabela de usuários e testar criação e login.

Execução:
    python -m db.bootstrap_users
"""

from .user_repository import UserRepository


def main():
    repo = UserRepository()
    try:
        ok = repo.ensure_users_table()
        if not ok:
            print("❌ Falha ao garantir tabela de usuários.")
            return
        print("✅ Tabela 'dbo.users' verificada/criada.")

        # Criar usuário admin se não existir
        created, msg = repo.create_user(
            name="Administrador",
            username="admin",
            email=None,
            password="admin",
            role="admin",
        )
        if created:
            print("✅ Usuário 'admin' criado.")
        else:
            print("ℹ️ Usuário 'admin' não criado:", msg or "já existe")

        # Testar autenticação
        ok, msg = repo.authenticate_user("admin", "admin")
        if ok:
            print("✅ Autenticação de 'admin' bem-sucedida.")
        else:
            print("❌ Falha na autenticação de 'admin':", msg)
    finally:
        repo.close()


if __name__ == "__main__":
    main()