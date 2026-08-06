#!/usr/bin/env python3
"""
Script para criar/resetar usuário SUPERADMIN no banco de dados.

Uso:
    python backend/scripts/ensure_superadmin.py [--email dezigpi@gmail.com] [--password <senha>]

Se --password não for fornecido, usa 'admin123' como padrão.
"""
import sys
import os
import argparse
import getpass

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from utils.password_utils import hash_password


def ensure_superadmin(database_url: str, email: str, password: str) -> bool:
    """Cria ou atualiza o superadmin no banco."""
    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Verificar se usuário já existe
        result = conn.execute(
            text("SELECT id, email, status, email_confirmado, role FROM users WHERE LOWER(email) = LOWER(:email)"),
            {"email": email}
        )
        user = result.fetchone()

        # Hash via PostgreSQL pgcrypto — garante compatibilidade bcrypt entre plataformas
    # (bcrypt Windows ≠ bcrypt Linux — gerar hash no próprio DB evita mismatch)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT crypt(:password, gen_salt('bf', 12))"), {"password": password})
        row = result.fetchone()
        password_hash = row[0] if row else hash_password(password)
        now = "NOW()"

        if user:
            print(f"[INFO] Usuario ja existe: id={user[0]}, email={user[1]}, status={user[2]}, confirmado={user[3]}, role={user[4]}")
            print(f"[INFO] Resetando senha e garantindo status=ativo, role=SUPERADMIN...")
            conn.execute(text("""
                UPDATE users
                SET password_hash = :hash,
                    senha_hash = :hash,
                    status = 'ativo',
                    email_confirmado = true,
                    role = 2,
                    updated_at = NOW()
                WHERE LOWER(email) = LOWER(:email)
            """), {"hash": password_hash, "email": email})
            conn.commit()
            print(f"[OK] Senha resetada com sucesso para '{email}'")
        else:
            print(f"[INFO] Usuario nao existe. Criando superadmin '{email}'...")
            conn.execute(text("""
                INSERT INTO users (email, password_hash, senha_hash, status, email_confirmado, role, nome, created_at, updated_at)
                VALUES (:email, :hash, :hash, 'ativo', true, 2, 'Super Admin', NOW(), NOW())
            """), {"hash": password_hash, "email": email})
            conn.commit()
            print(f"[OK] Superadmin criado com sucesso: '{email}'")

    # Verificação final
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, email, status, email_confirmado, role FROM users WHERE LOWER(email) = LOWER(:email)"),
            {"email": email}
        )
        user = result.fetchone()
        if user:
            print(f"[VERIFY] id={user[0]}, email={user[1]}, status={user[2]}, confirmado={user[3]}, role={user[4]}")
            return True
        return False


def main():
    parser = argparse.ArgumentParser(description="Cria/atualiza superadmin no banco FraLib")
    parser.add_argument("--email", default="dezigpi@gmail.com", help="Email do superadmin")
    parser.add_argument("--password", default=None, help="Senha (se omitido, usa admin123 ou prompt)")
    parser.add_argument("--db-url", default=None, help="DATABASE_URL (se omitido, usa .env)")
    args = parser.parse_args()

    # Obter senha
    password = args.password
    if not password:
        # Tentar pegar do .env primeiro
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith("ADMIN_PASSWORD="):
                        password = line.strip().split("=", 1)[1].strip().strip('"\'')
                        break
        if not password:
            password = "admin123"
            print(f"[INFO] Usando senha padrao: '{password}' (use --password para definir outra)")

    # Obter DATABASE_URL
    db_url = args.db_url or os.environ.get("DATABASE_URL")
    if not db_url:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith("DATABASE_URL="):
                        db_url = line.strip().split("=", 1)[1].strip().strip('"\'')
                        break
    if not db_url:
        print("[ERRO] DATABASE_URL nao encontrada. Passe via --db-url ou .env")
        sys.exit(1)

    print(f"[INFO] Conectando ao banco...")
    print(f"[INFO] Email: {args.email}")
    print(f"[INFO] Database: {db_url.split('@')[-1] if '@' in db_url else db_url}")

    success = ensure_superadmin(db_url, args.email, password)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
