"""Endpoints do Closer humano.

GET  /api/closer/queue           - Lista pendentes
POST /api/closer/queue/claim     - Reivindica lead
POST /api/closer/queue/done      - Marca como won/lost
GET  /api/closer/queue/stats     - Stats da fila
"""
from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.core.database import engine

router = APIRouter(prefix="/api/closer", tags=["closer"])
log = logging.getLogger("closer-endpoints")


def _tenant_id_from_request(request: Request) -> int:
    """Extrai user_id do tenant do request."""
    auth = request.headers.get("Authorization", "")
    # Simplificado - em produção ler JWT
    tenant = request.headers.get("X-Tenant-Id") or "1"
    try:
        return int(tenant)
    except ValueError:
        raise HTTPException(status_code=400, detail="X-Tenant-Id inválido")


def _ensure_schema() -> None:
    """Cria tabela closer_queue se não existir."""
    from backend.services.closer_queue import ensure_closer_queue_schema
    ensure_closer_queue_schema(engine)


@router.get("/queue")
def list_closer_queue(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Lista leads pendentes na fila do closer (ordenado por score + temperatura)."""
    _ensure_schema()
    user_id = _tenant_id_from_request(request)
    from backend.services.closer_queue import list_pending
    pending = list_pending(engine, user_id=user_id, limit=limit)
    return {
        "tenant_id": user_id,
        "count": len(pending),
        "leads": pending,
    }


class ClaimRequest(BaseModel):
    queue_id: int
    claimed_by: str = Field(..., description="Identificador do closer (email/nome)")


class DoneRequest(BaseModel):
    queue_id: int
    won: bool = False
    closer_notes: str = ""


@router.post("/queue/claim")
def claim_closer_queue(req: ClaimRequest, request: Request) -> dict[str, Any]:
    """Closer reivindica um lead. Marca como claimed e retorna contexto."""
    _ensure_schema()
    user_id = _tenant_id_from_request(request)
    from backend.services.closer_queue import claim
    success = claim(
        engine,
        queue_id=req.queue_id,
        claimed_by=req.claimed_by,
        user_id=user_id,
    )
    if not success:
        raise HTTPException(status_code=409, detail="Lead já reivindicado ou não encontrado")
    log.info(f"[CLOSER] Tenant {user_id}: lead {req.queue_id} claimed por {req.claimed_by}")
    return {"ok": True, "queue_id": req.queue_id, "claimed_by": req.claimed_by}


@router.post("/queue/done")
def complete_closer_queue(req: DoneRequest, request: Request) -> dict[str, Any]:
    """Closer marca lead como won ou lost."""
    _ensure_schema()
    user_id = _tenant_id_from_request(request)
    from backend.services.closer_queue import complete
    success = complete(
        engine,
        queue_id=req.queue_id,
        user_id=user_id,
        closer_notes=req.closer_notes,
        won=req.won,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Lead não encontrado na fila")
    log.info(
        f"[CLOSER] Tenant {user_id}: lead {req.queue_id} "
        f"{'won' if req.won else 'lost'} (notas={len(req.closer_notes)} chars)"
    )
    return {"ok": True, "queue_id": req.queue_id, "final_status": "won" if req.won else "lost"}


@router.get("/queue/stats")
def closer_queue_stats(request: Request, days: int = Query(30, ge=1, le=365)) -> dict[str, Any]:
    """Estatísticas da fila do closer."""
    _ensure_schema()
    user_id = _tenant_id_from_request(request)
    from backend.services.closer_queue import get_stats
    return get_stats(engine, user_id=user_id, days=days)
