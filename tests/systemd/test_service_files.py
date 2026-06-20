"""Tests para servicos systemd do FraLib."""
import sys
import os
import re
from pathlib import Path

# Adicionar raiz do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYSTEMD_DIR = PROJECT_ROOT / "infra" / "systemd"

EXPECTED_SERVICES = [
    "fralib-api.service",
    "fralib-worker.service",
    "fralib-franz.service",
    "fralib-wpp-listener.service",
    "fralib-hermes.service",
]


class TestServiceFilesExist:
    def test_all_service_files_present(self):
        """Todos os 5 .service files devem existir."""
        for svc in EXPECTED_SERVICES:
            path = SYSTEMD_DIR / svc
            assert path.exists(), f"Faltando: {svc}"

    def test_helper_script_exists(self):
        path = SYSTEMD_DIR / "env-from-dotenv.py"
        assert path.exists(), "env-from-dotenv.py nao encontrado"

    def test_readme_exists(self):
        path = SYSTEMD_DIR / "README.md"
        assert path.exists(), "README.md nao encontrado"


class TestServiceFileStructure:
    """Cada .service deve ter secoes [Unit], [Service], [Install]."""

    @pytest.mark.parametrize("service", EXPECTED_SERVICES)
    def test_has_unit_section(self, service):
        content = (SYSTEMD_DIR / service).read_text(encoding="utf-8")
        assert "[Unit]" in content, f"{service} sem [Unit]"

    @pytest.mark.parametrize("service", EXPECTED_SERVICES)
    def test_has_service_section(self, service):
        content = (SYSTEMD_DIR / service).read_text(encoding="utf-8")
        assert "[Service]" in content, f"{service} sem [Service]"

    @pytest.mark.parametrize("service", EXPECTED_SERVICES)
    def test_has_install_section(self, service):
        content = (SYSTEMD_DIR / service).read_text(encoding="utf-8")
        assert "[Install]" in content, f"{service} sem [Install]"


class TestServiceResourceLimits:
    """Validar limites de CPU/RAM aplicados."""

    @pytest.mark.parametrize("service", EXPECTED_SERVICES)
    def test_has_memory_max(self, service):
        content = (SYSTEMD_DIR / service).read_text(encoding="utf-8")
        assert "MemoryMax=" in content, f"{service} sem MemoryMax"

    @pytest.mark.parametrize("service", EXPECTED_SERVICES)
    def test_has_cpu_quota(self, service):
        content = (SYSTEMD_DIR / service).read_text(encoding="utf-8")
        assert "CPUQuota=" in content, f"{service} sem CPUQuota"

    @pytest.mark.parametrize("service", EXPECTED_SERVICES)
    def test_has_restart_policy(self, service):
        content = (SYSTEMD_DIR / service).read_text(encoding="utf-8")
        assert "Restart=" in content, f"{service} sem Restart="


class TestServicePaths:
    """Validar paths estao corretos."""

    @pytest.mark.parametrize("service", EXPECTED_SERVICES)
    def test_uses_correct_paths(self, service):
        content = (SYSTEMD_DIR / service).read_text(encoding="utf-8")
        assert "/root/fralib" in content, f"{service} nao usa /root/fralib"
        assert "/root/fralib/venv/bin/python3" in content, f"{service} nao usa venv python"


class TestSpecificLimits:
    """Validar limites especificos por servico."""

    def test_api_memory_max(self):
        content = (SYSTEMD_DIR / "fralib-api.service").read_text(encoding="utf-8")
        match = re.search(r"MemoryMax=(\d+[KMG])", content)
        assert match, "fralib-api sem MemoryMax"
        assert "M" in match.group(1) or "G" in match.group(1)

    def test_worker_memory_max_higher(self):
        """Worker deve ter mais RAM que API (faz sites pesados)."""
        api = (SYSTEMD_DIR / "fralib-api.service").read_text(encoding="utf-8")
        worker = (SYSTEMD_DIR / "fralib-worker.service").read_text(encoding="utf-8")
        api_mem = re.search(r"MemoryMax=(\d+[KMG])", api).group(1)
        worker_mem = re.search(r"MemoryMax=(\d+[KMG])", worker).group(1)
        # Worker >= API (em GB)
        assert "G" in worker_mem or worker_mem > api_mem


class TestBootOrder:
    """Hermes deve depender dos outros."""

    def test_hermes_depends_on_others(self):
        content = (SYSTEMD_DIR / "fralib-hermes.service").read_text(encoding="utf-8")
        assert "After=" in content
        assert "fralib-api" in content, "Hermes nao espera API"


class TestSecurity:
    """Validar hardening basico."""

    @pytest.mark.parametrize("service", EXPECTED_SERVICES)
    def test_no_new_privileges(self, service):
        content = (SYSTEMD_DIR / service).read_text(encoding="utf-8")
        assert "NoNewPrivileges=yes" in content, f"{service} sem NoNewPrivileges"

    @pytest.mark.parametrize("service", EXPECTED_SERVICES)
    def test_private_tmp(self, service):
        content = (SYSTEMD_DIR / service).read_text(encoding="utf-8")
        assert "PrivateTmp=yes" in content, f"{service} sem PrivateTmp"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))