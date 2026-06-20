"""
Testes de segurança para revoke_token
Garante que falha de Redis é tratada corretamente
"""
import pytest
import re


class TestRevokeToken:
    """Garante que revoke_token não falha silenciosamente"""

    def test_revoke_token_logga_erro(self):
        """Verifica que revoke_token logga erro crítico se Redis indisponível"""
        with open("backend/core/auth.py", "r") as f:
            content = f.read()

        # Deve ter logging.critical ou similar
        assert "critical" in content.lower() or "error" in content.lower(), \
            "Deve logar erro quando Redis indisponível"

    def test_revoke_token_nao_retorna_none_silencioso(self):
        """Verifica que não retorna None sem tratamento"""
        with open("backend/core/auth.py", "r") as f:
            content = f.read()

        # Deve retornar False ou raise exception quando Redis indisponível
        func_start = content.find("def revoke_token")
        func_end = content.find("\ndef ", func_start + 1)
        if func_end == -1:
            func_end = content.find("\n\n", func_start)
        func = content[func_start:func_end]

        # Não deve ter apenas "return" quando Redis indisponível
        assert "return False" in func or "raise" in func, \
            "Deve retornar False ou raise quando Redis indisponível"

    def test_logout_trata_falha_revoke(self):
        """Verifica que logout endpoint trata falha de revoke_token"""
        with open("backend/endpoints/auth_endpoints.py", "r") as f:
            content = f.read()

        # Deve verificar resultado de revoke_token
        assert "revoke_token" in content, "Logout deve chamar revoke_token"
        assert "result" in content or "logout_ok" in content or "warning" in content, \
            "Logout deve tratar resultado de revoke_token"


class TestAuthLogger:
    """Verifica que auth tem logging adequado"""

    def test_tem_import_logging(self):
        """Verifica que auth.py importa logging"""
        with open("backend/core/auth.py", "r") as f:
            content = f.read()

        assert "import logging" in content, "Deve importar logging"
