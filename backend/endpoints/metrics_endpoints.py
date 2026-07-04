"""
Metrics Endpoints - Observabilidade do sistema.

Inclui:
- Status do connection pool
- Uso de LLM hoje
- Métricas de leads
- Tamanho da fila de pipeline
"""
from fastapi import APIRouter, Depends, HTTPException
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
from pydantic import BaseModel

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.core.config import is_superadmin


router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def require_metrics_admin(user: dict = Depends(get_current_user)) -> dict:
    if not is_superadmin(user.get("email", "")):
        raise HTTPException(status_code=403, detail="Acesso negado")
    return user


class MetricsResponse(BaseModel):
    timestamp: str
    database: dict
    llm_usage: dict
    leads: dict
    pipeline: dict
    system: dict


def _get_db_pool_status() -> dict:
    """Status do connection pool do banco."""
    try:
        from database import engine
        pool = engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow(),
            "utilization_pct": round(pool.checkedout() / (pool.size() + max(pool.overflow(), 1)) * 100, 1),
        }
    except Exception as e:
        return {"error": str(e)}


def _get_llm_usage_today() -> dict:
    """Uso de LLM hoje."""
    try:
        from database import SessionLocal
        db = SessionLocal()
        try:
            row = db.execute(text("""
                SELECT
                    COUNT(*) as total_calls,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens,
                    COALESCE(SUM(cost_usd), 0) as cost_usd
                FROM llm_budget_ledger
                WHERE DATE(created_at) = CURRENT_DATE
            """)).fetchone()
            return {
                "total_calls": row[0] or 0,
                "input_tokens": row[1] or 0,
                "output_tokens": row[2] or 0,
                "cost_usd": round(float(row[3] or 0), 4),
            }
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


def _get_leads_stats() -> dict:
    """Estatísticas de leads."""
    try:
        from database import SessionLocal
        db = SessionLocal()
        try:
            total = db.execute(text("SELECT COUNT(*) FROM leads")).fetchone()[0] or 0
            with_site = db.execute(text("SELECT COUNT(*) FROM leads WHERE site_url IS NOT NULL AND site_url != ''")).fetchone()[0] or 0
            today = db.execute(text("SELECT COUNT(*) FROM leads WHERE DATE(created_at) = CURRENT_DATE")).fetchone()[0] or 0
            return {
                "total": total,
                "with_site": with_site,
                "created_today": today,
            }
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


def _get_pipeline_stats() -> dict:
    """Estatísticas da fila canônica de jobs."""
    try:
        from database import SessionLocal
        db = SessionLocal()
        try:
            row = db.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'pending') AS queue_size,
                    COUNT(*) FILTER (WHERE status = 'running') AS running,
                    COUNT(*) FILTER (
                        WHERE status = 'failed_permanent'
                          AND DATE(COALESCE(concluido_em, criado_em)) = CURRENT_DATE
                    ) AS failed_today,
                    COUNT(*) FILTER (
                        WHERE status = 'running'
                          AND worker_heartbeat < NOW() - INTERVAL '5 minutes'
                    ) AS stale_running
                FROM jobs
                WHERE tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main',
                               'lead_supply_hunter', 'lead_supply_caio',
                               'lead_production_tick', 'franz_outreach')
            """)).mappings().first()
            return {
                "queue_size": int(row.get("queue_size") or 0),
                "running": int(row.get("running") or 0),
                "failed_today": int(row.get("failed_today") or 0),
                "stale_running": int(row.get("stale_running") or 0),
                "source": "jobs",
            }
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


def _get_system_info() -> dict:
    """Informações do sistema."""
    import psutil

    try:
        process = psutil.Process()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
            "threads": process.num_threads(),
        }
    except Exception:
        return {
            "cpu_percent": "n/a",
            "memory_mb": "n/a",
            "threads": "n/a",
        }


@router.get("", response_model=MetricsResponse)
def get_metrics(
    db: Session = Depends(get_db),
    user: dict = Depends(require_metrics_admin),
):
    """
    Retorna métricas completas do sistema.
    Requer autenticação.
    """
    from datetime import datetime

    return MetricsResponse(
        timestamp=datetime.utcnow().isoformat(),
        database=_get_db_pool_status(),
        llm_usage=_get_llm_usage_today(),
        leads=_get_leads_stats(),
        pipeline=_get_pipeline_stats(),
        system=_get_system_info(),
    )


@router.get("/public")
def get_public_metrics():
    """
    Retorna apenas status público, sem métricas internas ou cross-tenant.
    """
    from datetime import datetime

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "ok",
    }


@router.get("/db-pool")
def get_db_pool_metrics(
    db: Session = Depends(get_db),
    user: dict = Depends(require_metrics_admin),
):
    """Métricas detalhadas do connection pool."""
    return _get_db_pool_status()


@router.get("/llm-usage")
def get_llm_usage_metrics(
    db: Session = Depends(get_db),
    user: dict = Depends(require_metrics_admin),
):
    """Métricas de uso de LLM."""
    return _get_llm_usage_today()
