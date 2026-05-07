from fastapi import APIRouter, Depends, HTTPException
import httpx
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import text
from auth import get_current_user
from database import get_db
import os

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

MEOWHATS_URL = os.getenv("MEOWHATS_URL", "http://localhost:3001")
MEOWHATS_KEY = os.getenv("MEOWHATS_KEY", "1763kovQ@")

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
async def whatsapp_connect(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    plano = db.execute(text("SELECT plano FROM users WHERE id=:id"), {"id": usuario["id"]}).scalar()
    if plano not in ("pro", "beta", "admin"):
        raise HTTPException(403, "WhatsApp disponivel apenas no plano Pro.")
    tenant_id = _tenant(usuario["id"])
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(f"{MEOWHATS_URL}/api/sessions/{tenant_id}/disconnect", headers=_headers())
            await asyncio.sleep(1)
            await c.post(f"{MEOWHATS_URL}/api/sessions/{tenant_id}/connect", headers=_headers())
            await asyncio.sleep(3)
            r = await c.get(f"{MEOWHATS_URL}/api/sessions", headers=_headers())
            if r.status_code == 200:
                for s in r.json():
                    if s.get("tenantId") == tenant_id:
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
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"{MEOWHATS_URL}/api/sessions/{tenant_id}/disconnect", headers=_headers())
            return r.json()
    except Exception as e:
        return {"status": "error", "detail": str(e)}
