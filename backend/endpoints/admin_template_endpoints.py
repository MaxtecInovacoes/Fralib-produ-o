"""Sprint 7 (v1.10) - RAG Templates: admin endpoints.

Exposes three routes that let operators inspect, rebuild, and query the
template embedding index produced by `backend.services.template_embeddings`.

Routes:
  GET  /api/admin/templates/index   - Stats + vectors summary
  POST /api/admin/templates/reindex - Rebuild the index from disk
  GET  /api/admin/templates/match   - Top-k template suggestions for a nicho
"""

from __future__ import annotations

import os
from typing import Any, List

from fastapi import APIRouter, HTTPException, Query, Request

from backend.services import template_embeddings as te

router = APIRouter(prefix="/api/admin/templates", tags=["admin-templates"])


def _require_admin(request: Request) -> None:
    """Mirror the auth pattern used by sibling admin endpoints."""
    user = getattr(request.state, "user", None)
    if not user or not user.get("is_admin"):
        if os.getenv("FRALIB_ENV") == "production":
            raise HTTPException(status_code=403, detail="Acesso restrito a admin")


@router.get("/index")
async def api_templates_index(request: Request) -> dict[str, Any]:
    """Return summary stats + the (truncated) on-disk index."""
    _require_admin(request)
    stats = te.get_template_stats()
    idx = te.get_index()

    # Avoid sending 64 floats per template in a single payload; return a
    # condensed preview and the full dim for validation purposes.
    preview: List[dict[str, Any]] = []
    for name in sorted(idx.keys()):
        vec = idx[name]
        preview.append(
            {
                "template": name,
                "norm": float(sum(v * v for v in vec) ** 0.5),
                "preview": vec[:8],
            }
        )

    return {
        "ok": True,
        "stats": stats,
        "preview": preview,
    }


@router.post("/reindex")
async def api_templates_reindex(request: Request) -> dict[str, Any]:
    """Force a fresh reindex of `backend/templates/*.html`."""
    _require_admin(request)
    idx = te.index_templates()
    return {
        "ok": True,
        "indexed": len(idx),
        "templates": sorted(idx.keys()),
        "path": str(te.INDEX_PATH),
    }


@router.get("/match")
async def api_templates_match(
    request: Request,
    nicho: str = Query(..., min_length=1, max_length=500),
    top_k: int = Query(default=3, ge=1, le=10),
) -> dict[str, Any]:
    """Return the top-k templates matching the supplied nicho/briefing."""
    _require_admin(request)
    results = te.find_best_template(nicho, top_k=top_k)
    return {
        "ok": True,
        "nicho": nicho,
        "top_k": top_k,
        "matches": results,
    }


__all__ = ["router"]