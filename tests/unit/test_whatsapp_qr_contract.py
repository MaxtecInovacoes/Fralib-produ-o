import inspect
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("DATABASE_URL", "sqlite:///C:/tmp/fralib_whatsapp_unit.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-32-bytes-min")
os.environ.setdefault("MEOWHATS_KEY", "unit-test-meowhats-key")
for rel in ("backend/core", "backend"):
    sys.path.insert(0, str(ROOT / rel))

from endpoints import whatsapp_endpoints as whatsapp


@pytest.mark.unit
def test_qr_payload_accepts_meowhats_field_variants():
    assert whatsapp._session_payload({"status": "qr", "qr": "a"}) == {"status": "qr", "qr": "a"}
    assert whatsapp._session_payload({"status": "qr", "qrCode": "b"}) == {"status": "qr", "qr": "b"}
    assert whatsapp._session_payload({"status": "qr", "qr_code": "c"}) == {"status": "qr", "qr": "c"}
    assert whatsapp._session_payload({"status": "qr", "qr": True}) == {"status": "qr"}


@pytest.mark.unit
def test_connected_states_are_normalized_for_frontend():
    assert whatsapp._session_payload({"status": "open"}) == {"status": "connected", "connected": True}
    assert whatsapp._session_payload({"status": "authenticated"}) == {
        "status": "connected",
        "connected": True,
    }
    assert whatsapp._session_payload({"connected": True}) == {"status": "connected", "connected": True}


@pytest.mark.unit
def test_connect_endpoint_does_not_restart_meowhats_or_clear_session():
    source = inspect.getsource(whatsapp.whatsapp_connect)
    assert "subprocess" not in source
    assert "pm2" not in source


@pytest.mark.unit
def test_disconnect_endpoint_logs_out_and_requires_new_qr():
    source = inspect.getsource(whatsapp.whatsapp_disconnect)
    assert "/api/sessions/{tenant_id}/logout" in source
    assert "/api/sessions/{tenant_id}/disconnect" not in source
    assert "subprocess" not in source
    assert "pm2" not in source
    assert "_limpar_sessao_db" not in source
    assert '"requires_qr": True' in source


@pytest.mark.unit
def test_admin_frontend_handles_qr_status_contract():
    source = (ROOT / "frontend" / "partials" / "admin" / "_scripts.html").read_text(encoding="utf-8")
    assert "data.qr || data.qrCode || data.qr_code" in source
    assert "typeof value === 'string'" in source
    assert "verificarStatusWhatsApp(true)" in source
    assert "tentativas >= 45" in source
    assert "Toast.error('Erro ao buscar QR: ' + e.message)" in source
    assert "renovarQRCodeWhatsApp" in source
    assert "/api/whatsapp/status" in source
    assert "qr-image-shell" in source
    assert "width:340px;height:340px" in source
    assert "border-radius:0;image-rendering:pixelated" in source
    assert "QR expirando. Gerando novo QR automaticamente" in source
    assert "attempts >= 30" in source


@pytest.mark.unit
def test_dashboard_frontend_handles_qr_status_contract():
    dashboard_scripts = ROOT / "frontend" / "partials" / "dashboard" / "_scripts.html"
    if dashboard_scripts.exists():
        source = dashboard_scripts.read_text(encoding="utf-8")
        assert "typeof qr === 'string'" in source
        assert "_whatsappPayloadConnected(data)" in source
        assert "mostrarQRCodeModal(qr)" in source
    else:
        source = (ROOT / "frontend" / "partials" / "admin" / "_scripts.html").read_text(
            encoding="utf-8"
        )
        assert "typeof value === 'string'" in source
        assert "verificarStatusWhatsApp(true)" in source
    assert "data.qr || data.qrCode || data.qr_code" in source
