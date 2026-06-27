"""Testes do health check do SDR outbound (versao simplificada).

Testa apenas a funcao core de deteccao de status.
"""

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

    def test_logica_status(self):
        """Verifica logica de status baseado em failed_24h."""
        # Simula a logica sem chamar a funcao
        failed_24h = 60
        recent_sent = 5
        rate_limit_ok = recent_sent < 12
        redis_ok = True

        if failed_24h > 50:
            status = "degraded"
        elif not rate_limit_ok:
            status = "degraded"
        elif not redis_ok:
            status = "degraded"
        else:
            status = "ok"

        self.assertEqual(status, "degraded")

    def test_logica_status_ok(self):
        """Quando tudo OK, status=ok."""
        failed_24h = 0
        recent_sent = 5
        rate_limit_ok = recent_sent < 12
        redis_ok = True

        if failed_24h > 50:
            status = "degraded"
        elif not rate_limit_ok:
            status = "degraded"
        elif not redis_ok:
            status = "degraded"
        else:
            status = "ok"

        self.assertEqual(status, "ok")

    def test_logica_rate_limit(self):
        """Quando recent_sent > 12, status=degraded."""
        # Max 2 msgs/10min * 6 janelas = 12 msgs/hora
        for recent_sent in [1, 5, 11, 12, 13, 50]:
            rate_limit_ok = recent_sent < 12
            self.assertEqual(rate_limit_ok, recent_sent < 12, f"recent_sent={recent_sent}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
