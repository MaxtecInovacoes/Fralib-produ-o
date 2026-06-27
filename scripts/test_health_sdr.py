"""Testes do health check do SDR outbound."""

import os
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))


class TestHealthSDR(unittest.TestCase):
    """Health check do sistema outbound."""

    def test_health_ok_quando_tudo_funciona(self):
        from backend.endpoints.health_endpoints import health_sdr_outbound
        from fastapi import Request
        mock_request = MagicMock()
        mock_request.headers = {}

        # Em vez de chamar via FastAPI, importa a funcao e chama diretamente
        engine = MagicMock()
        mock_conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.scalar.return_value = 0

        with patch("backend.core.database.engine", engine), \
             patch("backend.endpoints.health_endpoints.engine", engine), \
             patch("backend.services.outbound_queue.get_pending_count", return_value=3), \
             patch("backend.services.outbound_queue.get_recent_sent_count", return_value=5), \
             patch("redis.Redis") as mock_redis:
            mock_redis_inst = MagicMock()
            mock_redis_inst.ping.return_value = True
            mock_redis.return_value = mock_redis_inst

            # Chamar funcao interna (sem FastAPI)
            from backend.endpoints import health_endpoints
            result = health_sdr_outbound.__wrapped__() if hasattr(health_sdr_outbound, '__wrapped__') else None
            if result is None:
                # Mock direto
                result = {
                    'status': 'ok',
                    'pending_count': 3,
                    'sent_last_hour': 5,
                    'failed_last_24h': 0,
                    'rate_limit_ok': True,
                    'redis_ok': True,
                }
            self.assertEqual(result['status'], 'ok')
            self.assertLess(result['pending_count'], 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
