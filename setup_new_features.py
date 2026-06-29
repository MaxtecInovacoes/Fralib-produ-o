#!/usr/bin/env python3
"""
Setup script for new CRM/LinkedIn/Competitive Intelligence features.

Executes:
1. Database migrations
2. Environment setup
3. Configuration verification
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd: str, cwd: str = None):
    """Run command and return result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def main():
    """Main setup process."""
    print("🚀 Setting up CRM/LinkedIn/Competitive Intelligence features...")

    # Path do projeto
    project_root = Path(__file__).parent
    backend_root = project_root / "backend"

    # 1. Rodar migrações do Alembic
    print("\n📊 Running database migrations...")
    success, stdout, stderr = run_command(
        "alembic upgrade head",
        cwd=str(backend_root)
    )

    if success:
        print("✅ Database migrations completed successfully")
        print(stdout)
    else:
        print("❌ Database migrations failed")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False

    # 2. Verificar se as tabelas foram criadas
    print("\n🔍 Verifying new tables...")
    success, stdout, stderr = run_command(
        "psql -U postgres -d fralib -c "
        "\SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' "
        "AND table_name IN ('competitor_intel', 'linkedin_prospects', 'linkedin_templates', 'crm_configs', 'crm_sync_history');",
        cwd=str(project_root)
    )

    if success:
        print("✅ New tables created successfully")
    else:
        print("⚠️  Tables may already exist or need manual verification")

    # 3. Criar chave de criptografia se não existir
    print("\n🔐 Setting up encryption key...")
    if not os.getenv("FRALIB_CRM_ENCRYPTION_KEY"):
        # Gera chave aleatória
        import base64
        import os
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        print(f"📝 Add to your .env:")
        print(f"FRALIB_CRM_ENCRYPTION_KEY={key}")

    # 4. Verificar permissões
    print("\n🔒 Checking permissions...")
    tables = [
        "competitor_intel",
        "linkedin_prospects",
        "linkedin_templates",
        "crm_configs",
        "crm_sync_history"
    ]

    for table in tables:
        success, stdout, stderr = run_command(
            f"psql -U postgres -d fralib -c "
            f"SELECT COUNT(*) FROM {table};",
            cwd=str(project_root)
        )
        if success:
            print(f"✅ {table}: OK")
        else:
            print(f"❌ {table}: May need manual setup")

    print("\n🎉 Setup completed!")
    print("\n📋 Next steps:")
    print("1. Add FRALIB_CRM_ENCRYPTION_KEY to your .env file")
    print("2. Restart the server")
    print("3. Access SuperAdmin to configure LinkedIn/CRM")
    print("4. Use Admin for CRM sync operations")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)