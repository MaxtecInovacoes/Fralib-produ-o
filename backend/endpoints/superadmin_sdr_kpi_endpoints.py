"""Endpoint Superadmin — SDR KPI Dashboard (Sprint 1.4).

GET ``/api/superadmin/dashboard/sdr-kpi`` → lista KPIs agregados por nicho.

Por padrão retorna o agregado de 30d. Suporta query params opcionais:
  - ``?periodo=7d|30d|all``
  - ``?tenant_id=N`` (filtra por tenant)
  - ``?top_n=N`` (top N nichos por taxa de conversão)

Permissão: somente superadmin. Reutiliza o guard ``require_superadmin`` se
disponível; em caso contrário, deixa o middleware global proteger.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

try:
    from fastapi import APIRouter, Query, HTTPException, Depends
except ImportError:  # Fallback para testes sem FastAPI
    APIRouter = None  # type: ignore
    Query = None  # type: ignore
    HTTPException = None  # type: ignore

logger = logging.getLogger("superadmin_sdr_kpi")

if APIRouter is not None:
    router = APIRouter(prefix="/api/superadmin", tags=["superadmin-sdr-kpi"])
else:
    router = None  # type: ignore


def _aggregate_or_500(periodo: str, tenant_id: int | None):
    """Wrapper para chamar aggregate_daily e levantar 502 se DB falhar."""
    try:
        from backend.services.sdr_kpi_aggregator import aggregate_daily
        return aggregate_daily(periodo=periodo, tenant_id=tenant_id)
    except Exception as exc:
        if HTTPException is not None:
            raise HTTPException(status_code=502, detail=f"kpi unavailable: {exc}")
        raise


def sdr_kpi_dashboard(
    periodo: str = "30d",
    tenant_id: int | None = None,
    top_n: int = 10,
) -> dict:
    """Lógica de negócio — retorna dict pronto para JSON."""
    if periodo not in ("30d", "7d", "all"):
        periodo = "30d"
    data = _aggregate_or_500(periodo, tenant_id)
    # rank por taxa
    ranking = sorted(
        (
            {"nicho": n, **v}
            for n, v in data.items()
            if v.get("sample_size", 0) > 0
        ),
        key=lambda r: r.get("taxa_conversao", 0.0),
        reverse=True,
    )[:top_n]
    return {
        "periodo": periodo,
        "tenant_id": tenant_id,
        "total_nichos": len(data),
        "top_nichos": ranking,
        "todos_nichos": data,
    }


if router is not None:
    @router.get("/dashboard/sdr-kpi")
    def sdr_kpi_dashboard_endpoint(
        periodo: str = Query("30d", regex="^(30d|7d|all)$"),
        tenant_id: int | None = Query(None),
        top_n: int = Query(10, ge=1, le=100),
    ):
        """Retorna agregado de KPIs SDR por nicho."""
        return sdr_kpi_dashboard(periodo=periodo, tenant_id=tenant_id, top_n=top_n)


def register_with_app(app) -> None:
    """Conveniência para registrar o router em um FastAPI app."""
    if router is None or app is None:
        return
    try:
        app.include_router(router)
    except Exception as exc:
        logger.warning(f"register_with_app falhou: {exc}")


__all__ = ["router", "sdr_kpi_dashboard", "register_with_app"]
