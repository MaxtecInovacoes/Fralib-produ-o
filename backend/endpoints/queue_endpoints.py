"""
Queue Status Endpoints — Métricas e status da fila de jobs
"""

from fastapi import APIRouter, Query, Depends
from sqlalchemy import text
from database import engine, get_db
from auth import get_current_user

router = APIRouter(prefix='/api/queue', tags=['queue'])


@router.get("/status")
async def queue_status(usuario: dict = Depends(get_current_user)):
    """Status geral da fila: pendentes, rodando, completos, falhados (24h)."""
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending') as pendentes,
                COUNT(*) FILTER (WHERE status = 'running') as rodando,
                COUNT(*) FILTER (WHERE status = 'completed') as completos,
                COUNT(*) FILTER (WHERE status = 'failed_permanent') as falhados,
                COUNT(*) as total
            FROM jobs
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)).fetchone()
    if not row:
        return {"pendentes": 0, "rodando": 0, "completos": 0, "falhados": 0, "total": 0}
    return {
        "pendentes": row[0] or 0,
        "rodando": row[1] or 0,
        "completos": row[2] or 0,
        "falhados": row[3] or 0,
        "total": row[4] or 0,
    }


@router.get("/job/{job_id}")
async def queue_job_detail(job_id: int, usuario: dict = Depends(get_current_user)):
    """Status detalhado de um job específico."""
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT id, tipo, status, tenant_id, attempts, max_attempts,
                   last_phase, last_error, created_at, iniciado_em, concluido_em,
                   worker_id, priority
            FROM jobs WHERE id = :id
        """), {"id": job_id}).fetchone()
    if not row:
        return {"erro": "Job não encontrado"}
    return {
        "id": row[0], "tipo": row[1], "status": row[2], "tenant_id": row[3],
        "attempts": row[4], "max_attempts": row[5], "last_phase": row[6],
        "last_error": row[7], "created_at": str(row[8]), "iniciado_em": str(row[9]),
        "concluido_em": str(row[10]), "worker_id": row[11], "priority": row[12],
    }


@router.get("/failed")
async def queue_failed(dias: int = Query(default=7, ge=1, le=30), usuario: dict = Depends(get_current_user)):
    """Lista jobs na dead-letter (pipeline_failures)."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, tenant_id, job_id, lead_nome, fase,
                   mensagem_amigavel, tentativas_automaticas, created_at
            FROM pipeline_failures
            WHERE created_at > NOW() - make_interval(days => :dias)
            ORDER BY created_at DESC
            LIMIT 50
        """), {"dias": dias}).fetchall()
    return [
        {
            "id": r[0], "tenant_id": r[1], "job_id": r[2], "lead_nome": r[3],
            "fase": r[4], "mensagem": r[5], "tentativas": r[6], "created_at": str(r[7]),
        }
        for r in rows
    ]


@router.get("/metrics")
async def queue_metrics(dias: int = Query(default=7, ge=1, le=30), usuario: dict = Depends(get_current_user)):
    """Métricas: tempo médio, taxa sucesso, throughput."""
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed') as sucesso,
                COUNT(*) FILTER (WHERE status = 'failed_permanent') as falhas,
                ROUND(AVG(EXTRACT(EPOCH FROM (concluido_em - iniciado_em)))::numeric, 1)
                    FILTER (WHERE status = 'completed' AND concluido_em IS NOT NULL AND iniciado_em IS NOT NULL)
                    as duracao_media_s,
                ROUND(AVG(attempts)::numeric, 1) FILTER (WHERE status = 'completed') as tentativas_media
            FROM jobs
            WHERE created_at > NOW() - make_interval(days => :dias)
              AND tipo IN ('pipeline_lead', 'pipeline_multiplos')
        """), {"dias": dias}).fetchone()

        franz_row = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed') as sucesso,
                COUNT(*) FILTER (WHERE status = 'failed_permanent') as falhas,
                ROUND(AVG(attempts)::numeric, 1) FILTER (WHERE status = 'completed') as tentativas_media
            FROM jobs
            WHERE created_at > NOW() - make_interval(days => :dias)
              AND tipo = 'franz_outreach'
        """), {"dias": dias}).fetchone()

    pipeline = {}
    if row:
        total = row[0] or 1
        pipeline = {
            "total": row[0] or 0,
            "sucesso": row[1] or 0,
            "falhas": row[2] or 0,
            "taxa_sucesso": round((row[1] or 0) / total, 2),
            "duracao_media_s": float(row[3]) if row[3] else None,
            "tentativas_media": float(row[4]) if row[4] else None,
        }

    franz = {}
    if franz_row:
        total_f = franz_row[0] or 1
        franz = {
            "total": franz_row[0] or 0,
            "sucesso": franz_row[1] or 0,
            "falhas": franz_row[2] or 0,
            "taxa_sucesso": round((franz_row[1] or 0) / total_f, 2),
            "tentativas_media": float(franz_row[3]) if franz_row[3] else None,
        }

    return {"pipeline": pipeline, "franz": franz}
