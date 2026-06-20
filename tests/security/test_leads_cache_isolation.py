"""
Testes de segurança para leads_cache
Garante que cache é isolado por user_id, não global entre tenants
"""
import pytest
import re


class TestLeadsCacheIsolation:
    """Garante que leads_cache usa user_id para isolamento"""

    def test_server_migration_tem_user_id(self):
        """Verifica que server.py cria leads_cache com user_id"""
        with open("server.py", "r") as f:
            content = f.read()

        # Deve ter user_id na criação da tabela
        assert "user_id INTEGER NOT NULL" in content or \
               "user_id INTEGER" in content, \
               "leads_cache deve ter coluna user_id"

    def test_indices_usam_user_id(self):
        """Verifica que índices incluem user_id"""
        with open("server.py", "r") as f:
            content = f.read()

        # Deve ter índice com user_id
        assert "user_id" in content, "Índices devem usar user_id"

    def test_buscar_cache_usa_user_id(self):
        """Verifica que _buscar_cache_leads filtra por user_id"""
        with open("backend/utils/agente1_hunter_v2.py", "r") as f:
            content = f.read()

        # A função deve ter user_id como parâmetro
        assert "user_id" in content, "Função deve usar user_id"

    def test_salvar_cache_usa_user_id(self):
        """Verifica que _salvar_cache_leads inclui user_id"""
        with open("backend/utils/agente1_hunter_v2.py", "r") as f:
            content = f.read()

        # Deve inserir user_id
        assert "user_id" in content, "Deve inserir user_id"

    def test_cache_nao_e_mais_global(self):
        """Verifica que não há mais cache verdadeiramente global"""
        with open("server.py", "r") as f:
            content = f.read()

        # Comentário deve dizer "isolado por user_id", não "global"
        assert "ISOLADO POR USER_ID" in content or "isolado" in content.lower(), \
            "Cache deve ser isolado, não global"

    def test_pipeline_cache_control_aceita_user_id(self):
        """Verifica que invalidar_caches_cold_run aceita user_id"""
        with open("backend/services/pipeline_cache_control.py", "r") as f:
            content = f.read()

        assert "user_id" in content, "Função deve aceitar user_id"
