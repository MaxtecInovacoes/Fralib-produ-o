"""
Testes unitários para ia_manager.py

Cobre as operações de gerenciamento de chaves de API:
- Seleção de modelo (pick_key)
- Marcação de sucesso/falha
- Rate limiting e budgets
"""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, timedelta

# Setup path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'backend'))


class TestPickKey:
    """Testes para seleção de chave de API."""

    def test_pick_key_retorna_tupla_com_credenciais(self):
        """Deve retornar tupla com (api_key, base_url, key_id)."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_cursor.fetchone.return_value = (1, "encrypted_key_abc", "https://api.anthropic.com")
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            with patch('backend.services.ia_manager.decriptar') as mock_decriptar:
                mock_decriptar.return_value = "sk-ant-api03-plain-key"

                from backend.services.ia_manager import pick_key

                result = pick_key("anthropic")

                assert result is not None
                assert len(result) == 3
                api_key, base_url, key_id = result
                assert api_key == "sk-ant-api03-plain-key"
                assert base_url == "https://api.anthropic.com"
                assert key_id == 1

    def test_pick_key_sem_keys_saudaveis_retorna_fallback_env(self):
        """Sem keys disponíveis deve usar fallback do .env."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_cursor.fetchone.return_value = None  # Nenhuma key disponível
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            with patch.dict(os.environ, {
                'ANTHROPIC_API_KEY': 'env-fallback-key',
                'ANTHROPIC_BASE_URL': 'https://env-fallback-url.com'
            }):
                from backend.services.ia_manager import pick_key

                result = pick_key("anthropic")

                assert result is not None
                api_key, base_url, key_id = result
                assert api_key == "env-fallback-key"
                assert base_url == "https://env-fallback-url.com"
                assert key_id is None

    def test_pick_key_key_descriptografia_falha_tenta_proxima(self):
        """Se descriptografia falhar, deve tentar próxima key."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)

            # Primeira chamada retorna key corrupta, segunda retorna None
            mock_cursor.fetchone.side_effect = [
                (1, "corrupted_key", "https://api.anthropic.com"),
                None
            ]
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            with patch('backend.services.ia_manager.decriptar') as mock_decriptar:
                mock_decriptar.return_value = ""  # Falha na descriptografia

                with patch('backend.services.ia_manager.mark_failure') as mock_mark:
                    from backend.services.ia_manager import pick_key

                    result = pick_key("anthropic")

                    mock_mark.assert_called_once()


class TestMarkSuccess:
    """Testes para marcação de sucesso de key."""

    def test_mark_success_incrementa_contador(self):
        """Sucesso deve incrementar success_count."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import mark_success

            mark_success(key_id=42)

            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args[0][1]
            assert call_args == (42,)
            mock_conn.commit.assert_called_once()

    def test_mark_success_key_id_none_nao_faz_nada(self):
        """key_id None (fallback env) não deve fazer nada."""
        from backend.services.ia_manager import mark_success

        # Não deve lançar exceção
        result = mark_success(key_id=None)

        assert result is None


class TestMarkFailure:
    """Testes para marcação de falha de key."""

    def test_mark_failure_seta_cooldown(self):
        """Falha deve setar cooldown_until."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import mark_failure

            mark_failure(key_id=42, error="rate_limit_exceeded", cooldown_seconds=60)

            mock_cursor.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

    def test_mark_failure_key_id_none_seta_global_cooldown(self):
        """Falha com key None deve usar cooldown global."""
        with patch('backend.services.ia_manager.set_global_cooldown') as mock_set_cooldown:
            from backend.services.ia_manager import mark_failure

            mark_failure(key_id=None, error="global_failure", cooldown_seconds=30)

            mock_set_cooldown.assert_called_once_with(30)


class TestSetGlobalCooldown:
    """Testes para cooldown global."""

    def test_set_global_cooldown_menos_15_segundos_ignorado(self):
        """Cooldown menor que 15s não deve ser setado."""
        from backend.services.ia_manager import set_global_cooldown

        # Não deve lançar exceção
        result = set_global_cooldown(seconds=10)

        assert result is None

    def test_set_global_cooldown_sucesso(self):
        """Cooldown global deve ser setado corretamente."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import set_global_cooldown

            set_global_cooldown(seconds=60)

            mock_cursor.execute.assert_called()
            mock_conn.commit.assert_called_once()


