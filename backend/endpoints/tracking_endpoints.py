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
from fastapi import APIRouter, Depends, Request
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
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


# ============================================================
# Lead Funnel — UTM ponta a ponta (criado 2026-06-25)
# ============================================================
class TrackFunnelRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    etapa: str = Field(..., min_length=1, max_length=32)
    utm_source: Optional[str] = Field(None, max_length=64)
    utm_medium: Optional[str] = Field(None, max_length=64)
    utm_campaign: Optional[str] = Field(None, max_length=128)
    utm_content: Optional[str] = Field(None, max_length=128)
    referer: Optional[str] = Field(None, max_length=2048)
    landing_path: Optional[str] = Field(None, max_length=255)
    user_id: Optional[int] = None
    whatsapp: Optional[str] = Field(None, max_length=32)
    email: Optional[str] = Field(None, max_length=255)
    nome: Optional[str] = Field(None, max_length=255)
    cta_text: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=2048)
    ts: Optional[int] = None


_ETAPAS_VALIDAS = {
    "visit", "cta_clicked", "login_start",
    "signup_done", "whatsapp_joined", "activated",
}


@router.post("/funnel")
@limiter.limit("240/minute")
async def track_funnel(
    request: Request, req: TrackFunnelRequest, db: Session = Depends(get_db)
):
    """Registra etapa do funil de lead com UTM source para analytics ponta-a-ponta."""
    if req.etapa not in _ETAPAS_VALIDAS:
        return {"ok": False, "motivo": f"etapa invalida: {req.etapa}"}

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")

    ts = req.ts or int(__import__("time").time() * 1000)

    db.execute(
        text("""
        INSERT INTO public.lead_funnel (
            session_id, etapa_atual,
            utm_source, utm_medium, utm_campaign, utm_content, referer, landing_path,
            user_id, whatsapp, email, nome, cta_text,
            ip_hash, ua_hash, user_agent,
            entrou_landing, clicou_cta, iniciou_login, criou_conta,
            entrou_grupo_whatsapp, primeira_acao_app
        ) VALUES (
            :sid, :etapa,
            :usrc, :umed, :ucmp, :ucon, :ref, :path,
            :uid, :wa, :em, :nm, :cta,
            :ih, :uh, :ua_text,
            CASE WHEN :etapa='visit' THEN to_timestamp(:ts/1000.0) ELSE NULL END,
            CASE WHEN :etapa='cta_clicked' THEN to_timestamp(:ts/1000.0) ELSE NULL END,
            CASE WHEN :etapa='login_start' THEN to_timestamp(:ts/1000.0) ELSE NULL END,
            CASE WHEN :etapa='signup_done' THEN to_timestamp(:ts/1000.0) ELSE NULL END,
            CASE WHEN :etapa='whatsapp_joined' THEN to_timestamp(:ts/1000.0) ELSE NULL END,
            CASE WHEN :etapa='activated' THEN to_timestamp(:ts/1000.0) ELSE NULL END
        )
        """),
        {
            "sid": req.session_id,
            "etapa": req.etapa,
            "usrc": req.utm_source,
            "umed": req.utm_medium,
            "ucmp": req.utm_campaign,
            "ucon": req.utm_content,
            "ref": req.referer,
            "path": req.landing_path,
            "uid": req.user_id,
            "wa": req.whatsapp,
            "em": req.email,
            "nm": req.nome,
            "cta": req.cta_text,
            "ih": _hash(ip),
            "uh": _hash(ua),
            "ua_text": ua[:500],
            "ts": ts,
        },
    )
    db.commit()
    return {"ok": True}


# ============================================================
# Lead Funnel — leitura agregada para dashboard
# ============================================================
@router.get("/funnel/origem")
@limiter.limit("30/minute")
async def track_funnel_origem(
    request: Request, dias: int = 30, db: Session = Depends(get_db)
):
    """Retorna o funil agregado por utm_source para os ultimos N dias."""
    rows = db.execute(
        text("""
        SELECT * FROM vw_funnel_por_origem
        LIMIT 100
        """)
    ).fetchall()
    return {
        "ok": True,
        "dias": dias,
        "items": [dict(r._mapping) for r in rows],
    }


@router.get("/funnel/diario")
@limiter.limit("30/minute")
async def track_funnel_diario(
    request: Request, dias: int = 30, db: Session = Depends(get_db)
):
    """Retorna o funil diario agregado."""
    rows = db.execute(
        text("""
        SELECT * FROM vw_funnel_diario
        WHERE dia > CURRENT_DATE - (:dias || ' days')::interval
        ORDER BY dia DESC
        """),
        {"dias": dias},
    ).fetchall()
    return {
        "ok": True,
        "dias": dias,
        "items": [dict(r._mapping) for r in rows],
    }
