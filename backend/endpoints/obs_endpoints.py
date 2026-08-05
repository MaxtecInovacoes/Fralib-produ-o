"""
Observability Endpoints — Dashboard de métricas do pipeline (PRD #10)
"""

from fastapi import APIRouter, Query
from sqlalchemy import text
from database import engine

router = APIRouter(prefix='/api/observability', tags=['observability'])


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
            SELECT
                COUNT(*) FILTER (WHERE status = 'failed') as falhas,
                COUNT(*) as total
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
            ORDER BY created_at DESC
            LIMIT :limit
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
