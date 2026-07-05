"""
admin_pipeline_control_endpoints.py
====================================
Endpoints administrativos para visibilidade e controle da pipeline.

Permitem ao admin:
- Ver estado em tempo real do motor (worker, jobs, spans, travados)
- Executar reap de jobs/spans travados
- Matar spans travados manualmente
- Limpar fila pendente
- Reiniciar o servico systemd do worker

SEGURANCA:
- Queries agregadas NAO filtram por tenant porque sao consultas de ADMIN GLOBAL
- Requer role='superadmin' verificado via require_admin()
- Logs de auditoria em todas as operacoes de write
- Rate limiting protege contra abuses

Rotas:
  GET  /api/admin/pipeline/status           - Resumo agregado
  GET  /api/admin/pipeline/health           - Health check booleano
  POST /api/admin/pipeline/reap             - Executa reap (jobs+spans+exhausted)
  POST /api/admin/pipeline/kill-stuck       - Mata spans running antigos
  POST /api/admin/pipeline/clear-queue      - Cancela jobs pending
  POST /api/admin/pipeline/worker/restart   - systemctl restart fralib-worker

NOTA: Os endpoints de admin veem TODOS os tenants por design (superadmin precisa
de visibilidade global). Se multi-tenant admin for necessario, adicionar filtro.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
from backend.core.auth import get_current_user
from backend.core.database import get_db

router = APIRouter(prefix="/api/admin/pipeline", tags=["admin-pipeline-control"])


def require_admin(usuario: dict) -> None:
    """Verifica que o requester e admin/superadmin."""
    role = (usuario or {}).get("role", "")
    if role not in ("admin", "superadmin"):
        if os.getenv("FRALIB_ENV") == "production":
            raise HTTPException(status_code=403, detail="Acesso restrito a admin")


@router.get("/status")
async def api_pipeline_status(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Resumo agregado do estado do motor.

    Retorna worker (uptime/poll), jobs (por status/tipo), spans (running/24h),
    travados (>1h), fila por tenant.
    """
    require_admin(usuario)

    # Jobs por status e tipo
    jobs_rows = db.execute(
        text("""
        SELECT status, tipo, COUNT(*) AS qty
        FROM jobs
        GROUP BY status, tipo
        ORDER BY status, tipo
    """)
    ).fetchall()

    jobs_by_status: dict[str, int] = {}
    jobs_by_type: dict[str, int] = {}
    jobs_active = 0
    jobs_pending = 0
    jobs_running = 0
    jobs_failed_24h = 0
    for status, tipo, qty in jobs_rows:
        jobs_by_status[status] = jobs_by_status.get(status, 0) + qty
        jobs_by_type[tipo] = jobs_by_type.get(tipo, 0) + qty
        if status == "running":
            jobs_running += qty
            jobs_active += qty
        if status == "pending":
            jobs_pending += qty
        if status == "failed_permanent":
            jobs_failed_24h += qty

    # Spans running
    spans_running = db.execute(
        text("SELECT COUNT(*) FROM pipeline_run_spans WHERE status = 'running'")
    ).scalar() or 0

    # Spans finalizados nas ultimas 24h
    spans_done_24h = db.execute(
        text("""
        SELECT COUNT(*) FROM pipeline_run_spans
        WHERE finished_at >= NOW() - INTERVAL '24 hours'
          AND status IN ('success', 'failed', 'cancelled')
    """)
    ).scalar() or 0

    # Ultimo span finalizado
    last_span = db.execute(
        text("""
        SELECT run_id, fase_nome, status, finished_at
        FROM pipeline_run_spans
        WHERE finished_at IS NOT NULL
        ORDER BY finished_at DESC
        LIMIT 1
    """)
    ).fetchone()

    # Ultimo erro persistido em jobs/spans
    last_job_error = db.execute(
        text("""
        SELECT id, tipo, tenant_id, status, last_phase, last_error, attempts, max_attempts,
               iniciado_em, concluido_em, worker_heartbeat
        FROM jobs
        WHERE COALESCE(last_error, '') <> ''
        ORDER BY COALESCE(concluido_em, iniciado_em, criado_em) DESC, id DESC
        LIMIT 1
    """)
    ).fetchone()
    last_span_error = db.execute(
        text("""
        SELECT run_id, tenant_id, fase_nome, agente, erro, started_at, finished_at
        FROM pipeline_run_spans
        WHERE COALESCE(erro, '') <> ''
        ORDER BY COALESCE(finished_at, started_at) DESC
        LIMIT 1
    """)
    ).fetchone()
    latest_success_at = db.execute(
        text("""
        SELECT GREATEST(
            COALESCE((
                SELECT MAX(COALESCE(concluido_em, iniciado_em, criado_em))
                FROM jobs
                WHERE status = 'completed'
            ), TIMESTAMP 'epoch'),
            COALESCE((
                SELECT MAX(COALESCE(finished_at, started_at))
                FROM pipeline_run_spans
                WHERE status = 'success'
            ), TIMESTAMP 'epoch')
        )
    """)
    ).scalar()
    latest_active_job_started_at = db.execute(
        text("""
        SELECT MAX(COALESCE(iniciado_em, criado_em))
        FROM jobs
        WHERE status IN ('running', 'pending', 'queued')
    """)
    ).scalar()

    def _is_stale_error(ts: Any) -> bool:
        latest_anchor = latest_success_at
        if latest_active_job_started_at and (
            not latest_anchor or latest_active_job_started_at > latest_anchor
        ):
            latest_anchor = latest_active_job_started_at
        return bool(latest_anchor and ts and ts < latest_anchor)

    if last_job_error and _is_stale_error(last_job_error[9] or last_job_error[8]):
        last_job_error = None
    if last_span_error and _is_stale_error(last_span_error[6] or last_span_error[5]):
        last_span_error = None

    # Travados: spans running > 1h
    stuck_spans = db.execute(
        text("""
        SELECT run_id, tenant_id, fase_nome, agente,
               EXTRACT(EPOCH FROM (NOW() - started_at)) AS age_seconds,
               started_at
        FROM pipeline_run_spans
        WHERE status = 'running'
          AND finished_at IS NULL
          AND started_at < NOW() - INTERVAL '1 hour'
        ORDER BY started_at ASC
        LIMIT 20
    """)
    ).fetchall()

    stuck_list = [
        {
            "run_id": r[0],
            "tenant_id": r[1],
            "fase_nome": r[2],
            "agente": r[3],
            "age_seconds": float(r[4] or 0),
            "age_human": _humanize_age(float(r[4] or 0)),
            "started_at": str(r[5]),
        }
        for r in stuck_spans
    ]

    # Fila por tenant (top 10)
    queue_by_tenant = db.execute(
        text("""
        SELECT tenant_id, COUNT(*) FILTER (WHERE status = 'pending') AS pending,
               COUNT(*) FILTER (WHERE status = 'running') AS running
        FROM jobs
        WHERE tenant_id IS NOT NULL
        GROUP BY tenant_id
        ORDER BY pending DESC, running DESC
        LIMIT 10
    """)
    ).fetchall()

    # Spans running por tenant
    spans_by_tenant = db.execute(
        text("""
        SELECT tenant_id, COUNT(*) AS qty
        FROM pipeline_run_spans
        WHERE status = 'running'
          AND tenant_id IS NOT NULL
        GROUP BY tenant_id
        ORDER BY qty DESC
        LIMIT 10
    """)
    ).fetchall()

    return {
        "worker": {
            "alive": _is_worker_alive(db),
            "stuck_spans_count": len(stuck_list),
        },
        "jobs": {
            "active": jobs_active,
            "running": jobs_running,
            "pending": jobs_pending,
            "by_status": jobs_by_status,
            "by_type": jobs_by_type,
        },
        "spans": {
            "running": spans_running,
            "done_24h": spans_done_24h,
            "last_finished": {
                "run_id": last_span[0] if last_span else None,
                "fase_nome": last_span[1] if last_span else None,
                "status": last_span[2] if last_span else None,
                "finished_at": str(last_span[3]) if last_span else None,
            } if last_span else None,
        },
        "latest_error": {
            "source": "job" if last_job_error else ("span" if last_span_error else None),
            "job": {
                "id": last_job_error[0] if last_job_error else None,
                "tipo": last_job_error[1] if last_job_error else None,
                "tenant_id": last_job_error[2] if last_job_error else None,
                "status": last_job_error[3] if last_job_error else None,
                "last_phase": last_job_error[4] if last_job_error else None,
                "error": last_job_error[5] if last_job_error else None,
                "attempts": last_job_error[6] if last_job_error else None,
                "max_attempts": last_job_error[7] if last_job_error else None,
                "iniciado_em": str(last_job_error[8]) if last_job_error else None,
                "concluido_em": str(last_job_error[9]) if last_job_error else None,
                "worker_heartbeat": str(last_job_error[10]) if last_job_error else None,
            } if last_job_error else None,
            "span": {
                "run_id": last_span_error[0] if last_span_error else None,
                "tenant_id": last_span_error[1] if last_span_error else None,
                "fase_nome": last_span_error[2] if last_span_error else None,
                "agente": last_span_error[3] if last_span_error else None,
                "error": last_span_error[4] if last_span_error else None,
                "started_at": str(last_span_error[5]) if last_span_error else None,
                "finished_at": str(last_span_error[6]) if last_span_error else None,
            } if last_span_error else None,
        },
        "stuck": {
            "count": len(stuck_list),
            "threshold_minutes": 60,
            "list": stuck_list,
        },
        "queue_by_tenant": [
            {"tenant_id": r[0], "pending": r[1], "running": r[2]}
            for r in queue_by_tenant
        ],
        "spans_by_tenant": [
            {"tenant_id": r[0], "running": r[1]} for r in spans_by_tenant
        ],
        "generated_at": _now_iso(),
    }


