"""
Observability Endpoints — Dashboard de métricas do pipeline (PRD #10)

Rota base: /api/observability

Endpoints herdados (dashboard, por-agente, gargalos, alertas, traces, trace/{trace_id})
    → sem auth, leitura de métricas agregadas.

Endpoints novos (alerts CRUD, errors, RAG, quality-gate)
    → usam auth para isolamento multi-tenant onde aplicável.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import engine, get_db
from auth import get_current_user

router = APIRouter(prefix='/api/observability', tags=['observability'])


# ===== ALERTAS CRUD (novo) =====

@router.get("/alerts/unresolved")
def obs_alerts_unresolved(
    categoria: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    usuario: dict = Depends(get_current_user),
):
    """Lista alertas de sistema não resolvidos."""
    try:
        from backend.core.alerting import get_unresolved
        return get_unresolved(categoria=categoria, severity=severity, limit=limit)
    except Exception as exc:
        raise HTTPException(500, f"Erro ao buscar alertas: {exc}") from exc


@router.post("/alerts/{alert_id}/resolve")
def obs_alert_resolve(alert_id: int, usuario: dict = Depends(get_current_user)):
    """Marca alerta como resolvido."""
    try:
        from backend.core.alerting import resolve
        ok = resolve(alert_id)
        if not ok:
            raise HTTPException(404, f"Alerta #{alert_id} não encontrado")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Erro ao resolver: {exc}") from exc


# ===== ERROR LOGS (novo) =====

@router.get("/errors/top")
def obs_errors_top(
    hours: int = Query(24, ge=1, le=168),
    usuario: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Top erros nas últimas N horas."""
    try:
        rows = db.execute(text("""
            SELECT categoria, exception_type, step_name, count(*) AS n,
                   max(criado_em) AS ultimo
            FROM pipeline_error_log
            WHERE criado_em > NOW() - INTERVAL ':h hours'
            GROUP BY 1, 2, 3
            ORDER BY n DESC
            LIMIT 50
        """), {"h": hours}).fetchall()
        return [
            {"categoria": r[0], "exception_type": r[1], "step_name": r[2],
             "count": r[3], "ultimo": r[4].isoformat() if r[4] else None}
            for r in rows
        ]
    except Exception as exc:
        raise HTTPException(500, f"Erro ao buscar erros: {exc}") from exc


@router.get("/errors/lead/{lead_id}")
def obs_lead_errors(
    lead_id: str,
    usuario: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Erros de um lead específico."""
    try:
        rows = db.execute(text("""
            SELECT step_name, exception_type, message, categoria, criado_em
            FROM pipeline_error_log WHERE lead_id = :lid
            ORDER BY criado_em DESC LIMIT 20
        """), {"lid": lead_id}).fetchall()
        return [
            {"step_name": r[0], "exception_type": r[1], "message": r[2],
             "categoria": r[3], "criado_em": r[4].isoformat() if r[4] else None}
            for r in rows
        ]
    except Exception as exc:
        raise HTTPException(500, f"Erro ao buscar erros do lead: {exc}") from exc


# ===== QUALITY GATE HISTORY (novo) =====

@router.get("/quality-gate/history")
def obs_qg_history(
    limit: int = Query(20, ge=1, le=100),
    usuario: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Histórico de Quality Gate results."""
    try:
        rows = db.execute(text("""
            SELECT lead_id, segmento, vision_score, a11y_score,
                   aprovado, reparos_aplicados, criado_em
            FROM quality_gate_results
            ORDER BY criado_em DESC LIMIT :lim
        """), {"lim": limit}).fetchall()
        return [
            {"lead_id": r[0], "segmento": r[1],
             "vision_score": float(r[2]) if r[2] else None,
             "a11y_score": float(r[3]) if r[3] else None,
             "aprovado": r[4], "reparos_aplicados": r[5],
             "criado_em": r[6].isoformat() if r[6] else None}
            for r in rows
        ]
    except Exception as exc:
        raise HTTPException(500, f"Erro ao buscar QG history: {exc}") from exc


# ===== RAG (novo) =====

@router.get("/rag/leads/search")
def obs_rag_leads(
    q: str = Query(..., min_length=2),
    tenant_id: int | None = Query(None),
    limit: int = Query(10, ge=1, le=20),
    usuario: dict = Depends(get_current_user),
):
    """Busca leads semanticamente similares via RAG vetorial."""
    try:
        from backend.core.rag import search_leads
        tid = tenant_id or usuario.get("tenant_id") or usuario.get("user_id")
        return search_leads(q, tenant_id=tid, limit=limit)
    except Exception as exc:
        raise HTTPException(500, f"Erro na busca RAG: {exc}") from exc


@router.get("/rag/failures/search")
def obs_rag_failures(
    q: str = Query(..., min_length=2),
    step_name: str | None = Query(None),
    limit: int = Query(10, ge=1, le=20),
):
    """Busca erros de pipeline semanticamente similares (troubleshooting)."""
    try:
        from backend.core.rag import search_failures
        return search_failures(q, step_name=step_name, limit=limit)
    except Exception as exc:
        raise HTTPException(500, f"Erro na busca RAG de falhas: {exc}") from exc


# ===== PIPELINE TRACE DETAIL (novo, suporta run_id) =====

@router.get("/traces/run/{run_id}")
def obs_trace_by_run(run_id: str, usuario: dict = Depends(get_current_user)):
    """Trace completo por run_id."""
    try:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT trace_id, run_id, lead_nome, nicho, tier,
                       estado_final, erro_final, total_tokens,
                       custo_estimado, duracao_segundos, spans, criado_em
                FROM pipeline_traces WHERE run_id = :rid LIMIT 1
            """), {"rid": run_id}).fetchone()
        if not row:
            raise HTTPException(404, f"Trace {run_id} não encontrado")
        return {
            "trace_id": row[0], "run_id": row[1], "lead_nome": row[2],
            "nicho": row[3], "tier": row[4], "estado_final": row[5],
            "erro_final": row[6], "total_tokens": row[7],
            "custo_estimado": float(row[8]) if row[8] else None,
            "duracao_segundos": row[9], "spans": row[10],
            "criado_em": row[11].isoformat() if row[11] else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Erro ao buscar trace: {exc}") from exc


# ===== DASHBOARD (legado) =====

@router.get("/dashboard")
async def obs_dashboard(dias: int = Query(default=7, ge=1, le=90)):
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
                COUNT(*) as total_runs,
                COUNT(*) FILTER (WHERE status = 'success') as sucesso,
                COUNT(*) FILTER (WHERE status = 'failed') as falhas,
                ROUND(AVG(duracao_total_ms)::numeric / 1000, 1) as duracao_media_s,
                ROUND(AVG(custo_total_usd)::numeric, 4) as custo_medio,
                ROUND(SUM(custo_total_usd)::numeric, 2) as custo_total,
                ROUND(AVG(total_cache_hit::float / NULLIF(total_input_tokens, 0) * 100)::numeric, 1) as cache_hit_pct,
                ROUND(AVG(total_chamadas_llm)::numeric, 1) as chamadas_media
            FROM pipeline_traces
            WHERE created_at > NOW() - make_interval(days => :dias)
        """), {"dias": dias}).fetchone()
    if not row:
        return {"total_runs": 0}
    return dict(row._mapping)


