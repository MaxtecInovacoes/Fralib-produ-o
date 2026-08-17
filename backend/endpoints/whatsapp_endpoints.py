from fastapi import APIRouter, Depends, HTTPException
import httpx
import asyncio
import time
from sqlalchemy.orm import Session
from sqlalchemy import text
from auth import get_current_user
from database import get_db
import os

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

MEOWHATS_URL = os.getenv("MEOWHATS_URL", "http://localhost:3001")
MEOWHATS_KEY = os.getenv("MEOWHATS_KEY", "1763kovQ@")
WHATSMEOW_DB = os.getenv("WHATSMEOW_DB_URL", "postgres://postgres:fralib2024@localhost:5433/whatsmeow?sslmode=disable")

def _headers():
    return {"X-API-Key": MEOWHATS_KEY}

def _tenant(user_id: int) -> str:
    return f"fralib_user_{user_id}"

async def _get_session(tenant_id: str):
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.get(f"{MEOWHATS_URL}/api/sessions", headers=_headers())
        if r.status_code == 200:
            for s in r.json():
                if s.get("tenantId") == tenant_id:
                    return s
    return None

def _limpar_sessao_db(tenant_id: str):
    """Deleta dados de sessão do whatsmeow DB pra forçar novo QR."""
    from sqlalchemy import create_engine
    try:
        eng = create_engine(WHATSMEOW_DB)
        with eng.connect() as conn:
            # Buscar JID do tenant
            row = conn.execute(text("SELECT jid FROM tenant_device WHERE tenant_id=:tid"), {"tid": tenant_id}).fetchone()
            if row:
                jid = row[0]
                conn.execute(text("DELETE FROM whatsmeow_device WHERE jid=:jid"), {"jid": jid})
                conn.execute(text("DELETE FROM tenant_device WHERE tenant_id=:tid"), {"tid": tenant_id})
                conn.commit()
    except Exception as e:
        print(f"[WPP] Erro ao limpar sessão DB: {e}")

@router.get("/status")
async def whatsapp_status(usuario: dict = Depends(get_current_user)):
    tenant_id = _tenant(usuario["id"])
    try:
        s = await _get_session(tenant_id)
        if not s:
            return {"status": "disconnected"}
        result = {"status": s.get("status", "unknown")}
        if s.get("status") == "qr" and s.get("qr"):
            result["qr"] = s["qr"]
        return result
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.post("/connect")
def whatsapp_connect(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    plano = db.execute(text("SELECT plano FROM users WHERE id=:id"), {"id": usuario["id"]}).scalar()
    if (plano or "").lower() not in ("pro", "starter", "beta", "admin", "trial"):
        raise HTTPException(403, "Conecte o WhatsApp apos assinar um plano.")
    tenant_id = _tenant(usuario["id"])

    # Verificar se já está conectado — não reconectar
    try:
        with httpx.Client(timeout=5) as c:
            r = c.get(f"{MEOWHATS_URL}/api/sessions/{tenant_id}/status", headers=_headers())
            if r.status_code == 200:
                data = r.json()
                if data.get("connected") or data.get("status") == "connected":
                    return {"status": "connected", "mensagem": "WhatsApp ja esta conectado"}
    except Exception:
        pass

    try:
        # 1. Desconectar sessão existente no meowhats
        with httpx.Client(timeout=10) as c:
            c.post(f"{MEOWHATS_URL}/api/sessions/{tenant_id}/disconnect", headers=_headers())
            time.sleep(1)

        # 2. Limpar sessão antiga do banco (forçar novo QR)
        _limpar_sessao_db(tenant_id)
        time.sleep(1)

        # 3. Reiniciar meowhats pra pegar estado limpo
        import subprocess
        subprocess.run(["pm2", "restart", "meowhats"], capture_output=True, timeout=10)
        time.sleep(3)

        # 4. Conectar sessão nova
        with httpx.Client(timeout=10) as c:
            c.post(f"{MEOWHATS_URL}/api/sessions/{tenant_id}/connect", headers=_headers())
            time.sleep(4)
            r = c.get(f"{MEOWHATS_URL}/api/sessions/{tenant_id}/status", headers=_headers())
            if r.status_code == 200:
                s = r.json()
                if s.get("status") == "qr" and s.get("qr"):
                    return {"status": "qr", "qr": s["qr"]}
                if s.get("status") == "connected":
                    return {"status": "connected", "connected": True}
        return {"status": "connecting"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.get("/qr")
async def whatsapp_qr(usuario: dict = Depends(get_current_user)):
    tenant_id = _tenant(usuario["id"])
    try:
        s = await _get_session(tenant_id)
        if s and s.get("status") == "qr" and s.get("qr"):
            return {"status": "qr", "qr": s["qr"]}
        if s:
            return {"status": s.get("status", "unknown")}
        return {"status": "disconnected"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.post("/disconnect")
async def whatsapp_disconnect(usuario: dict = Depends(get_current_user)):
    tenant_id = _tenant(usuario["id"])
    try:
        # 1. Desconectar no meowhats
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(f"{MEOWHATS_URL}/api/sessions/{tenant_id}/disconnect", headers=_headers())

        # 2. Limpar sessão do banco (delete device)
        _limpar_sessao_db(tenant_id)

        # 3. Reiniciar meowhats
        subprocess.run(["pm2", "restart", "meowhats"], capture_output=True, timeout=10)

        return {"status": "disconnected"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ══════════════════════════════════════════════════════════════════
# BOT CONFIG — Toggles do chatbot WhatsApp
# ══════════════════════════════════════════════════════════════════

@router.get("/bot-config")
def get_bot_config(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Retorna configurações do bot para o dashboard."""
    uid = user.get('id') if isinstance(user, dict) else user.id
    rows = db.execute(
        text("SELECT config_key, config_value FROM user_configs WHERE user_id = :uid"),
        {"uid": uid}
    ).fetchall()
    config = {r[0]: r[1] for r in rows}
    return {
        "bot_ignore_saved_contacts": config.get("bot_ignore_saved_contacts", "0") in ("1", "true", "sim"),
    }


@router.post("/bot-config")
def update_bot_config(body: dict, db: Session = Depends(get_db), user=Depends(get_current_user)):
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
    db.commit()
    return {"updated": updated, "status": "ok"}
