"""
connection_tracker.py — Gerenciamento de status de conexão por tenant
e mapeamento de estados Franz → sdr_stage kanban.

Extraído de whatsapp_listener.py (extração pura, sem reescrita).
"""
import os
import threading
import logging

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logger = logging.getLogger("whatsapp_listener")

MEOWHATS_HTTP = os.getenv("MEOWHATS_URL", "http://localhost:3001")
MEOWHATS_KEY = os.getenv("MEOWHATS_KEY", "")

# Cache do status de conexao por tenant, alimentado por eventos connection.update
# do meowhats. Multi-tenant pos-fix (2026-05-13): meowhats emite "connected",
# "pairing", "rejected", "logged_out", "disconnected", "reconnecting", "qr",
# "timeout". So "connected" significa que o device esta pareado e pronto para
# enviar mensagens.
_TENANT_STATUS: dict[str, str] = {}
_TENANT_STATUS_LOCK = threading.Lock()
_CONNECTED_STATUSES = frozenset({"connected", "open", "authenticated"})

# Contador de QR timeouts por tenant (anti-loop zumbi)
_QR_TIMEOUT_COUNT: dict[str, int] = {}
_QR_MAX_RETRIES = 3


def _on_qr_timeout(tenant_id: str) -> bool:
    """Chamado quando QR code expira sem ser escaneado. Retorna False se deve parar."""
    _QR_TIMEOUT_COUNT[tenant_id] = _QR_TIMEOUT_COUNT.get(tenant_id, 0) + 1
    count = _QR_TIMEOUT_COUNT[tenant_id]
    if count >= _QR_MAX_RETRIES:
        print(f"[WPP] {tenant_id}: QR timeout {count}x — parando tentativas. Reconectar manualmente.")
        return False
    print(f"[WPP] {tenant_id}: QR timeout ({count}/{_QR_MAX_RETRIES})")
    return True


def _on_qr_success(tenant_id: str):
    """Chamado quando QR é escaneado com sucesso."""
    _QR_TIMEOUT_COUNT.pop(tenant_id, None)


def _set_tenant_status(tenant_id: str, status: str) -> None:
    if not tenant_id or not status:
        return
    with _TENANT_STATUS_LOCK:
        _TENANT_STATUS[tenant_id] = status


def _get_tenant_status(tenant_id: str) -> str:
    if not tenant_id:
        return ""
    with _TENANT_STATUS_LOCK:
        return _TENANT_STATUS.get(tenant_id, "")


def is_tenant_connected(tenant_id: str, *, fallback_http: bool = True) -> bool:
    """Retorna True se o tenant esta com WhatsApp pareado e pronto para envio.

    Usa o cache local (alimentado pelo WebSocket). Se o cache esta vazio para
    aquele tenant e fallback_http=True, consulta GET /api/sessions/{id}/status
    e cacheia o resultado. Chame com fallback_http=False em hot paths onde
    consultas HTTP sao caras.
    """
    cached = _get_tenant_status(tenant_id)
    if cached:
        return cached in _CONNECTED_STATUSES
    if not fallback_http:
        return False
    try:
        import httpx
        with httpx.Client(timeout=3) as c:
            r = c.get(
                f"{MEOWHATS_HTTP}/api/sessions/{tenant_id}/status",
                headers={"X-API-Key": MEOWHATS_KEY},
            )
            if r.status_code == 200:
                status = (r.json() or {}).get("status", "")
                _set_tenant_status(tenant_id, status)
                return status in _CONNECTED_STATUSES
    except Exception as e:
        logger.debug(f"is_tenant_connected fallback HTTP falhou ({tenant_id}): {e}")
    return False

# Mapeamento estado Franz -> sdr_stage kanban
ESTADO_TO_STAGE = {
    # Stages novos (Franz prompt v2)
    "intro":       "intro",
    "qualify":     "intro",
    "proof":       "followup1",
    "link":        "followup1",
    "value":       "followup2",
    "price":       "negociacao",
    "negotiate":   "negociacao",
    "close":       "negociacao",
    "won":         "ganhos",
    "lost":        "perdidos",
    # Stages legados (compatibilidade)
    "hook":        "intro",
    "pain":        "followup1",
    "amplify":     "followup1",
    "tease":       "followup2",
    "reveal":      "negociacao",
    "feedback":    "negociacao",
    "urgency":     "negociacao",
    "followup1":   "followup1",
    "followup2":   "followup2",
    "rapport":     "followup2",
    "education":   "followup2",
    "negotiation": "negociacao",
    "offer":       "negociacao",
    "qualificado": "qualificados",
    "handoff":     "qualificados",
    "scheduled":   "followup1",
    # Stages extras (SDR)
    "opt_out":     "perdidos",
    "followup_24h": "followup1",
    "followup_72h": "followup2",
}
