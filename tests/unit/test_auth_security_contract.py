import os
import sys
from unittest.mock import Mock


os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-32-bytes-min")
os.environ.setdefault("SUPERADMIN_EMAIL", "admin@example.com")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend", "core"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "backend", "endpoints")
)

from endpoints.auth_endpoints import _client_ip


def test_client_ip_uses_last_forwarded_ip_only_from_trusted_proxy():
    request = Mock()
    request.client.host = "127.0.0.1"
    request.headers = {"x-forwarded-for": "203.0.113.10, 198.51.100.8"}

    assert _client_ip(request) == "198.51.100.8"


def test_client_ip_ignores_forwarded_ip_from_direct_client():
    request = Mock()
    request.client.host = "203.0.113.10"
    request.headers = {"x-forwarded-for": "198.51.100.8"}

    assert _client_ip(request) == "203.0.113.10"
