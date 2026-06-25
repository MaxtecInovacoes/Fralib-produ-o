"""
Microsoft Clarity Data Export API integration.

Puxa dados de heatmap, recordings e insights do Clarity.
Salva no banco proprio pra cruzar com nosso tracking.

Doc: https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-api
"""

import os
import httpx
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel

from backend.core.database import get_db

router = APIRouter(prefix="/api/clarity", tags=["clarity"])
log = logging.getLogger("uvicorn")

CLARITY_PROJECT_ID = "wv8xiy7kvk"
CLARITY_API_BASE = "https://www.clarity.ms/export-data/api/v1"
CLARITY_TOKEN = os.getenv("CLARITY_API_TOKEN", "")


async def clarity_request(endpoint: str, params: dict | None = None) -> dict:
    """Faz request autenticada pra Clarity Data Export API."""
    if not CLARITY_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="CLARITY_API_TOKEN nao configurado no .env",
        )
    headers = {"Authorization": f"Bearer {CLARITY_TOKEN}"}
    url = f"{CLARITY_API_BASE}/{endpoint}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers, params=params or {})
        if r.status_code != 200:
            log.error("Clarity API %s -> %s: %s", endpoint, r.status_code, r.text[:300])
            raise HTTPException(status_code=r.status_code, detail=f"Clarity: {r.text[:200]}")
        return r.json()


@router.get("/info")
async def clarity_info():
    """Info do projeto Clarity."""
    try:
        data = await clarity_request(
            "project-info",
            {"projectId": CLARITY_PROJECT_ID},
        )
        return {"ok": True, "project": data}
    except HTTPException:
        # fallback: retorna o que sabemos hardcoded
        return {
            "ok": True,
            "project": {
                "id": CLARITY_PROJECT_ID,
                "name": "FraLib OS",
                "site": "seunegociofralib.site",
            },
            "note": "Retornado do fallback - API pode estar lenta ou indisponivel",
        }


@router.get("/heatmap")
async def clarity_heatmap(
    days: int = 7,
    device: Optional[str] = None,  # "desktop" | "mobile" | None (ambos)
):
    """Heatmap aggregated data (clicks, scroll, area)."""
    params = {
        "projectId": CLARITY_PROJECT_ID,
        "numOfDays": days,
    }
    if device:
        params["device"] = device
    try:
        data = await clarity_request("heatmap", params)
        return {"ok": True, "days": days, "device": device, "data": data}
    except HTTPException as e:
        return {"ok": False, "error": str(e.detail), "days": days, "device": device}


@router.get("/metrics")
async def clarity_metrics(days: int = 7):
    """Metricas agregadas: sessoes, bounce, scroll depth medio."""
    params = {"projectId": CLARITY_PROJECT_ID, "numOfDays": days}
    try:
        data = await clarity_request("metrics", params)
        return {"ok": True, "days": days, "data": data}
    except HTTPException as e:
        return {"ok": False, "error": str(e.detail), "days": days}


@router.get("/recordings")
async def clarity_recordings(days: int = 7, limit: int = 20):
    """Lista das ultimas gravacoes (session recordings)."""
    params = {
        "projectId": CLARITY_PROJECT_ID,
        "numOfDays": days,
        "limit": limit,
    }
    try:
        data = await clarity_request("recordings", params)
        return {"ok": True, "days": days, "limit": limit, "data": data}
    except HTTPException as e:
        return {"ok": False, "error": str(e.detail), "days": days}


@router.get("/sync")
async def clarity_sync(days: int = 7, db: Session = Depends(get_db)):
    """Sincroniza metricas do Clarity pro nosso banco (landing_analytics)."""
    if not CLARITY_TOKEN:
        raise HTTPException(status_code=503, detail="CLARITY_API_TOKEN nao configurado")

    try:
        metrics = await clarity_request(
            "metrics", {"projectId": CLARITY_PROJECT_ID, "numOfDays": days}
        )
    except HTTPException as e:
        return {"ok": False, "error": str(e.detail)}

    # Salvar snapshot no banco pra historico
    db.execute(
        text("""
        INSERT INTO landing_analytics (session_id, evento, valor_extra, criado_em)
        VALUES (:sid, :ev, :val, NOW())
        ON CONFLICT DO NOTHING
        """),
        {
            "sid": f"clarity_sync_{datetime.utcnow().strftime('%Y%m%d')}",
            "ev": "clarity_sync",
            "val": str(metrics)[:250],
        },
    )
    db.commit()

    return {"ok": True, "synced_at": datetime.utcnow().isoformat(), "metrics": metrics}


@router.get("/dashboard")
async def clarity_dashboard(days: int = 7, db: Session = Depends(get_db)):
    """Dashboard consolidado: Clarity + nosso banco."""
    clarity_data: dict = {}
    try:
        clarity_data = await clarity_request(
            "metrics", {"projectId": CLARITY_PROJECT_ID, "numOfDays": days}
        )
    except HTTPException as e:
        clarity_data = {"error": str(e.detail)}

    # Cruzar com nosso banco
    nosso = db.execute(
        text("""
        SELECT
          DATE(criado_em) as dia,
          COUNT(*) FILTER (WHERE evento = 'view') as views,
          COUNT(*) FILTER (WHERE evento = 'bounce') as bounces,
          COUNT(*) FILTER (WHERE evento LIKE 'click_%') as clicks,
          COUNT(*) FILTER (WHERE evento LIKE 'funnel_%') as funnel_events
        FROM landing_analytics
        WHERE criado_em > NOW() - (:days || ' days')::interval
        GROUP BY DATE(criado_em)
        ORDER BY dia DESC
        """),
        {"days": days},
    ).fetchall()

    return {
        "ok": True,
        "days": days,
        "clarity": clarity_data,
        "nosso_banco": [dict(r._mapping) for r in nosso],
    }