class TestParseCooldownFromResponse:
    """Testes para parsing de cooldown de resposta HTTP."""

    def test_parse_429_sem_headers_retorna_60(self):
        """HTTP 429 sem headers específicos retorna 60s."""
        from backend.services.ia_manager import parse_cooldown_from_response

        result = parse_cooldown_from_response(429, {})

        assert result == 60

    def test_parse_429_com_retry_after_header(self):
        """HTTP 429 com retry-after retorna valor do header."""
        from backend.services.ia_manager import parse_cooldown_from_response

        result = parse_cooldown_from_response(429, {"retry-after": "30"})

        assert result == 30

    def test_parse_429_com_anthropic_reset_header(self):
        """HTTP 429 com header Anthropic retorna tempo até reset."""
        from backend.services.ia_manager import parse_cooldown_from_response
        from datetime import datetime, timezone, timedelta

        reset_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        headers = {
            "Anthropic-Ratelimit-Input-Tokens-Reset": reset_time.isoformat().replace("+00:00", "Z")
        }

        result = parse_cooldown_from_response(429, headers)

        # Deve ser aproximadamente 5 minutos (300s), tolerância de 5s
        assert 295 <= result <= 305

    def test_parse_502_503_529_retorna_30(self):
        """HTTP 502/503/529 retorna 30s."""
        from backend.services.ia_manager import parse_cooldown_from_response

        assert parse_cooldown_from_response(502, {}) == 30
        assert parse_cooldown_from_response(503, {}) == 30
        assert parse_cooldown_from_response(529, {}) == 30

    def test_parse_5xx_retorna_15(self):
        """HTTP 5xx genérico retorna 15s."""
        from backend.services.ia_manager import parse_cooldown_from_response

        assert parse_cooldown_from_response(500, {}) == 15
        assert parse_cooldown_from_response(501, {}) == 15
        assert parse_cooldown_from_response(504, {}) == 15


class TestIsGloballyCooledDown:
    """Testes para verificação de cooldown global."""

    def test_is_globally_cooled_down_tem_keys_saudaveis(self):
        """Com keys saudáveis, não está em cooldown."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_cursor.fetchone.side_effect = [
                (3,),  # total_keys
                (2,),  # healthy keys
            ]
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import is_globally_cooled_down

            em_cooldown, segundos = is_globally_cooled_down()

            assert em_cooldown is False
            assert segundos == 0

    def test_is_globally_cooled_down_todas_em_cooldown(self):
        """Com todas keys em cooldown, retorna tempo restante."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_cursor.fetchone.side_effect = [
                (2,),  # total_keys
                (0,),  # healthy = 0
                (120,),  # segundos até próximo cooldown
            ]
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import is_globally_cooled_down

            em_cooldown, segundos = is_globally_cooled_down()

            assert em_cooldown is True
            assert segundos == 120


class TestCheckDailyBudget:
    """Testes para verificação de budget diário."""

    def test_check_daily_budget_dentro_do_limite(self):
        """Dentro do limite deve retornar True."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_cursor.fetchone.return_value = (500000,)  # 500k tokens usados de 2M
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import check_daily_budget

            dentro, restantes = check_daily_budget()

            assert dentro is True
            assert restantes == 1500000

    def test_check_daily_budget_excedeu_limite(self):
        """Excedeu o limite deve retornar False."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_cursor.fetchone.return_value = (2500000,)  # 2.5M tokens usados de 2M
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import check_daily_budget

            dentro, restantes = check_daily_budget()

            assert dentro is False
            assert restantes == 0


class TestCheckTenantBudget:
    """Testes para verificação de budget por tenant."""

    def test_check_tenant_budget_plano_ilimitado(self):
        """Plano ilimitado sempre retorna True."""
        from backend.services.ia_manager import check_tenant_budget

        dentro, restantes = check_tenant_budget(tenant_id=1, plano="ilimitado")

        assert dentro is True
        assert restantes == 999999999

    def test_check_tenant_budget_pro_dentro_limite(self):
        """Tenant pro dentro do limite."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_cursor.fetchone.return_value = (200000,)  # 200k de 800k
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import check_tenant_budget

            dentro, restantes = check_tenant_budget(tenant_id=1, plano="pro")

            assert dentro is True
            assert restantes == 600000


class TestCheckGlobalCallRate:
    """Testes para verificação de taxa de chamadas."""

    def test_check_global_call_rate_dentro_limite(self):
        """Dentro do limite de calls/min."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_cursor.fetchone.return_value = (15,)  # 15 calls no último minuto
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import check_global_call_rate

            with patch('backend.services.ia_manager.GLOBAL_MAX_CALLS_PER_MIN', 30):
                dentro, count = check_global_call_rate()

            assert dentro is True
            assert count == 15

    def test_check_global_call_rate_excedeu_limite(self):
        """Excedeu o limite de calls/min."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_cursor.fetchone.return_value = (35,)  # 35 calls (limite é 30)
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import check_global_call_rate

            with patch('backend.services.ia_manager.GLOBAL_MAX_CALLS_PER_MIN', 30):
                dentro, count = check_global_call_rate()

            assert dentro is False
            assert count == 35


class TestGetRateLimitStatus:
    """Testes para status completo de rate limiting."""

    def test_get_rate_limit_status_retorna_estrutura_completa(self):
        """Deve retornar estrutura completa com budget, keys e tenants."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_cursor.fetchone.side_effect = [
                (1000000,),  # daily_used
                (20,),       # calls_last_min
            ]
            mock_cursor.fetchall.side_effect = [
                [],  # keys
                [],  # top_tenants
            ]
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import get_rate_limit_status

            result = get_rate_limit_status()

            assert "daily_budget" in result
            assert "keys" in result
            assert "calls_last_minute" in result
            assert "max_calls_per_minute" in result
            assert "top_tenants_today" in result

            assert result["daily_budget"]["limit"] == 2000000
            assert result["calls_last_minute"] == 20


