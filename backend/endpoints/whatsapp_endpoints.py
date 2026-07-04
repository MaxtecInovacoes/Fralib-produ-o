from fastapi import APIRouter, Depends, HTTPException
import httpx
import asyncio
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.services.credits_manager import plano_tem_sdr
from backend.services.sdr_settings import fetch_sdr_settings, save_sdr_settings
import os

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

MEOWHATS_URL = os.getenv("MEOWHATS_URL", "http://localhost:3001")
MEOWHATS_KEY = os.getenv("MEOWHATS_KEY", "").strip()
_CONNECTED_STATES = {"connected", "open", "authenticated"}
_QR_KEYS = ("qr", "qrCode", "qr_code")

def _headers():
    if not MEOWHATS_KEY:
        raise HTTPException(503, "MEOWHATS_KEY ausente na configuração do servidor")
    return {"X-API-Key": MEOWHATS_KEY}

def _tenant(user_id: int) -> str:
    return f"fralib_user_{user_id}"


def _session_tenant_matches(session: dict, tenant_id: str) -> bool:
    return session.get("tenantId") == tenant_id or session.get("id") == tenant_id


def _extract_qr(session: dict | None) -> str:
    if not session:
        return ""
    for key in _QR_KEYS:
        value = session.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _session_status(session: dict | None) -> str:
    if not session:
        return "disconnected"
    status = str(session.get("status") or "").lower()
    if not status and session.get("connected"):
        status = "connected"
    return status or "unknown"


def _session_payload(session: dict | None) -> dict:
    status = _session_status(session)
    result = {"status": "connected" if status in _CONNECTED_STATES else status}
    qr = _extract_qr(session)
    if qr:
        result["status"] = "qr"
        result["qr"] = qr
    if status in _CONNECTED_STATES:
        result["connected"] = True
    return result

async def _get_session(tenant_id: str):
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.get(f"{MEOWHATS_URL}/api/sessions", headers=_headers())
        if r.status_code == 200:
            for s in r.json():
                if _session_tenant_matches(s, tenant_id):
                    return s
    return None


async def _get_session_status_direct(tenant_id: str) -> dict | None:
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.get(
            f"{MEOWHATS_URL}/api/sessions/{tenant_id}/status",
            headers=_headers(),
        )
        if r.status_code == 200:
            return r.json()
    return None


async def _get_session_any(tenant_id: str) -> dict | None:
    direct = await _get_session_status_direct(tenant_id)
    if direct and (_extract_qr(direct) or _session_status(direct) != "qr"):
        return direct
    listed = await _get_session(tenant_id)
    return listed or direct


async def _wait_for_qr_or_connected(tenant_id: str, attempts: int = 24, delay: float = 1.0) -> dict:
    last_payload = {"status": "connecting"}
    for _ in range(attempts):
        session = await _get_session_any(tenant_id)
        payload = _session_payload(session)
        last_payload = payload
        if payload.get("qr") or payload.get("connected"):
            return payload
        await asyncio.sleep(delay)
    return last_payload

@router.get("/status")
async def whatsapp_status(usuario: dict = Depends(get_current_user)):
    tenant_id = _tenant(usuario["id"])
    try:
        return _session_payload(await _get_session_any(tenant_id))
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.post("/connect")
async def whatsapp_connect(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    row = db.execute(
        text("SELECT plano, status, trial_expires_at FROM users WHERE id=:id"),
        {"id": usuario["id"]},
    ).fetchone()
    plano = row[0] if row else "trial"
    status = row[1] if row else ""
    trial_expires_at = row[2] if row else None
    if not plano_tem_sdr(plano, status, trial_expires_at):
        raise HTTPException(
            403,
            "WhatsApp/SDR esta disponivel no Trial ativo e nos planos Pro ou Ilimitado. Starter nao inclui SDR.",
        )
    tenant_id = _tenant(usuario["id"])

    # Verificar estado atual. Se ja existe QR pendente, retorna sem recriar sessao.
    try:
        current = _session_payload(await _get_session_any(tenant_id))
        if current.get("qr"):
            return current
        if current.get("connected"):
            return {"status": "connected", "connected": True, "mensagem": "WhatsApp ja esta conectado"}
    except Exception:
        pass

    try:
        # Pede conexao e aguarda o QR. Nao reinicia meowhats aqui: reinicio em
        # fluxo de usuario cria corrida e pode apagar o QR recem-gerado.
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"{MEOWHATS_URL}/api/sessions/{tenant_id}/connect",
                headers=_headers(),
            )
            if r.status_code >= 400:
                raise HTTPException(502, f"Meowhats recusou connect: {r.text[:160]}")
            try:
                immediate = _session_payload(r.json())
                if immediate.get("qr") or immediate.get("connected"):
                    return immediate
            except Exception:
                pass
        payload = await _wait_for_qr_or_connected(tenant_id)
        if payload.get("qr") or payload.get("connected"):
            return payload
        return {"status": payload.get("status", "connecting") or "connecting"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.get("/qr")
async def whatsapp_qr(usuario: dict = Depends(get_current_user)):
    tenant_id = _tenant(usuario["id"])
    try:
        return _session_payload(await _get_session_any(tenant_id))
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.post("/disconnect")
async def whatsapp_disconnect(usuario: dict = Depends(get_current_user)):
    tenant_id = _tenant(usuario["id"])
    try:
        # Meowhats /disconnect so derruba o socket e preserva credenciais.
        # O painel "Desconectar" deve invalidar o pareamento para exigir QR novo.
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"{MEOWHATS_URL}/api/sessions/{tenant_id}/logout",
                headers=_headers(),
            )
            if r.status_code >= 400:
                raise HTTPException(502, f"Meowhats recusou logout: {r.text[:160]}")

        return {"status": "disconnected", "requires_qr": True}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ══════════════════════════════════════════════════════════════════
# BOT CONFIG — Toggles do chatbot WhatsApp
# ══════════════════════════════════════════════════════════════════

@router.get("/bot-config")
async def get_bot_config(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Retorna configurações do bot para o dashboard."""
    uid = user.get('id') if isinstance(user, dict) else user.id
    rows = db.execute(
        text("SELECT config_key, config_value FROM user_configs WHERE user_id = :uid"),
        {"uid": uid}
    ).fetchall()
    config = {r[0]: r[1] for r in rows}
    sdr_config = fetch_sdr_settings(db, uid)
    return {
        "bot_ignore_saved_contacts": bool(
            sdr_config.get("bot_ignore_saved_contacts")
            or config.get("bot_ignore_saved_contacts", "0") in ("1", "true", "sim")
        ),
    }


@router.post("/bot-config")
async def update_bot_config(body: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Atualiza toggle de config do bot."""
    uid = user.get('id') if isinstance(user, dict) else user.id
    allowed_keys = ["bot_ignore_saved_contacts"]
    updated = []
    for key in allowed_keys:
        if key in body:
            value = "1" if body[key] in (True, "1", "true", "sim") else "0"
            db.execute(
                text("""
                    INSERT INTO user_configs (user_id, config_key, config_value, updated_at)
                    VALUES (:uid, :key, :val, NOW())
                    ON CONFLICT (user_id, config_key) DO UPDATE SET config_value = :val, updated_at = NOW()
                """),
                {"uid": uid, "key": key, "val": value}
            )
            updated.append(key)
            if key == "bot_ignore_saved_contacts":
                sdr_config = fetch_sdr_settings(db, uid)
                sdr_config["bot_ignore_saved_contacts"] = value == "1"
                save_sdr_settings(db, uid, sdr_config)
    db.commit()
    return {"updated": updated, "status": "ok"}
