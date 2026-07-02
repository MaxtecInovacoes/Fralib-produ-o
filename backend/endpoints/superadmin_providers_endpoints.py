"""Endpoints superadmin para o painel de provedores externos (Sprint 0.1).

GET /api/superadmin/dashboard/providers
    Lista provedores externos com semáforo (healthy/degraded/down/unknown).
    Lê da view v_provider_health_now.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Engine

from backend.core.auth import get_current_user
from backend.core.database import engine as _default_engine
from backend.services.provider_health_service import (
    compute_all_providers,
    view_provider_health_now,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/superadmin/dashboard",
    tags=["superadmin-providers"],
)

# Permite override em testes (monkey-patch `mod.engine`).
engine: Engine = _default_engine


def _require_superadmin(usuario: dict | None) -> None:
    if not usuario:
        raise HTTPException(status_code=401, detail="Autenticação necessária")
    role = (usuario or {}).get("role", "")
    is_su = (usuario or {}).get("is_superadmin", False)
    if role != "superadmin" and not is_su:
        raise HTTPException(status_code=403, detail="Acesso restrito a superadmin")


@router.get("/providers")
async def list_providers(
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Lista provedores externos com status atual.

    Response shape:
        {
          "ok": True,
          "providers": [...],          # lista detalhada (1 dict por provider)
          "by_status": {...},          # contadores
          "providers_total": int,
          "has_risk": bool,
          "stale_count": int,
        }
    """
    _require_superadmin(usuario)

    try:
        summary = compute_all_providers(engine)
        return {
            "ok": True,
            "providers": summary["providers"],
            "by_status": summary["by_status"],
            "providers_total": summary["providers_total"],
            "has_risk": summary["has_risk"],
            "stale_count": summary.get("stale_count", 0),
        }
    except Exception as exc:
        logger.exception("[superadmin_providers] list_providers falhou: %s", exc)
        # Não vaza stack trace: devolve 503 com mensagem curta.
        raise HTTPException(
            status_code=503,
            detail=f"Falha ao consultar provedores: {exc.__class__.__name__}",
        )


@router.get("/providers/{provider}")
async def get_provider(
    provider: str,
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Detalhe de 1 provider (lookup direto na view)."""
    _require_superadmin(usuario)
    rows = view_provider_health_now(engine)
    for row in rows:
        if row.get("provider") == provider:
            return {"ok": True, "provider": row}
    raise HTTPException(status_code=404, detail=f"provider '{provider}' não encontrado")