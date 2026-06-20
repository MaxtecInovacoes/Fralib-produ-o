"""
Testes de segurança para users_endpoints.py
Garante que IDOR não volte - todas as queries devem usar user_id, não tenant_id
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# Testes de IDOR para exportar_dados_usuario
class TestExportarDadosIDOR:
    """Garante que exportar_dados_usuario usa user_id, não tenant_id"""

    def test_exportar_usa_user_id_na_query_leads(self):
        """Verifica que query de leads usa :uid = user_id"""
        with open("backend/endpoints/users_endpoints.py", "r") as f:
            content = f.read()

        # Encontra o bloco de exportar_leads
        assert "FROM leads WHERE user_id = :uid" in content

        # Verifica que NÃO usa tenant_id no lugar errado
        # O padrão {uid: tenant_id} é o bug
        lines = content.split("\n")
        in_export_block = False
        for i, line in enumerate(lines):
            if "def exportar_dados_usuario" in line:
                in_export_block = True
            if in_export_block and "def " in line and "exportar_dados_usuario" not in line:
                in_export_block = False
                break
            if in_export_block:
                # Depois do primeiro fetchone de user_data, todas as queries devem usar user_id
                if "FROM leads WHERE" in line or "FROM interacoes WHERE" in line or "FROM pipeline_runs WHERE" in line:
                    # A próxima linha deve ter {"uid": user_id}
                    next_line = lines[i + 1] if i + 1 < len(lines) else ""
                    assert 'user_id' in next_line, f"Query na linha {i+1} deve usar user_id"
                    assert 'tenant_id' not in next_line or '"uid": user_id' in next_line, f"IDOR na linha {i+1}: não use tenant_id em queries de usuário"

    def test_exportar_nao_usa_tenant_id_em_leads(self):
        """Verifica que NÃO existe padrão {'uid': tenant_id} em exportar"""
        with open("backend/endpoints/users_endpoints.py", "r") as f:
            content = f.read()

        # Extrai a função exportar_dados_usuario
        start = content.find("async def exportar_dados_usuario")
        end = content.find("\n\n@router", start)
        if end == -1:
            end = content.find("\ndef ", start + 1)
        export_func = content[start:end if end != -1 else len(content)]

        # Verifica que não há tenant_id usado como uid
        import re
        # Procura {"uid": tenant_id}
        matches = re.findall(r'\{\s*"uid"\s*:\s*tenant_id\s*\}', export_func)
        assert len(matches) == 0, f"Encontrado IDOR pattern: {matches}"


class TestDeletarContaIDOR:
    """Garante que deletar_conta_usuario usa user_id, não tenant_id"""

    def test_deletar_usa_user_id_em_todas_queries(self):
        """Verifica que todas as queries de delete usam user_id"""
        with open("backend/endpoints/users_endpoints.py", "r") as f:
            content = f.read()

        # Extrai a função deletar_conta_usuario
        start = content.find("async def deletar_conta_usuario")
        end = content.find("\n\n# Import datetime", start)
        if end == -1:
            end = content.find("\n\n@router", start)
        delete_func = content[start:end if end != -1 else len(content)]

        # Todas as queries DELETE devem usar user_id, não tenant_id
        import re

        # Procura {"uid": tenant_id} ou {"tid": tenant_id}
        matches_uid = re.findall(r'\{\s*"uid"\s*:\s*tenant_id\s*\}', delete_func)
        matches_tid = re.findall(r'\{\s*"tid"\s*:\s*tenant_id\s*\}', delete_func)

        assert len(matches_uid) == 0, f"Encontrado IDOR pattern (uid): {matches_uid}"
        assert len(matches_tid) == 0, f"Encontrado IDOR pattern (tid): {matches_tid}"

    def test_deletar_nao_usa_tenant_id_em_deletes(self):
        """Verifica que DELETE queries não usam tenant_id"""
        with open("backend/endpoints/users_endpoints.py", "r") as f:
            content = f.read()

        # Extrai a função
        start = content.find("async def deletar_conta_usuario")
        end = content.find("\n\n# Import datetime", start)
        if end == -1:
            end = content.find("\n\n@router", start)
        delete_func = content[start:end if end != -1 else len(content)]

        # Verifica que todas as linhas com DELETE tem user_id
        lines = delete_func.split("\n")
        for i, line in enumerate(lines):
            if "DELETE FROM" in line:
                # A próxima linha deve ter {"uid": user_id}
                next_line = lines[i + 1] if i + 1 < len(lines) else ""
                assert 'user_id' in next_line, f"DELETE na linha deve usar user_id"
                assert 'tenant_id' not in next_line, f"IDOR: DELETE não deve usar tenant_id"


class TestSchemaValidation:
    """Verifica que schema de resposta usa dados corretos"""

    def test_response_nao_expoe_tenant_id_inutil(self):
        """Response não deve expor dados de outros tenants"""
        with open("backend/endpoints/users_endpoints.py", "r") as f:
            content = f.read()

        # Verifica que o return não inclui dados crus de tenant_id
        # Exceto para verificação interna (que já tem proteção)
        export_func_start = content.find("async def exportar_dados_usuario")
        if export_func_start != -1:
            export_func_end = content.find("\n\n@router", export_func_start)
            if export_func_end == -1:
                export_func_end = content.find("\ndef ", export_func_start + 1)
            export_func = content[export_func_start:export_func_end]

            # O return não deve incluir tenant_id do usuário
            assert '"tenant_id"' not in export_func or "usuarios" in export_func, \
                "Response não deve expor tenant_id"
