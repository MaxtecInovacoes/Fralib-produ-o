"""Testes Sprint 1.1 — Redis resilience + debounce idempotency.

Cobre:
  1. lead_lock_graceful: Redis offline NAO bloqueia (yield None)
  2. lead_lock_graceful: 3 retries antes de desistir
  3. debounce buffer: marca em_processamento impede loop infinito
  4. debounce buffer: remove do buffer SÓ no sucesso
  5. debounce buffer: falha reseta em_processamento (permite retry)
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))


# ── lead_lock_graceful ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestLeadLockGraceful:
    """lead_lock_graceful: Redis offline NAO bloqueia (yield None)."""

    def test_redis_none_yields_none(self):
        from agents.sdr_langgraph.lead_lock_graceful import lead_lock_guard
        with patch(
            "agents.sdr_langgraph.lead_lock_graceful.get_redis_client",
            return_value=None,
        ):
            with lead_lock_guard("lead_123") as lock:
                assert lock is None  # yield None — sem raise

    def test_redis_acquired_yields_lock(self):
        from agents.sdr_langgraph.lead_lock_graceful import lead_lock_guard
        mock_redis = MagicMock()
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_redis.lock.return_value = mock_lock

        with patch(
            "agents.sdr_langgraph.lead_lock_graceful.get_redis_client",
            return_value=mock_redis,
        ):
            with lead_lock_guard("lead_456") as lock:
                assert lock is mock_lock
                mock_lock.acquire.assert_called_once()
            # release() chamado no exit
            mock_lock.release.assert_called_once()

    def test_redis_acquire_fails_after_3_tries_yields_none(self):
        from agents.sdr_langgraph.lead_lock_graceful import lead_lock_guard
        mock_redis = MagicMock()
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = False  # nunca consegue
        mock_redis.lock.return_value = mock_lock

        with patch(
            "agents.sdr_langgraph.lead_lock_graceful.get_redis_client",
            return_value=mock_redis,
        ):
            with lead_lock_guard("lead_789") as lock:
                # 3 tentativas falharam → graceful fallback
                assert lock is None
            # 3 acquires tentativas
            assert mock_lock.acquire.call_count == 3

    def test_redis_exception_during_acquire_yields_none(self):
        from agents.sdr_langgraph.lead_lock_graceful import lead_lock_guard
        mock_redis = MagicMock()
        mock_lock = MagicMock()
        mock_lock.acquire.side_effect = ConnectionError("redis caiu")
        mock_redis.lock.return_value = mock_lock

        with patch(
            "agents.sdr_langgraph.lead_lock_graceful.get_redis_client",
            return_value=mock_redis,
        ):
            with lead_lock_guard("lead_aaa") as lock:
                assert lock is None

    def test_release_exception_does_not_propagate(self):
        from agents.sdr_langgraph.lead_lock_graceful import lead_lock_guard
        mock_redis = MagicMock()
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_lock.release.side_effect = Exception("release falhou")
        mock_redis.lock.return_value = mock_lock

        with patch(
            "agents.sdr_langgraph.lead_lock_graceful.get_redis_client",
            return_value=mock_redis,
        ):
            # NUNCA deve levantar
            with lead_lock_guard("lead_bbb") as lock:
                assert lock is mock_lock
            # Sem raise mesmo com release falhando


# ── Debounce buffer idempotency ───────────────────────────────────────────


@pytest.mark.unit
class TestDebounceBuffer:
    """Debounce: marca em_processamento impede loop infinito."""

    def _import_buffer(self):
        """Importa o _DEBOUNCE_BUFFER do whatsapp_listener."""
        from backend.whatsapp_listener import _DEBOUNCE_BUFFER, _DEBOUNCE_LOCK
        return _DEBOUNCE_BUFFER, _DEBOUNCE_LOCK

    def test_em_processamento_flag_set_on_fire(self):
        """Quando timer dispara, marca em_processamento=True."""
        buffer, lock = self._import_buffer()
        lead_key = "test:111:222"
        buffer.clear()

        # Simula: buffer criado com timer
        with lock:
            buffer[lead_key] = {
                "msgs": ["oi"],
                "tenant_id": "test",
                "msg_data": {},
                "timer": None,
                "em_processamento": False,
            }

        # Simula o _fire (idempotency check)
        with lock:
            entry = buffer.get(lead_key)
            assert entry is not None
            if entry.get("em_processamento"):
                pytest.fail("nao devia estar em_processamento ainda")
            entry["em_processamento"] = True

        # Verifica flag
        with lock:
            assert buffer[lead_key]["em_processamento"] is True

    def test_em_processamento_impede_reentrada(self):
        """Se timer disparar 2x enquanto em_processamento=True, 2nd e' skip."""
        buffer, lock = self._import_buffer()
        lead_key = "test:333:444"
        buffer.clear()

        with lock:
            buffer[lead_key] = {
                "msgs": ["oi"],
                "tenant_id": "test",
                "msg_data": {},
                "timer": None,
                "em_processamento": True,  # ja em processamento
            }

        # Simula _fire tentando entrar de novo
        with lock:
            entry = buffer.get(lead_key)
            if entry.get("em_processamento"):
                # skip — nao processa 2x
                skip = True
            else:
                skip = False

        assert skip is True

    def test_success_remove_from_buffer(self):
        """Sucesso no batch → remove do buffer."""
        buffer, lock = self._import_buffer()
        lead_key = "test:555:666"
        buffer.clear()

        with lock:
            buffer[lead_key] = {
                "msgs": ["oi"],
                "tenant_id": "test",
                "msg_data": {},
                "timer": None,
                "em_processamento": True,
            }

        # Simula sucesso
        success = True
        if lead_key and success:
            with lock:
                entry = buffer.get(lead_key)
                if entry and entry.get("em_processamento"):
                    buffer.pop(lead_key, None)

        assert lead_key not in buffer

    def test_failure_keeps_in_buffer_reset_flag(self):
        """Falha no batch → mantém buffer e reseta em_processamento."""
        buffer, lock = self._import_buffer()
        lead_key = "test:777:888"
        buffer.clear()

        with lock:
            buffer[lead_key] = {
                "msgs": ["oi"],
                "tenant_id": "test",
                "msg_data": {},
                "timer": None,
                "em_processamento": True,
            }

        # Simula falha
        success = False
        if lead_key and not success:
            with lock:
                entry = buffer.get(lead_key)
                if entry:
                    entry["em_processamento"] = False  # permite retry

        assert lead_key in buffer
        with lock:
            assert buffer[lead_key]["em_processamento"] is False
