"""admin_prompts_endpoints.py - Sprint 8 (v1.11) - Gestao de prompt versions.

Endpoints administrativos para gerenciar as versoes v2/v3 dos system prompts
dos 4 agentes (nicho / arquiteto / builder / validador) geradas pelo servico
`auto_improve.py`.

Rotas:
  GET  /api/admin/prompts/versions    - Lista versoes persistidas de um agente
  POST /api/admin/prompts/analyze     - Roda analyze_traces (gera sugestoes)
  POST /api/admin/prompts/apply       - Ativa uma versao persistida (v1/v2/...)
  GET  /api/admin/prompts/current     - Retorna o prompt ativo

Reuso explicito:
    - `backend.services.auto_improve.analyze_traces`
    - `backend.services.auto_improve.suggest_prompt_improvements`
    - `backend.services.auto_improve.evolve_prompt`
    - `backend.services.auto_improve.persist_prompt_version`
    - `backend.services.auto_improve.get_best_prompt`
    - `backend.services.auto_improve.should_apply_v2`
    - `backend.services.auto_improve.list_versions / get_active_prompt /
      get_active_version / set_active_version`
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/prompts", tags=["admin-prompts"])

# Diretorio onde estao os system prompts canonicos (v1) dos 4 agentes
AGENTS_DIR = Path(
    os.getenv("FRALIB_AGENTS_DIR", "backend/agents")
)

# Agentes suportados (espelha auto_improve.SUPPORTED_AGENTS)
SUPPORTED_AGENTS: tuple[str, ...] = ("nicho", "arquiteto", "builder", "validador")


def require_admin(request: Request) -> Optional[dict]:
    """Verifica que o requester e admin (mesmo padrao de admin_tracing)."""
    user = getattr(request.state, "user", None)
    if not user or not user.get("is_admin"):
        if os.getenv("FRALIB_ENV") == "production":
            raise HTTPException(status_code=403, detail="Acesso restrito a admin")
    return user


def _read_canonical_prompt(agent: str) -> str:
    """Le o system prompt canonico (v1) do agente a partir de <agent>.py.

    Procura por um bloco `SYSTEM_PROMPT = \"\"\"...\"\"\"` no topo do arquivo.
    NUNCA modifica o arquivo — apenas leitura.
    """
    import re

    path = AGENTS_DIR / f"{agent}.py"
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return ""
    # Captura o primeiro `SYSTEM_PROMPT = """..."""` (triple-quoted)
    m = re.search(r'SYSTEM_PROMPT\s*=\s*(?:r)?"""(.*?)"""', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"SYSTEM_PROMPT\s*=\s*(?:r)?'''(.*?)'''", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


# ════════════════════════════════════════════════════════════════════
# ROTAS
# ════════════════════════════════════════════════════════════════════

@router.get("/versions")
async def api_prompts_versions(
    request: Request,
    agent: str = Query(..., description="nicho|arquiteto|builder|validador"),
) -> dict[str, Any]:
    """Lista versoes persistidas (v2/v3/...) do agente."""
    require_admin(request)
    if agent not in SUPPORTED_AGENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Agente '{agent}' nao suportado. Suportados: {list(SUPPORTED_AGENTS)}",
        )

    from backend.services.auto_improve import (
        list_versions, get_active_version, get_best_prompt,
    )

    versions = list_versions(agent)
    active = get_active_version(agent)
    best = get_best_prompt(agent)

    return {
        "agent": agent,
        "active_version": active,
        "has_best_prompt": bool(best),
        "best_prompt_length": len(best) if best else 0,
        "versions": versions,
    }


@router.post("/analyze")
async def api_prompts_analyze(
    request: Request,
    days: int = Query(default=7, ge=1, le=30),
    persist: bool = Query(
        default=False,
        description="Se True, persiste v2 em backend/agents/_prompts_v2/",
    ),
) -> dict[str, Any]:
    """Roda analyze_traces + suggest_prompt_improvements para todos os 4 agentes.

    Args:
        days: janela de analise.
        persist: se True, gera v2 e persiste (default False para seguranca).
    """
    require_admin(request)

    from backend.services.auto_improve import (
        analyze_traces, suggest_prompt_improvements, evolve_prompt,
        persist_prompt_version, should_apply_v2,
    )

    analysis = analyze_traces(days=days)
    suggestions_by_agent: dict[str, list[str]] = {}
    v2_preview: dict[str, str] = {}

    for agent in SUPPORTED_AGENTS:
        sug = suggest_prompt_improvements(agent)
        suggestions_by_agent[agent] = sug

        if persist and analysis["agents"][agent].get("reliable"):
            canonical = _read_canonical_prompt(agent)
            v2 = evolve_prompt(agent, canonical, sug)
            v2_preview[agent] = v2[:200] + "..." if len(v2) > 200 else v2

            # Persiste (mas NAO ativa — activate eh decisao humana)
            persist_prompt_version(agent, "v2", v2)

    return {
        "days": days,
        "persisted": persist,
        "analysis": analysis,
        "suggestions": suggestions_by_agent,
        "v2_preview": v2_preview if persist else {},
        "should_apply": {
            agent: should_apply_v2(agent) for agent in SUPPORTED_AGENTS
        },
    }


@router.post("/apply")
async def api_prompts_apply(
    request: Request,
    agent: str = Query(..., description="nicho|arquiteto|builder|validador"),
    version: str = Query(..., description="v1 (reverte) ou v2/v3/... (ativa)"),
) -> dict[str, Any]:
    """Ativa uma versao persistida (gate should_apply_v2 respeitado para v2)."""
    require_admin(request)
    if agent not in SUPPORTED_AGENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Agente '{agent}' nao suportado.",
        )

    from backend.services.auto_improve import (
        set_active_version, should_apply_v2,
    )

    # Gate conservador para v2 (v1 = rollback livre)
    if version == "v2" and not should_apply_v2(agent):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Gate should_apply_v2 BLOQUEADO para '{agent}'. "
                "Precisa min_samples=10 E delta>5%. "
                "Considere manter v1 ativa."
            ),
        )

    ok = set_active_version(agent, version)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail=f"Versao '{version}' nao existe para o agente '{agent}'.",
        )

    return {
        "agent": agent,
        "active_version": version,
        "applied": True,
    }


@router.get("/current")
async def api_prompts_current(
    request: Request,
    agent: str = Query(..., description="nicho|arquiteto|builder|validador"),
) -> dict[str, Any]:
    """Retorna o prompt ativo (v1 canonico se nenhuma v2 aplicada)."""
    require_admin(request)
    if agent not in SUPPORTED_AGENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Agente '{agent}' nao suportado.",
        )

    from backend.services.auto_improve import (
        get_active_version, get_active_prompt,
    )

    active = get_active_version(agent)
    if active == "v1":
        prompt = _read_canonical_prompt(agent)
    else:
        prompt = get_active_prompt(agent)

    return {
        "agent": agent,
        "active_version": active,
        "prompt": prompt,
        "prompt_length": len(prompt) if prompt else 0,
    }
