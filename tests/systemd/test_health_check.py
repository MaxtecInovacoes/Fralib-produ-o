"""Tests para verify_systemd_health.py e estrutura geral."""
import sys
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestAuditScript:
    def test_script_exists(self):
        path = PROJECT_ROOT / "scripts" / "verify_systemd_health.py"
        assert path.exists(), "verify_systemd_health.py nao encontrado"

    def test_script_imports_correctly(self):
        path = PROJECT_ROOT / "scripts" / "verify_systemd_health.py"
        content = path.read_text(encoding="utf-8")
        assert "def main" in content
        assert "playwright" in content.lower()

    def test_script_has_8_checks(self):
        """Spec exige 8+ checks."""
        path = PROJECT_ROOT / "scripts" / "verify_systemd_health.py"
        content = path.read_text(encoding="utf-8")
        check_count = content.count('run_check(')
        assert check_count >= 8, f"So {check_count} checks (minimo 8)"


class TestManagementScripts:
    """Scripts de gestao devem existir e ser executaveis."""

    def test_install_exists(self):
        path = PROJECT_ROOT / "scripts" / "systemd_install.sh"
        assert path.exists(), "systemd_install.sh faltando"

    def test_uninstall_exists(self):
        path = PROJECT_ROOT / "scripts" / "systemd_uninstall.sh"
        assert path.exists(), "systemd_uninstall.sh faltando"

    def test_migrate_exists(self):
        path = PROJECT_ROOT / "scripts" / "migrate_pm2_to_systemd.sh"
        assert path.exists(), "migrate_pm2_to_systemd.sh faltando"

    def test_scripts_have_idempotent_install(self):
        content = (PROJECT_ROOT / "scripts" / "systemd_install.sh").read_text(encoding="utf-8")
        # install deve ser idempotente (pode rodar +1 vez)
        assert "daemon-reload" in content or "systemctl" in content

    def test_uninstall_rollback_pm2(self):
        content = (PROJECT_ROOT / "scripts" / "systemd_uninstall.sh").read_text(encoding="utf-8")
        assert "pm2 resurrect" in content, "uninstall nao faz rollback PM2"


class TestSpecDocument:
    def test_spec_exists(self):
        path = PROJECT_ROOT / "docs" / "specs" / "SPEC_systemd_migration.md"
        assert path.exists(), "SPEC faltando"

    def test_spec_has_acceptance_criteria(self):
        path = PROJECT_ROOT / "docs" / "specs" / "SPEC_systemd_migration.md"
        content = path.read_text(encoding="utf-8")
        assert "CRITERIOS DE ACEITE" in content.upper() or "critérios de aceite" in content.lower()

    def test_spec_has_out_of_scope(self):
        path = PROJECT_ROOT / "docs" / "specs" / "SPEC_systemd_migration.md"
        content = path.read_text(encoding="utf-8")
        assert "FORA DE ESCOPO" in content.upper() or "fora de escopo" in content.lower()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))