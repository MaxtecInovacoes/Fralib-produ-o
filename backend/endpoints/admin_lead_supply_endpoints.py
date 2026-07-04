"""
Admin Endpoints - Lead Supply Diagnóstico

Endpoints para administradores verificarem o status do Lead Supply.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
from backend.core.auth import get_current_user, require_admin
from backend.core.database import get_db

logger = logging.getLogger("fralib.admin_lead_supply")

router = APIRouter(prefix="/api/admin/lead-supply", tags=["admin-lead-supply"])


def _require_admin(usuario: dict) -> dict:
    """Verifica se o usuário é admin."""
    if not usuario.get("is_admin") and not usuario.get("email", "").endswith("@seunegociofralib.site"):
        raise HTTPException(403, "Apenas administradores podem acessar")
    return usuario


@router.get("/health")
async def get_lead_supply_health(
    db: Session = Depends(get_db),
    usuario: dict = Depends(_require_admin),
):
    """
    Diagnóstico completo de saúde do Lead Supply.

    Retorna:
    - Status dos scrapers (GOSOM, Playwright)
    - Atividade recente (eventos por hora)
    - Totais por status de leads
    - Tenants com problemas potenciais
    """
    from backend.services.lead_supply_watchdog import (
        check_gosom_availability,
        diagnose_all_tenants,
    )

    # Verifica scrapers
    gosom_ok, gosom_status = await check_gosom_availability()

    # Tenta Playwright
    playwright_ok = False
    playwright_error = None
    try:
        from backend.utils.google_local_scraper import GoogleLocalScraper
        playwright_ok = True
    except Exception as e:
        playwright_error = str(e)

    # Diagnóstico completo dos tenants
    diagnostico = diagnose_all_tenants(db)

    # Determina saúde geral
    gosom_healthy = gosom_ok
    playwright_healthy = playwright_ok
    hunter_active = diagnostico.get("events_24h", {}).get("hunter", 0) > 0
    caio_active = diagnostico.get("events_24h", {}).get("caio", 0) > 0

    if gosom_healthy and playwright_healthy and hunter_active and caio_active:
        health = "good"
    elif gosom_healthy and hunter_active:
        health = "ok"
    elif hunter_active or caio_active:
        health = "degraded"
    else:
        health = "critical"

    return {
        "health": health,
        "scrapers": {
            "gosom": {
                "available": gosom_ok,
                "status": gosom_status,
                "endpoint": "http://localhost:8085",
            },
            "playwright": {
                "available": playwright_ok,
                "error": playwright_error,
            },
        },
        "activity_24h": diagnostico.get("events_24h", {}),
        "totals": diagnostico.get("totals", {}),
        "tenants": diagnostico.get("tenants", []),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/events")
async def get_lead_supply_events(
    limit: int = 50,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario: dict = Depends(_require_admin),
):
    """
    Lista eventos recentes do Lead Supply.

    Params:
    - limit: número de eventos (default 50)
    - source: filtrar por source (hunter, caio, config, etc)
    """
    query = """
        SELECT
            e.id,
            e.tenant_id,
            e.source,
            e.level,
            e.message,
            e.payload,
            e.criado_em
        FROM lead_supply_events e
    """
    params = {"limit": limit}

    if source:
        query += " WHERE e.source = :source"
        params["source"] = source

    query += " ORDER BY e.criado_em DESC LIMIT :limit"

    rows = db.execute(text(query), params).fetchall()

    events = []
    for r in rows:
        payload = r[6] if isinstance(r[6], dict) else json.loads(r[6] or "{}")
        events.append({
            "id": r[0],
            "tenant_id": r[1],
            "source": r[2],
            "level": r[3],
            "message": r[4],
            "payload": payload,
            "criado_em": r[7].isoformat() if r[7] else None,
        })

    return {"events": events, "count": len(events)}


@router.get("/inventory")
async def get_lead_supply_inventory(
    status: Optional[str] = None,
    tenant_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    usuario: dict = Depends(_require_admin),
):
    """
    Lista leads no inventário.

    Params:
    - status: filtrar por status (raw, qualifying, approved, discarded)
    - tenant_id: filtrar por tenant
    - limit: número de leads (default 100)
    """
    query = """
        SELECT
            id,
            tenant_id,
            origem,
            segmento,
            cidade,
            nome,
            status,
            score_caio,
            tier,
            caio_motivo,
            erro,
            attempts,
            criado_em,
            atualizado_em
        FROM lead_inventory
        WHERE 1=1
    """
    params: dict = {"limit": limit}

    if status:
        query += " AND status = :status"
        params["status"] = status

    if tenant_id:
        query += " AND tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id

    query += " ORDER BY criado_em DESC LIMIT :limit"

    rows = db.execute(text(query), params).fetchall()

    leads = []
    for r in rows:
        leads.append({
            "id": r[0],
            "tenant_id": r[1],
            "origem": r[2],
            "segmento": r[3],
            "cidade": r[4],
            "nome": r[5],
            "status": r[6],
            "score_caio": r[7],
            "tier": r[8],
            "caio_motivo": r[9],
            "erro": r[10],
            "attempts": r[11],
            "criado_em": r[12].isoformat() if r[12] else None,
            "atualizado_em": r[13].isoformat() if r[13] else None,
        })

    return {"leads": leads, "count": len(leads)}


@router.post("/diagnose")
async def run_diagnose(
    db: Session = Depends(get_db),
    usuario: dict = Depends(_require_admin),
):
    """
    Executa diagnóstico completo e retorna alertas potenciais.

    Same as /health mas força re-verificação dos scrapers.
    """
    from backend.services.lead_supply_watchdog import run_lead_supply_health_check

    alerts = await run_lead_supply_health_check()

    return {
        "alerts": [a.to_dict() for a in alerts],
        "alert_count": len(alerts),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/jobs")
async def get_lead_supply_jobs(
    db: Session = Depends(get_db),
    usuario: dict = Depends(_require_admin),
):
    """
    Lista jobs pendentes/executando do Lead Supply.
    """
    rows = db.execute(
        text("""
            SELECT
                id,
                tenant_id,
                tipo,
                status,
                payload,
                criado_em,
                atualizado_em
            FROM jobs
            WHERE tipo IN ('lead_supply_hunter', 'lead_supply_caio', 'lead_production_tick')
            ORDER BY criado_em DESC
            LIMIT 100
        """)
    ).fetchall()

    jobs = []
    for r in rows:
        payload = r[5] if isinstance(r[5], dict) else json.loads(r[5] or "{}")
        jobs.append({
            "id": r[0],
            "tenant_id": r[1],
            "tipo": r[2],
            "status": r[3],
            "payload": payload,
            "criado_em": r[4].isoformat() if r[4] else None,
            "atualizado_em": r[6].isoformat() if r[6] else None,
        })

    return {"jobs": jobs, "count": len(jobs)}
