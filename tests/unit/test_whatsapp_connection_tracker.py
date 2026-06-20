"""Testes unitários para whatsapp.connection_tracker (extração pura)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('MEOWHATS_URL', 'http://localhost:3001')
os.environ.setdefault('MEOWHATS_KEY', 'test')

from whatsapp.connection_tracker import (
    _on_qr_timeout,
    _on_qr_success,
    _set_tenant_status,
    _get_tenant_status,
    is_tenant_connected,
    ESTADO_TO_STAGE,
    _QR_TIMEOUT_COUNT,
    _TENANT_STATUS,
    _TENANT_STATUS_LOCK,
)


def _clean():
    _QR_TIMEOUT_COUNT.clear()
    with _TENANT_STATUS_LOCK:
        _TENANT_STATUS.clear()


def test_qr_timeout_increments_and_stops():
    _clean()
    assert _on_qr_timeout("t1") is True   # 1/3
    assert _on_qr_timeout("t1") is True   # 2/3
    assert _on_qr_timeout("t1") is False  # 3/3 -> stop


def test_qr_success_resets_counter():
    _clean()
    _on_qr_timeout("t1")
    _on_qr_success("t1")
    assert "t1" not in _QR_TIMEOUT_COUNT


def test_set_and_get_tenant_status():
    _clean()
    _set_tenant_status("tenant_a", "connected")
    assert _get_tenant_status("tenant_a") == "connected"


def test_is_tenant_connected_true():
    _clean()
    _set_tenant_status("tenant_a", "connected")
    assert is_tenant_connected("tenant_a", fallback_http=False) is True


def test_is_tenant_connected_false():
    _clean()
    _set_tenant_status("tenant_a", "disconnected")
    assert is_tenant_connected("tenant_a", fallback_http=False) is False


def test_is_tenant_connected_unknown_no_fallback():
    _clean()
    assert is_tenant_connected("unknown", fallback_http=False) is False


def test_empty_tenant_returns_empty():
    _clean()
    assert _get_tenant_status("") == ""


def test_estado_to_stage_mapping():
    assert ESTADO_TO_STAGE["intro"] == "intro"
    assert ESTADO_TO_STAGE["won"] == "ganhos"
    assert ESTADO_TO_STAGE["lost"] == "perdidos"
    assert ESTADO_TO_STAGE["handoff"] == "qualificados"
    assert ESTADO_TO_STAGE["scheduled"] == "followup1"


if __name__ == "__main__":
    test_qr_timeout_increments_and_stops()
    test_qr_success_resets_counter()
    test_set_and_get_tenant_status()
    test_is_tenant_connected_true()
    test_is_tenant_connected_false()
    test_is_tenant_connected_unknown_no_fallback()
    test_empty_tenant_returns_empty()
    test_estado_to_stage_mapping()
    print("ALL TESTS PASSED")
