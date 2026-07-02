"""Endpoints superadmin para dashboard de custos (Sprint 0.3).

GET /api/superadmin/dashboard/cost-events?days=30&tenant_id=...
    Breakdown de custo unificado multi-provider.
GET /api/superadmin/dashboard/cost-events/top-tenants?days=30&limit=10
    Top tenants por custo BRL.
GET /api/superadmin/dashboard/cost-events/budget-alerts?days=30&threshold_pct=80
    Alertas de orçamento mensal.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Engine

from backend.core.auth import get_current_user
from backend.core.database import engine as _default_engine
from backend.agents import cost_tracker as _cost_tracker

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/superadmin/dashboard",
    tags=["superadmin-costs"],
)

# Override em testes (monkey-patch `mod.engine`).
engine: Engine = _default_engine


def _require_superadmin(usuario: dict | None) -> None:
    if not usuario:
        raise HTTPException(status_code=401, detail="Autenticação necessária")
    role = (usuario or {}).get("role", "")
    is_su = (usuario or {}).get("is_superadmin", False)
    if role != "superadmin" and not is_su:
        raise HTTPException(status_code=403, detail="Acesso restrito a superadmin")


@router.get("/cost-events")
async def list_cost_events(
    days: int = Query(30, ge=1, le=365),
    tenant_id: int | None = Query(None),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Breakdown de custos por provider nos últimos N dias (opcionalmente por tenant)."""
    _require_superadmin(usuario)
    try:
        breakdown = _cost_tracker.costs_breakdown(
            engine, days=days, tenant_id=tenant_id
        )
        total_brl = sum(float(p.get("total_brl", 0) or 0) for p in breakdown)
        total_usd = sum(float(p.get("total_usd", 0) or 0) for p in breakdown)
        return {
            "ok": True,
            "days": days,
            "tenant_id": tenant_id,
            "breakdown": breakdown,
            "total_brl": round(total_brl, 4),
            "total_usd": round(total_usd, 6),
            "providers_total": len(breakdown),
        }
    except Exception as exc:
        logger.exception("[superadmin_costs] list_cost_events falhou: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Falha ao consultar custos: {exc.__class__.__name__}",
        )


@router.get("/cost-events/top-tenants")
async def list_top_tenants(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=100),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Top tenants por custo BRL nos últimos N dias."""
    _require_superadmin(usuario)
    try:
        rows = _cost_tracker.top_tenants_by_cost(engine, days=days, limit=limit)
        return {"ok": True, "days": days, "limit": limit, "tenants": rows}
    except Exception as exc:
        logger.exception("[superadmin_costs] list_top_tenants falhou: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Falha ao consultar top tenants: {exc.__class__.__name__}",
        )


@router.get("/cost-events/budget-alerts")
async def list_budget_alerts(
    days: int = Query(30, ge=1, le=365),
    threshold_pct: float = Query(80.0, ge=0.0, le=1000.0),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Alertas de orçamento: providers com custo >= threshold% do budget mensal."""
    _require_superadmin(usuario)
    try:
        alerts = _cost_tracker.check_budget_alerts(
            engine, days=days, threshold_pct=threshold_pct
        )
        return {
            "ok": True,
            "days": days,
            "threshold_pct": threshold_pct,
            "alerts": alerts,
            "alerts_total": len(alerts),
        }
    except Exception as exc:
        logger.exception("[superadmin_costs] list_budget_alerts falhou: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Falha ao consultar alertas: {exc.__class__.__name__}",
        )