@router.get("/por-agente")
async def obs_por_agente(dias: int = Query(default=7, ge=1, le=90)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                span->>'agente' as agente,
                COUNT(*) as chamadas,
                ROUND(AVG((span->>'duracao_ms')::int)::numeric, 0) as latencia_media_ms,
                ROUND(AVG((span->>'custo_usd')::float)::numeric, 4) as custo_medio,
                ROUND(SUM((span->>'custo_usd')::float)::numeric, 3) as custo_total,
                COUNT(*) FILTER (WHERE span->>'status' = 'error') as erros
            FROM pipeline_traces, jsonb_array_elements(spans_json) as span
            WHERE created_at > NOW() - make_interval(days => :dias)
            GROUP BY span->>'agente'
            ORDER BY custo_total DESC
        """), {"dias": dias}).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/gargalos")
async def obs_gargalos(dias: int = Query(default=7, ge=1, le=90)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                span->>'agente' as agente,
                span->>'nome' as fase,
                (span->>'duracao_ms')::int as duracao_ms,
                trace_id,
                lead_nome
            FROM pipeline_traces, jsonb_array_elements(spans_json) as span
            WHERE created_at > NOW() - make_interval(days => :dias)
              AND (span->>'duracao_ms')::int IS NOT NULL
            ORDER BY (span->>'duracao_ms')::int DESC
            LIMIT 10
        """), {"dias": dias}).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/alertas")
async def obs_alertas(dias: int = Query(default=1, ge=1, le=7)):
    alertas = []
    with engine.connect() as conn:
        stats = conn.execute(text("""
            SELECT AVG(custo_total_usd) as media, COALESCE(STDDEV(custo_total_usd), 0) as desvio
            FROM pipeline_traces WHERE created_at > NOW() - INTERVAL '30 days'
        """)).fetchone()

        if stats and stats[0]:
            threshold = float(stats[0]) + 2 * float(stats[1])
            caros = conn.execute(text("""
                SELECT trace_id, lead_nome, custo_total_usd
                FROM pipeline_traces
                WHERE created_at > NOW() - make_interval(days => :dias)
                  AND custo_total_usd > :threshold
            """), {"dias": dias, "threshold": threshold}).fetchall()
            for r in caros:
                alertas.append({"tipo": "custo_alto", "trace_id": r[0], "lead": r[1], "custo": round(r[2], 3)})

        taxa_row = conn.execute(text("""
            SELECT COUNT(*) FILTER (WHERE status = 'failed') as falhas, COUNT(*) as total
            FROM pipeline_traces WHERE created_at > NOW() - make_interval(days => :dias)
        """), {"dias": dias}).fetchone()

        if taxa_row and taxa_row[1] > 0:
            taxa = taxa_row[0] / taxa_row[1]
            if taxa > 0.3:
                alertas.append({"tipo": "taxa_falha_alta", "valor": round(taxa, 2), "falhas": taxa_row[0], "total": taxa_row[1]})

    return alertas


@router.get("/traces")
async def obs_traces(dias: int = Query(default=7, ge=1, le=90), limit: int = Query(default=20, le=100)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT trace_id, run_id, lead_nome, nicho, tier, complexidade,
                   duracao_total_ms, status, custo_total_usd, total_chamadas_llm, created_at
            FROM pipeline_traces
            WHERE created_at > NOW() - make_interval(days => :dias)
            ORDER BY created_at DESC LIMIT :limit
        """), {"dias": dias, "limit": limit}).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/trace/{trace_id}")
async def obs_trace_detail(trace_id: str):
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT * FROM pipeline_traces WHERE trace_id = :tid
        """), {"tid": trace_id}).fetchone()
    if not row:
        return {"erro": "trace não encontrado"}
    return dict(row._mapping)
