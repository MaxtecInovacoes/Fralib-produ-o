"""
Testes de segurança para OAuth CSRF em auth_endpoints.py
Garante que state é armazenado em cookie httponly, não JSON
"""
import pytest
import re


class TestOAuthCSRF:
    """Garante que OAuth CSRF usa cookie httponly"""

    def test_state_nao_esta_no_json_response(self):
        """Verifica que state NÃO é retornado no JSON response"""
        with open("backend/endpoints/auth_endpoints.py", "r") as f:
            content = f.read()

        # Encontrar função google_oauth_redirect
        start = content.find("async def google_oauth_redirect")
        end = content.find("\n@router", start)
        if end == -1:
            end = content.find("\nasync def ", start + 1)
        func = content[start:end if end != -1 else len(content)]

        # O return não deve ter "state" no JSON
        assert '"state":' not in func, \
            "CSRF: state NÃO deve ser retornado no JSON response"

    def test_usa_cookie_httponly(self):
        """Verifica que usa cookie httponly para state"""
        with open("backend/endpoints/auth_endpoints.py", "r") as f:
            content = f.read()

        # Deve ter set_cookie com httponly=True
        assert 'set_cookie' in content, "Deve usar set_cookie"
        assert 'httponly=True' in content, "Cookie deve ser httponly=True"

    def test_cookie_tem_assinatura_hmac(self):
        """Verifica que state é assinado com HMAC"""
        with open("backend/endpoints/auth_endpoints.py", "r") as f:
            content = f.read()

        assert 'hmac.new' in content, "State deve ser assinado com HMAC"
        assert 'sha256' in content, "Deve usar SHA256 para assinatura"

    def test_callback_valida_cookie(self):
        """Verifica que callback valida cookie httponly"""
        with open("backend/endpoints/auth_endpoints.py", "r") as f:
            content = f.read()

        # Encontrar função callback
        start = content.find("async def google_oauth_callback")
        if start != -1:
            end = content.find("\n@router", start)
            if end == -1:
                end = content.find("\nasync def ", start + 1)
            callback_func = content[start:end if end != -1 else len(content)]

            # Deve validar cookie, não parâmetro GET
            assert 'oauth_state_cookie' in callback_func, \
                "Callback deve ler state do cookie"
            assert 'request.cookies.get' in callback_func, \
                "Callback deve obter state dos cookies"
            assert 'hmac.compare_digest' in callback_func, \
                "Callback deve validar assinatura HMAC"

    def test_nao_confia_no_state_do_get(self):
        """Verifica que state do GET parameter não é usado sem validação"""
        with open("backend/endpoints/auth_endpoints.py", "r") as f:
            content = f.read()

        # Callback deve validar state contra cookie
        start = content.find("async def google_oauth_callback")
        if start != -1:
            callback_func = content[start:start + 2000]

            # Se há validação, deve ser contra cookie
            if 'state = ' in callback_func and 'request' in callback_func:
                # Deve ter validação de correspondência
                assert 'oauth_state_cookie' in callback_func or \
                       'state_from_cookie' in callback_func, \
                       "State do GET deve ser validado contra cookie"


class TestOAuthDeadCode:
    """Remove código morto do OAuth"""

    def test_sem_dead_code_retorno_duplo(self):
        """Verifica que não há dois returns consecutivos"""
        with open("backend/endpoints/auth_endpoints.py", "r") as f:
            content = f.read()

        # Encontrar google_oauth_redirect
        start = content.find("async def google_oauth_redirect")
        end = content.find("\n@router.get", start)
        func = content[start:end]

        # Não deve ter dois returns
        return_count = func.count("return")
        assert return_count <= 1, \
            f"Encontrado {return_count} returns - código morto detectado"
