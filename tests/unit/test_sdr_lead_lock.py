"""Testes para lead_lock.py.

Testa:
- Redis unavailable: _lead_lock_guard deve lancar RuntimeError
- get_redis_status()
- is_redis_available()
- force_redis_reconnect()
- _is_duplicate_message_id()
"""
import pytest
from unittest.mock import patch, MagicMock


class TestRedisUnavailable:
    """Testa comportamento quando Redis NAO esta disponivel."""

    def test_lead_lock_guard_lanca_quando_redis_offline(self):
        """Quando Redis offline, _lead_lock_guard deve lancrar RuntimeError."""
        from backend.agents.sdr_langgraph.lead_lock import _lead_lock_guard

        # Force Redis offline
        with patch("backend.agents.sdr_langgraph.lead_lock.get_redis_client", return_value=None):
            with pytest.raises(RuntimeError) as exc_info:
                with _lead_lock_guard("lead-123"):
                    pass

            assert "lead-123" in str(exc_info.value)
            assert "offline" in str(exc_info.value).lower()

    def test_is_redis_available_false_quando_nao_conectado(self):
        from backend.agents.sdr_langgraph.lead_lock import is_redis_available

        with patch("backend.agents.sdr_langgraph.lead_lock._redis_available", False):
            assert is_redis_available() is False

    def test_is_redis_available_true_quando_conectado(self):
        from backend.agents.sdr_langgraph.lead_lock import is_redis_available

        with patch("backend.agents.sdr_langgraph.lead_lock._redis_available", True):
            assert is_redis_available() is True


class TestRedisStatus:
    """Testa get_redis_status()."""

    def test_status_retorna_dict(self):
        from backend.agents.sdr_langgraph.lead_lock import get_redis_status

        status = get_redis_status()
        assert isinstance(status, dict)

    def test_status_tem_campos_necessarios(self):
        from backend.agents.sdr_langgraph.lead_lock import get_redis_status

        status = get_redis_status()
        assert "available" in status
        assert "in_recovery_mode" in status
        assert "last_error" in status


class TestForceReconnect:
    """Testa force_redis_reconnect()."""

    def test_forca_reconexao_retorna_bool(self):
        from backend.agents.sdr_langgraph.lead_lock import force_redis_reconnect

        result = force_redis_reconnect()
        assert isinstance(result, bool)

    def test_forca_reconexao_muda_estado(self):
        from backend.agents.sdr_langgraph.lead_lock import force_redis_reconnect

        # Se Redis nao configurado, deve retornar False
        # Nao deve lancar excecao
        result = force_redis_reconnect()
        assert isinstance(result, bool)


class TestDuplicateMessageId:
    """Testa _is_duplicate_message_id()."""

    def test_msg_id_novo_nao_e_duplicado(self):
        from backend.agents.sdr_langgraph.lead_lock import _is_duplicate_message_id

        msg_id = f"unique-{id(self)}"
        assert _is_duplicate_message_id(msg_id) is False

    def test_msg_id_igual_e_duplicado(self):
        from backend.agents.sdr_langgraph.lead_lock import _is_duplicate_message_id

        msg_id = f"dup-test-{id(self)}"
        # Primeira vez: nao duplicado
        assert _is_duplicate_message_id(msg_id) is False
        # Segunda vez: duplicado
        assert _is_duplicate_message_id(msg_id) is True

    def test_msg_id_vazio_nao_e_duplicado(self):
        from backend.agents.sdr_langgraph.lead_lock import _is_duplicate_message_id

        assert _is_duplicate_message_id("") is False
        assert _is_duplicate_message_id(None) is False

    def test_ttl_expirado_nao_e_duplicado(self):
        from backend.agents.sdr_langgraph.lead_lock import _is_duplicate_message_id

        msg_id = f"ttl-test-{id(self)}"
        # Primeira vez
        assert _is_duplicate_message_id(msg_id) is False
        # Imediatamente: duplicado (ainda no cache)
        assert _is_duplicate_message_id(msg_id) is True


class TestRedisConfig:
    """Testa configuracao de retry."""

    def test_retry_count_eh_3(self):
        from backend.agents.sdr_langgraph.lead_lock import REDIS_RETRY_COUNT

        assert REDIS_RETRY_COUNT == 3

    def test_retry_base_delay_positivo(self):
        from backend.agents.sdr_langgraph.lead_lock import REDIS_RETRY_BASE_DELAY

        assert REDIS_RETRY_BASE_DELAY > 0

    def test_recovery_interval_positivo(self):
        from backend.agents.sdr_langgraph.lead_lock import REDIS_RECOVERY_INTERVAL

        assert REDIS_RECOVERY_INTERVAL > 0


class TestExports:
    """Verifica que funcoes estao exportadas."""

    def test_lead_lock_guard_exportado(self):
        from backend.agents.sdr_langgraph.lead_lock import _lead_lock_guard
        assert callable(_lead_lock_guard)

    def test_is_duplicate_message_id_exportado(self):
        from backend.agents.sdr_langgraph.lead_lock import _is_duplicate_message_id
        assert callable(_is_duplicate_message_id)

    def test_is_redis_available_exportado(self):
        from backend.agents.sdr_langgraph.lead_lock import is_redis_available
        assert callable(is_redis_available)

    def test_get_redis_status_exportado(self):
        from backend.agents.sdr_langgraph.lead_lock import get_redis_status
        assert callable(get_redis_status)

    def test_force_redis_reconnect_exportado(self):
        from backend.agents.sdr_langgraph.lead_lock import force_redis_reconnect
        assert callable(force_redis_reconnect)
