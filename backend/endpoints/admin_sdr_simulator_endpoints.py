"""Endpoints admin (escopados por tenant) para o Simulador do Franz.

Rotas:
  POST /api/admin/simulate        - roda uma simulacao
  GET  /api/admin/simulations     - historico das ultimas N simulacoes

Autenticacao: mesma dos outros /api/admin/* (Depends(get_current_user)).
Nao requer role=superadmin.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.auth import get_current_user
from services.sdr_simulator import list_simulations, simulate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin-sdr-simulator"])


# ── DTOs ────────────────────────────────────────────────────────────────


class HistoryTurn(BaseModel):
    role: str = Field(default="user")
    content: str = Field(default="")


class SimulateRequest(BaseModel):
    tenant_id: int | None = Field(
        default=None,
        description=(
            "Tenant alvo da simulacao. Se omitido, usa o user_id "
            "do token (tenant dono da sessao)."
        ),
    )
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[HistoryTurn] | None = Field(default=None)


class SimulateResponse(BaseModel):
    id: int | None = None
    response: str
    intent: str | None = None
    stage_after: str | None = None
    kanban_action: str | None = None
    rules_applied: list[str] = Field(default_factory=list)
    latency_ms: int = 0
    error: str | None = None


class SimulationHistoryItem(BaseModel):
    id: int
    tenant_id: int
    message: str
    response: str | None = None
    intent: str | None = None
    stage_after: str | None = None
    kanban_action: str | None = None
    rules_applied: list[str] = Field(default_factory=list)
    latency_ms: int | None = None
    criado_em: str | None = None


# ── Helpers ─────────────────────────────────────────────────────────────


def _resolve_user_id(usuario: dict[str, Any]) -> int:
    uid = (usuario or {}).get("user_id") or (usuario or {}).get("id")
    if not uid:
        raise HTTPException(status_code=401, detail="user_id ausente no token")
    return int(uid)


def _history_to_dict(history: list[HistoryTurn] | None) -> list[dict[str, Any]]:
    if not history:
        return []
    out: list[dict[str, Any]] = []
    for turn in history[-20:]:
        out.append(
            {
                "role": (turn.role or "user").lower(),
                "content": (turn.content or "").strip(),
            }
        )
    return [t for t in out if t["content"]]


# ── Rotas ───────────────────────────────────────────────────────────────


@router.post("/simulate", response_model=SimulateResponse)
async def post_simulate(
    payload: SimulateRequest,
    usuario: dict[str, Any] = Depends(get_current_user),
) -> SimulateResponse:
    """Roda uma simulacao do Franz contra o tenant do usuario autenticado."""
    user_id = _resolve_user_id(usuario)
    tenant_id = int(payload.tenant_id) if payload.tenant_id else user_id

    history = _history_to_dict(payload.history)
    try:
        result = simulate(
            tenant_id=tenant_id,
            message=payload.message,
            history=history,
        )
    except Exception as exc:
        logger.exception("[admin_sdr_simulator] simulate falhou: %s", exc)
        raise HTTPException(status_code=500, detail=f"simulate falhou: {exc}") from exc

    return SimulateResponse(
        id=result.get("id"),
        response=result.get("response") or "",
        intent=result.get("intent"),
        stage_after=result.get("stage_after"),
        kanban_action=result.get("kanban_action"),
        rules_applied=result.get("rules_applied") or [],
        latency_ms=int(result.get("latency_ms") or 0),
        error=result.get("error"),
    )


@router.get("/simulations", response_model=list[SimulationHistoryItem])
async def get_simulations(
    limit: int = Query(10, ge=1, le=100),
    usuario: dict[str, Any] = Depends(get_current_user),
) -> list[SimulationHistoryItem]:
    """Historico das ultimas simulacoes do tenant autenticado."""
    user_id = _resolve_user_id(usuario)
    rows = list_simulations(tenant_id=user_id, limit=limit)
    return [
        SimulationHistoryItem(
            id=int(r["id"]),
            tenant_id=int(r["tenant_id"]),
            message=r.get("message") or "",
            response=r.get("response"),
            intent=r.get("intent"),
            stage_after=r.get("stage_after"),
            kanban_action=r.get("kanban_action"),
            rules_applied=r.get("rules_applied") or [],
            latency_ms=r.get("latency_ms"),
            criado_em=r.get("criado_em"),
        )
        for r in rows
    ]


__all__ = ["router"]