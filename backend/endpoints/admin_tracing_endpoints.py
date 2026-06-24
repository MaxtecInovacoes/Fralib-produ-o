"""admin_tracing_endpoints.py - Sprint 5 (v1.8).

Endpoints administrativos para visualizar traces dos 4 agentes (Nicho/
Arquiteto/Builder/Validador) + Franz (SDR).

Consome `backend.services.tracing` (JSONL local + opcional LangSmith).

Rotas:
  GET /api/admin/tracing/summary        - Totais agregados (todos agentes)
  GET /api/admin/tracing/recent         - Ultimos N traces (default 50)
  GET /api/admin/tracing/stats          - Stats por agente (query params)
  GET /api/admin/tracing/agents         - Lista agentes conhecidos
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/tracing", tags=["admin-tracing"])

KNOWN_AGENTS = ("nicho", "arquiteto", "builder", "validador", "franz")


def require_admin(request: Request):
    """Verifica que o requester e admin (reutiliza padrao de admin_services_endpoints)."""
    import os
    user = getattr(request.state, "user", None)
    if not user or not user.get("is_admin"):
        if os.getenv("FRALIB_ENV") == "production":
            raise HTTPException(status_code=403, detail="Acesso restrito a admin")
    return user


def _read_traces(days: int = 1, agent: Optional[str] = None) -> list[dict[str, Any]]:
    """Le traces dos ultimos N dias (JSONL append-only)."""
    from backend.services.tracing import TRACES_DIR, TRACING_ENABLED
    if not TRACING_ENABLED:
        return []
    traces: list[dict[str, Any]] = []
    try:
        for day_offset in range(days):
            day = time.strftime(
                "%Y-%m-%d", time.localtime(time.time() - day_offset * 86400)
            )
            path = TRACES_DIR / f"traces_{day}.jsonl"
            if not path.is_file():
                continue
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        t = json.loads(line)
                        if agent and t.get("agent") != agent:
                            continue
                        traces.append(t)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.warning(f"[admin_tracing] read_traces falhou: {e}")
    return traces


@router.get("/summary")
async def api_tracing_summary(
    request: Request,
    days: int = Query(default=1, ge=1, le=30),
) -> dict[str, Any]:
    """Resumo agregado dos traces (todos agentes)."""
    require_admin(request)
    from backend.services.tracing import is_enabled
    if not is_enabled():
        return {
            "enabled": False,
            "hint": "Ative FRALIB_TRACING=1 (local) ou FRALIB_TRACING=2 (LangSmith)",
            "agents": {},
        }
    traces = _read_traces(days=days)
    by_agent: dict[str, dict[str, Any]] = {}
    for t in traces:
        a = t.get("agent", "unknown")
        if a not in by_agent:
            by_agent[a] = {
                "count": 0, "errors": 0,
                "total_latency_ms": 0, "total_cost_usd": 0.0,
                "total_input_tokens": 0, "total_output_tokens": 0,
            }
        s = by_agent[a]
        s["count"] += 1
        if not t.get("success", True):
            s["errors"] += 1
        s["total_latency_ms"] += t.get("latency_ms", 0)
        s["total_cost_usd"] += t.get("cost_usd", 0.0)
        s["total_input_tokens"] += t.get("input_tokens", 0)
        s["total_output_tokens"] += t.get("output_tokens", 0)
    # Calcula medias
    for a, s in by_agent.items():
        if s["count"] > 0:
            s["avg_latency_ms"] = s["total_latency_ms"] // s["count"]
            s["success_rate"] = round(1.0 - (s["errors"] / s["count"]), 4)
        else:
            s["avg_latency_ms"] = 0
            s["success_rate"] = 1.0
    total_cost = round(sum(s["total_cost_usd"] for s in by_agent.values()), 6)
    total_count = sum(s["count"] for s in by_agent.values())
    return {
        "enabled": True,
        "days": days,
        "total_traces": total_count,
        "total_cost_usd": total_cost,
        "agents": by_agent,
    }


@router.get("/recent")
async def api_tracing_recent(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    agent: Optional[str] = Query(default=None),
    days: int = Query(default=1, ge=1, le=7),
) -> dict[str, Any]:
    """Ultimos N traces (ordenados por mais recente)."""
    require_admin(request)
    from backend.services.tracing import is_enabled
    if not is_enabled():
        return {"enabled": False, "traces": [], "hint": "FRALIB_TRACING desabilitado"}
    traces = _read_traces(days=days, agent=agent)
    # Ordena por start_unix desc
    traces.sort(key=lambda t: t.get("start_unix", 0), reverse=True)
    return {
        "enabled": True,
        "count": len(traces[:limit]),
        "total_available": len(traces),
        "agent_filter": agent,
        "days": days,
        "traces": traces[:limit],
    }


@router.get("/stats")
async def api_tracing_stats(
    request: Request,
    agent: Optional[str] = Query(default=None),
    days: int = Query(default=7, ge=1, le=30),
) -> dict[str, Any]:
    """Stats agregadas por agente (ou geral se agent=None)."""
    require_admin(request)
    from backend.services.tracing import get_stats
    stats = get_stats(agent=agent, days=days)
    stats["agent"] = agent
    stats["days"] = days
    return stats


@router.get("/agents")
async def api_tracing_agents(request: Request) -> dict[str, Any]:
    """Lista agentes conhecidos no sistema de tracing."""
    require_admin(request)
    return {
        "agents": list(KNOWN_AGENTS),
        "count": len(KNOWN_AGENTS),
    }
