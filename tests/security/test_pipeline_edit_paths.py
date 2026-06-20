"""
Testes de segurança para pipeline_edit_endpoints.py
Garante que paths não são hardcoded - usar SITES_DIR do config
"""
import pytest
import re


class TestPathSecurity:
    """Garante que não há paths hardcoded"""

    def test_nao_tem_path_hardcoded_var_www(self):
        """Verifica que /var/www/fralib não está hardcoded"""
        with open("backend/endpoints/pipeline_edit_endpoints.py", "r") as f:
            content = f.read()

        # Procura /var/www/fralib
        matches = re.findall(r'/var/www/fralib', content)
        assert len(matches) == 0, \
            f"ENCONTRADO PATH HARDCODEADO: /var/www/fralib - usar SITES_DIR do config"

    def test_importa_SITES_DIR_do_config(self):
        """Verifica que SITES_DIR é importado"""
        with open("backend/endpoints/pipeline_edit_endpoints.py", "r") as f:
            content = f.read()

        assert "from backend.core.config import SITES_DIR" in content, \
            "SITES_DIR deve ser importado de backend.core.config"

    def test_usa_os_path_join_ou_pathlib(self):
        """Verifica que usa os.path.join ou Path para construir paths"""
        with open("backend/endpoints/pipeline_edit_endpoints.py", "r") as f:
            content = f.read()

        # Deve usar os.path.join ou pathlib
        uses_safe_path = "os.path.join" in content or "Path(" in content
        assert uses_safe_path, "Usar os.path.join ou Path para construir paths"

    def test_html_path_construido_corretamente(self):
        """Verifica que html_path é construído com SITES_DIR"""
        with open("backend/endpoints/pipeline_edit_endpoints.py", "r") as f:
            content = f.read()

        # Deve ter SITES_DIR na construção do path
        assert "SITES_DIR" in content, "SITES_DIR deve ser usado"

        # Não deve ter f-string com paths hardcoded
        hardcoded_pattern = re.findall(r'f["\'].*/var/www.*["\']', content)
        assert len(hardcoded_pattern) == 0, \
            f"ENCONTRADO f-string com path hardcoded: {hardcoded_pattern}"


class TestTenantIsolation:
    """Verifica que tenant_id é usado corretamente"""

    def test_queries_usam_user_id_para_leads(self):
        """Verifica que queries de leads usam user_id"""
        with open("backend/endpoints/pipeline_edit_endpoints.py", "r") as f:
            content = f.read()

        # Queries de leads devem verificar user_id
        assert "AND user_id = :uid" in content, \
            "Queries devem verificar user_id para isolamento de tenant"

    def test_nao_expoe_caminho_real_no_response(self):
        """Response não deve expor caminho real do filesystem"""
        with open("backend/endpoints/pipeline_edit_endpoints.py", "r") as f:
            content = f.read()

        # Se retornar html_path, deve ser para debug apenas (não expõe caminho interno)
        # O ideal é nem retornar, ou retornar apenas slug
        # Por ora, verificamos que não retorna path completo com /var/www
        if '"html_path"' in content:
            # Se retornar, verificar que é o path construido, não hardcoded
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '"html_path"' in line or "'html_path'" in line:
                    # A linha não deve ter /var/www hardcoded
                    assert '/var/www' not in line, \
                        "Response não deve expor /var/www"
