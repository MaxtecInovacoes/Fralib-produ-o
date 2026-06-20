"""
PR15: Tracking de visitas nos sites gerados.

Pixel inline reporta page view e clicks em wa.me/tel:.
Endpoints publicos (sem auth) - visitantes do site nao tem JWT.
Rate limit por IP via slowapi. IP/UA hasheados (sem PII).
Deduplicacao: mesma combinacao (lead_id, ip_hash, ua_hash) em <30min = 1 view.
"""

import hashlib
import os
import sys
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel, Field

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "core"))
from backend.core.database import get_db
from rate_limiter import limiter

router = APIRouter(prefix="/api/track", tags=["tracking"])
log = logging.getLogger("uvicorn")

_TRACK_SALT = os.getenv("TRACKING_SALT", "fralib-tracking-default-salt-v1")


def _hash(s: str) -> str:
    return hashlib.sha256((s + _TRACK_SALT).encode("utf-8")).hexdigest()[:32]


class TrackViewRequest(BaseModel):
    lead_id: str = Field(..., min_length=1, max_length=100)


class TrackClickRequest(BaseModel):
    lead_id: str = Field(..., min_length=1, max_length=100)
    tipo: str = Field(..., pattern=r"^(wa|tel)$")


class TrackLandingRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=50)
    evento: str = Field(..., min_length=1, max_length=50)
    valor_extra: Optional[str] = Field(None, max_length=255)


def _lead_existe(db: Session, lead_id: str) -> bool:
    # Tracking é público: só aceita leads com site publicado (status=concluido).
    # Evita enumeração de IDs de leads não publicados.
    row = db.execute(
        text("SELECT 1 FROM leads WHERE id=:id AND status='concluido'"),
        {"id": lead_id},
    ).fetchone()
    return row is not None


def _registrar_evento(
    db: Session, lead_id: str, evento: str, ip_hash: str, ua_hash: str
) -> bool:
    """Retorna True se inseriu (nao era duplicata em 30min)."""
    dup = db.execute(
        text("""
        SELECT 1 FROM site_visitas
        WHERE lead_id=:lid AND evento=:ev AND ip_hash=:ih AND ua_hash=:uh
          AND criado_em > (NOW() - INTERVAL '30 minutes')
        LIMIT 1
    """),
        {"lid": lead_id, "ev": evento, "ih": ip_hash, "uh": ua_hash},
    ).fetchone()
    if dup:
        return False
    db.execute(
        text("""
        INSERT INTO site_visitas (lead_id, evento, ip_hash, ua_hash)
        VALUES (:lid, :ev, :ih, :uh)
    """),
        {"lid": lead_id, "ev": evento, "ih": ip_hash, "uh": ua_hash},
    )
    db.commit()
    return True


@router.post("/view")
@limiter.limit("60/minute")
async def track_view(
    request: Request, req: TrackViewRequest, db: Session = Depends(get_db)
):
    if not _lead_existe(db, req.lead_id):
        return {"ok": False, "motivo": "lead nao encontrado"}
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    _registrar_evento(db, req.lead_id, "view", _hash(ip), _hash(ua))
    return {"ok": True}


@router.post("/click")
@limiter.limit("120/minute")
async def track_click(
    request: Request, req: TrackClickRequest, db: Session = Depends(get_db)
):
    if not _lead_existe(db, req.lead_id):
        return {"ok": False, "motivo": "lead nao encontrado"}
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    _registrar_evento(db, req.lead_id, "click_" + req.tipo, _hash(ip), _hash(ua))
    return {"ok": True}


@router.post("/landing")
@limiter.limit("120/minute")
async def track_landing(
    request: Request, req: TrackLandingRequest, db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")

    db.execute(
        text("""
        INSERT INTO public.landing_analytics (session_id, evento, valor_extra, ip_hash, ua_hash)
        VALUES (:sid, :ev, :val, :ih, :uh)
    """),
        {
            "sid": req.session_id,
            "ev": req.evento,
            "val": req.valor_extra,
            "ih": _hash(ip),
            "uh": _hash(ua),
        },
    )
    db.commit()
    return {"ok": True}