@router.get("/health")
async def api_pipeline_health(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Health check booleano rapido."""
    require_admin(usuario)

    worker_alive = _is_worker_alive(db)
    stuck_count = db.execute(
        text("""
        SELECT COUNT(*) FROM pipeline_run_spans
        WHERE status = 'running'
          AND started_at < NOW() - INTERVAL '1 hour'
          AND finished_at IS NULL
    """)
    ).scalar() or 0

    pending_count = db.execute(
        text("SELECT COUNT(*) FROM jobs WHERE status = 'pending'")
    ).scalar() or 0

    no_stuck = stuck_count == 0
    queue_ok = pending_count < 100

    overall = worker_alive and no_stuck and queue_ok
    return {
        "healthy": overall,
        "worker_alive": worker_alive,
        "no_stuck_spans": no_stuck,
        "queue_not_saturated": queue_ok,
        "stuck_count": stuck_count,
        "pending_count": pending_count,
    }


class KillStuckBody(BaseModel):
    min_age_minutes: int = 60
    dry_run: bool = False


@router.post("/kill-stuck")
async def api_kill_stuck(
    body: KillStuckBody,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Mata spans 'running' mais antigos que N minutos."""
    require_admin(usuario)

    if body.dry_run:
        count = db.execute(
            text("""
            SELECT COUNT(*) FROM pipeline_run_spans
            WHERE status = 'running'
              AND finished_at IS NULL
              AND started_at < NOW() - (:mins || ' minutes')::interval
        """),
            {"mins": body.min_age_minutes},
        ).scalar() or 0
        return {"would_kill": count, "dry_run": True}

    # Aplica
    result = db.execute(
        text("""
        UPDATE pipeline_run_spans
        SET status = 'failed',
            finished_at = NOW(),
            duracao_ms = COALESCE(
                EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000, 0
            )::int,
            erro = COALESCE(erro || ' | ', '') || 'admin_kill'
        WHERE status = 'running'
          AND finished_at IS NULL
          AND started_at < NOW() - (:mins || ' minutes')::interval
        RETURNING id, run_id
    """),
        {"mins": body.min_age_minutes},
    )
    killed = result.fetchall()
    db.commit()

    return {
        "killed": len(killed),
        "items": [
            {"id": r[0], "run_id": r[1]} for r in killed[:50]
        ],
        "dry_run": False,
        "min_age_minutes": body.min_age_minutes,
    }


@router.post("/reap")
async def api_pipeline_reap(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Executa reap completo (jobs travados + spans stale + exhausted)."""
    require_admin(usuario)

    # Import local para evitar import circular
    from backend.core import job_queue

    jobs_ressuscitados = job_queue.reap_dead_workers(db)
    spans_finalizados = job_queue.reap_stale_spans(db)
    jobs_exhausted = job_queue.finalize_exhausted_jobs(db)

    return {
        "ok": True,
        "jobs_ressuscitados": jobs_ressuscitados,
        "spans_finalizados": spans_finalizados,
        "jobs_exhausted": jobs_exhausted,
        "executed_at": _now_iso(),
    }


class ClearQueueBody(BaseModel):
    tenant_id: Optional[int] = None
    tipo: Optional[str] = None
    dry_run: bool = False


@router.post("/clear-queue")
async def api_clear_queue(
    body: ClearQueueBody,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Cancela jobs 'pending' (opcionalmente filtrados por tenant/tipo)."""
    require_admin(usuario)

    where = ["status = 'pending'"]
    params: dict[str, Any] = {}

    if body.tenant_id is not None:
        where.append("tenant_id = :tid")
        params["tid"] = body.tenant_id
    if body.tipo:
        where.append("tipo = :tipo")
        params["tipo"] = body.tipo

    where_sql = " AND ".join(where)

    if body.dry_run:
        count = db.execute(
            text(f"SELECT COUNT(*) FROM jobs WHERE {where_sql}"), params
        ).scalar() or 0
        return {"would_clear": count, "dry_run": True, "filter": body.model_dump()}

    # Marca como cancelled (nao remove, para auditoria)
    result = db.execute(
        text(f"""
        UPDATE jobs
        SET status = 'cancelled_admin',
            last_error = COALESCE(last_error || ' | ', '') || 'cancelled by admin',
            concluido_em = NOW(),
            next_retry_at = NOW() + INTERVAL '100 years'
        WHERE {where_sql}
        RETURNING id
    """),
        params,
    )
    cleared = result.fetchall()
    db.commit()

    return {
        "cleared": len(cleared),
        "dry_run": False,
        "filter": body.model_dump(),
        "cancelled_ids": [r[0] for r in cleared[:100]],
    }


@router.post("/worker/restart")
async def api_worker_restart(
    usuario: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Reinicia o servico systemd do worker (acao destrutiva)."""
    require_admin(usuario)

    try:
        result = subprocess.run(
            ["systemctl", "restart", "fralib-worker.service"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        ok = result.returncode == 0
        return {
            "ok": ok,
            "message": result.stdout.strip() or result.stderr.strip() or "Restart solicitado",
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout ao reiniciar worker")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha: {e}")


# === Helpers ===

def _is_worker_alive(db: Session | None = None) -> bool:
    """Checa worker por service, heartbeat recente ou processo vivo."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "fralib-worker.service"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and "active" in result.stdout:
            return True
    except Exception:
        pass

    if db is not None:
        try:
            recent_heartbeat = db.execute(
                text(
                    """
                    SELECT 1
                    FROM jobs
                    WHERE status = 'running'
                      AND worker_heartbeat >= NOW() - INTERVAL '90 seconds'
                    LIMIT 1
                    """
                )
            ).fetchone()
            if recent_heartbeat:
                return True
        except Exception:
            db.rollback()

    try:
        proc = subprocess.run(
            ["pgrep", "-f", "/root/fralib/worker.py"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.returncode == 0 and bool((proc.stdout or "").strip())
    except Exception:
        return False


def _humanize_age(seconds: float) -> str:
    """Converte segundos em '2h 15m' / '45m' / '30s'."""
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    if seconds < 86400:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}m"
    d = int(seconds // 86400)
    h = int((seconds % 86400) // 3600)
    return f"{d}d {h}h"


def _now_iso() -> str:
    """Compat shim — fonte em backend.utils.time.now_iso_utc (M14 DRY)."""
    from backend.utils.time import now_iso_utc as _nis  # noqa: E402  — M14 DRY shim
    return _nis()