class TestRaiseAlert:
    """Testes para criação de alertas."""

    def test_raise_alert_tipo_invalido_ignorado(self):
        """Tipo de alerta inválido deve ser ignorado."""
        from backend.services.ia_manager import raise_alert

        # Não deve lançar exceção
        result = raise_alert(
            tipo="tipo_invalido",
            key_id=1,
            mensagem="Teste"
        )

        assert result is None

    def test_raise_alert_deduplica_alertas_recentes(self):
        """Alertas recentes do mesmo tipo/key não devem ser duplicados."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            # Simular alerta existente nos últimos 5 minutos
            mock_cursor.fetchone.return_value = (1,)
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import raise_alert

            raise_alert(
                tipo="rate_limit",
                key_id=42,
                mensagem="Rate limit exceeded"
            )

            # INSERT não deve ser chamado porque alerta já existe
            assert mock_cursor.execute.call_count == 1  # Só o SELECT

    def test_raise_alert_novo_insere_no_banco(self):
        """Novo alerta deve ser inserido no banco."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            # Nenhum alerta recente
            mock_cursor.fetchone.return_value = None
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import raise_alert

            raise_alert(
                tipo="all_keys_failed",
                key_id=None,
                mensagem="Todas as keys falharam",
                user_id=1
            )

            # SELECT + INSERT
            assert mock_cursor.execute.call_count == 2
            mock_conn.commit.assert_called_once()


class TestDefaultBaseUrl:
    """Testes para URL base por provider."""

    def test_default_base_url_anthropic(self):
        """Provider anthropic tem URL padrão correta."""
        import os
        # Isolar variável de ambiente para testar fallback real do código
        original = os.environ.pop('ANTHROPIC_BASE_URL', None)
        try:
            from backend.services.ia_manager import _default_base_url
            result = _default_base_url("anthropic")
            assert "api.anthropic" in result or "aibee" in result
        finally:
            if original:
                os.environ['ANTHROPIC_BASE_URL'] = original

    def test_default_base_url_openai(self):
        """Provider openai tem URL padrão correta."""
        from backend.services.ia_manager import _default_base_url

        result = _default_base_url("openai")

        assert "api.openai.com" in result

    def test_default_base_url_deepseek(self):
        """Provider deepseek tem URL padrão correta."""
        from backend.services.ia_manager import _default_base_url

        result = _default_base_url("deepseek")

        assert "api.deepseek.com" in result

    def test_default_base_url_desconhecido_retorna_vazio(self):
        """Provider desconhecido retorna string vazia."""
        from backend.services.ia_manager import _default_base_url

        result = _default_base_url("provider_desconhecido")

        assert result == ""


class TestListHealthy:
    """Testes para listagem de keys saudáveis."""

    def test_list_healthy_retorna_lista_de_tuplas(self):
        """Deve retornar lista de (id, encrypted_key, base_url)."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
            mock_cursor.fetchall.return_value = [
                (1, "key1", "https://api1.com"),
                (2, "key2", "https://api2.com"),
            ]
            mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = Mock(return_value=False)

            from backend.services.ia_manager import _list_healthy

            result = _list_healthy("anthropic")

            assert len(result) == 2
            assert result[0] == (1, "key1", "https://api1.com")
            assert result[1] == (2, "key2", "https://api2.com")

    def test_list_healthy_erro_retorna_lista_vazia(self):
        """Erro de conexão retorna lista vazia."""
        with patch('backend.services.ia_manager._connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            from backend.services.ia_manager import _list_healthy

            result = _list_healthy("anthropic")

            assert result == []
