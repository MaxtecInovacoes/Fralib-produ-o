"""franz_insights_endpoints.py — CRUD de insights do Franz (SDR learning).

Endpoints:
  GET  /api/franz/insights             — lista insights (filtro opcional por status/tenant)
  POST  /api/franz/insights/{id}/promote — promove hipótese → validada
  DELETE /api/franz/insights/{id}       — descarta insight
  POST  /api/franz/insights             — cria insight (interno: Franz agent loop)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/franz", tags=["franz-insights"])


# ─── Schemas ──────────────────────────────────────────────────────────

class InsightCreate(BaseModel):
    hypothesis: str
    axis: str = "general"
    confidence: float = 0.5
    tenant_id: Optional[int] = None
    source: str = "agent_loop"


class InsightPromote(BaseModel):
    confidence: float = 0.9


# ─── Helpers ──────────────────────────────────────────────────────────

def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat()


def _tenant_filter(usuario: dict, tenant_override: Optional[int] = None) -> int:
    return tenant_override if tenant_override is not None else usuario.get("tenant_id", usuario["id"])


def _row_to_insight(r) -> dict:
    """Converte row do banco para dict do frontend."""
    return {
        "id": r.id,
        "hypothesis": r.hypothesis,
        "axis": r.axis,
        "confidence": float(r.confidence or 0),
        "validation_status": r.validation_status,
        "tenant_id": r.tenant_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "promoted_at": r.promoted_at.isoformat() if r.promoted_at else None,
        "source": r.source,
    }


# ─── Endpoints ────────────────────────────────────────────────────────

@router.get('/insights')
async def list_insights(
    status: Optional[str] = Query(None, description="Filtro: hypothesis|validated|promoted|discarded"),
    tenant_id: Optional[int] = Query(None, description="Tenant override (superadmin)"),
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Lista insights do Franz. Filtra por tenant do usuário logado."""
    tid = _tenant_filter(usuario, tenant_id)
    try:
        sql = """
            SELECT id, hypothesis, axis, confidence, validation_status,
                   tenant_id, created_at, promoted_at, source
            FROM franz_insights
            WHERE tenant_id = :tid
        """
        params = {"tid": tid}
        if status:
            sql += " AND validation_status = :st"
            params["st"] = status
        sql += " ORDER BY created_at DESC LIMIT 200"

        rows = db.execute(text(sql), params).fetchall()
        return {"items": [_row_to_insight(r) for r in rows]}
    except Exception as e:
        print(f"[FranzInsights] Erro list: {e}")
        return {"items": []}


@router.get('/insights/{insight_id}')
async def get_insight(
    insight_id: int,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Detalhe de um insight."""
    tid = _tenant_filter(usuario)
    row = db.execute(text("""
        SELECT id, hypothesis, axis, confidence, validation_status,
               tenant_id, created_at, promoted_at, source
        FROM franz_insights
        WHERE id = :iid AND tenant_id = :tid
    """), {"iid": insight_id, "tid": tid}).fetchone()
    if not row:
        raise HTTPException(404, "Insight não encontrado")
    return _row_to_insight(row)


@router.post('/insights')
async def create_insight(
    body: InsightCreate,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Cria um novo insight (chamado internamente pelo Franz agent loop)."""
    tid = body.tenant_id or _tenant_filter(usuario)
    try:
        row = db.execute(text("""
            INSERT INTO franz_insights
                (hypothesis, axis, confidence, validation_status, tenant_id, source, created_at)
            VALUES (:hyp, :ax, :conf, 'hypothesis', :tid, :src, :now)
            RETURNING id
        """), {
            "hyp": body.hypothesis[:500],
            "ax": body.axis[:50],
            "conf": max(0.0, min(1.0, float(body.confidence or 0.5))),
            "tid": tid,
            "src": body.source[:50],
            "now": _now(),
        }).fetchone()
        db.commit()
        return {"id": row.id, "status": "created"}
    except Exception as e:
        db.rollback()
        print(f"[FranzInsights] Erro create: {e}")
        raise HTTPException(500, "Falha ao criar insight")


@router.post('/insights/{insight_id}/promote')
async def promote_insight(
    insight_id: int,
    body: Optional[InsightPromote] = None,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Promove um insight de hypothesis → validated/promoted."""
    tid = _tenant_filter(usuario)
    conf = (body.confidence if body else 0.9) if body else 0.9
    try:
        row = db.execute(text("""
            UPDATE franz_insights
            SET validation_status = 'promoted',
                confidence = :conf,
                promoted_at = :now
            WHERE id = :iid AND tenant_id = :tid AND validation_status = 'hypothesis'
            RETURNING id
        """), {"conf": conf, "now": _now(), "iid": insight_id, "tid": tid}).fetchone()
        db.commit()
        if not row:
            raise HTTPException(404, "Insight não encontrado ou já promovido")
        return {"id": insight_id, "status": "promoted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[FranzInsights] Erro promote: {e}")
        raise HTTPException(500, "Falha ao promover insight")


@router.delete('/insights/{insight_id}')
async def discard_insight(
    insight_id: int,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Descarta (soft-delete) um insight → validation_status = 'discarded'."""
    tid = _tenant_filter(usuario)
    try:
        row = db.execute(text("""
            UPDATE franz_insights
            SET validation_status = 'discarded'
            WHERE id = :iid AND tenant_id = :tid
              AND validation_status NOT IN ('promoted', 'discarded')
            RETURNING id
        """), {"iid": insight_id, "tid": tid}).fetchone()
        db.commit()
        if not row:
            raise HTTPException(404, "Insight não encontrado ou já descartado/promovido")
        return {"id": insight_id, "status": "discarded"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[FranzInsights] Erro discard: {e}")
        raise HTTPException(500, "Falha ao descartar insight")
