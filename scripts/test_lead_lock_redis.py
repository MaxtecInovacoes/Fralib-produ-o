"""Testes do lock distribuido Redis para SDR 10/10."""

import os
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "")

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))


class TestLeadLockRedis(unittest.TestCase):
    """Lock distribuido Redis para o SDR."""

    def test_redis_lock_quando_disponivel(self):
        """Se Redis ta disponivel, usa Redis lock."""
        from backend.agents.sdr_langgraph import lead_lock
        lead_lock._use_redis = True
        lead_lock._redis_client = MagicMock()
        mock_redis_lock = MagicMock()
        lead_lock._redis_client.lock.return_value = mock_redis_lock
        mock_redis_lock.acquire.return_value = True

        with lead_lock._lead_lock_guard("L_test_redis"):
            # Verifica que o lock foi adquirido
            lead_lock._redis_client.lock.assert_called_once()
            mock_redis_lock.acquire.assert_called_once()

        # Apos sair do context manager, release deve ter sido chamado
        mock_redis_lock.release.assert_called_once()

    def test_fallback_threading_quando_redis_offline(self):
        """Se Redis offline, usa threading.Lock in-memory."""
        from backend.agents.sdr_langgraph import lead_lock
        lead_lock._use_redis = False
        lead_lock._redis_client = None

        with patch.object(lead_lock, '_redis_client', None):
            with patch.object(lead_lock, '_use_redis', False):
                with lead_lock._lead_lock_guard("L_test_thread"):
                    # Deve funcionar sem Redis
                    pass
        # Se chegou aqui sem erro, fallback funcionou

    def test_redis_lock_com_timeout(self):
        """Lock tem timeout de 30s (deadlock protection)."""
        from backend.agents.sdr_langgraph import lead_lock
        lead_lock._use_redis = True
        lead_lock._redis_client = MagicMock()
        mock_redis_lock = MagicMock()
        lead_lock._redis_client.lock.return_value = mock_redis_lock
        mock_redis_lock.acquire.return_value = False  # timeout

        with self.assertRaises(TimeoutError):
            with lead_lock._lead_lock_guard("L_test_timeout"):
                pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
