"""
Observability Endpoints — Dashboard de métricas do pipeline (PRD #10)
Protegido por tenant: cada usuário vê APENAS seus próprios dados.
Superadmin pode consultar qualquer tenant via ?tenant_id=.
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy import text
from backend.core.database import engine
from backend.core.auth import get_current_user

router = APIRouter(prefix="/api/observability", tags=["observability"])


def _resolve_tenant(usuario: dict, tenant_id_query: int = None) -> int:
    """Retorna o tenant_id correto: do usuário logado, ou se superadmin, da query."""
    user_tenant = usuario.get("tenant_id", usuario["id"])
    if usuario.get("role") == "superadmin" and tenant_id_query is not None:
        return tenant_id_query
    return user_tenant


def _fetch_run_level(conn, tenant_id: int, dias: int):
    """Busca dados agregados por RUN (distinct run_id) para um tenant."""
    return conn.execute(
        text("""
            SELECT
                COUNT(DISTINCT run_id) as total_runs,
                (
                    SELECT COUNT(*) FROM (
                        SELECT run_id
                        FROM pipeline_run_spans
                        WHERE tenant_id = :tenant_id
                          AND started_at > NOW() - make_interval(days => :dias)
                        GROUP BY run_id
                        HAVING bool_and(status = 'success')
                    ) runs_ok
                ) as runs_sucesso,
                COALESCE(SUM(custo_usd), 0) as custo_total,
                COALESCE(AVG(duracao_ms), 0)::int as duracao_media_ms,
                COUNT(*) FILTER (WHERE status = 'running') as fases_ativas,
                COALESCE(SUM(input_tokens), 0) as input_total,
                COALESCE(SUM(output_tokens), 0) as output_total
            FROM pipeline_run_spans s
            WHERE tenant_id = :tenant_id
              AND started_at > NOW() - make_interval(days => :dias)
        """),
        {"tenant_id": tenant_id, "dias": dias},
    ).fetchone()


@router.get("/dashboard")
async def obs_dashboard(
    dias: int = Query(default=7, ge=1, le=90),
    usuario: dict = Depends(get_current_user),
):
    tenant_id = _resolve_tenant(usuario)
    with engine.connect() as conn:
        row = _fetch_run_level(conn, tenant_id, dias)
    if not row or not row[0]:
        return {"total_runs": 0, "custo_total": 0}
    keys = [
        "total_runs",
        "runs_sucesso",
        "custo_total",
        "duracao_media_ms",
        "fases_ativas",
        "input_total",
        "output_total",
    ]
    d = dict(zip(keys, row))
    d["taxa_sucesso"] = round(d["runs_sucesso"] / max(d["total_runs"], 1) * 100, 1)
    d["custo_medio"] = round(d["custo_total"] / max(d["total_runs"], 1), 4)
    return d


@router.get("/por-agente")
async def obs_por_agente(
    dias: int = Query(default=7, ge=1, le=90),
    usuario: dict = Depends(get_current_user),
):
    tenant_id = _resolve_tenant(usuario)
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT fase_nome as agente,
                       COUNT(*) as chamadas,
                       ROUND(AVG(duracao_ms))::int as latencia_media_ms,
                       ROUND(AVG(custo_usd)::numeric, 4) as custo_medio,
                       ROUND(SUM(custo_usd)::numeric, 3) as custo_total,
                       COUNT(*) FILTER (WHERE status = 'error') as erros
                FROM pipeline_run_spans
                WHERE tenant_id = :tenant_id
                  AND started_at > NOW() - make_interval(days => :dias)
                GROUP BY fase_nome
                ORDER BY custo_total DESC
            """),
            {"tenant_id": tenant_id, "dias": dias},
        ).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/gargalos")
async def obs_gargalos(
    dias: int = Query(default=7, ge=1, le=90),
    usuario: dict = Depends(get_current_user),
):
    tenant_id = _resolve_tenant(usuario)
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT fase_nome as fase, agente,
                       duracao_ms, run_id, started_at as data
                FROM pipeline_run_spans
                WHERE tenant_id = :tenant_id
                  AND duracao_ms IS NOT NULL
                  AND started_at > NOW() - make_interval(days => :dias)
                ORDER BY duracao_ms DESC
                LIMIT 10
            """),
            {"tenant_id": tenant_id, "dias": dias},
        ).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/alertas")
async def obs_alertas(
    dias: int = Query(default=1, ge=1, le=7),
    usuario: dict = Depends(get_current_user),
):
    tenant_id = _resolve_tenant(usuario)
    alertas = []
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT
                    COUNT(DISTINCT run_id) as total,
                    (
                        SELECT COUNT(*) FROM (
                            SELECT run_id
                            FROM pipeline_run_spans
                            WHERE tenant_id = :tenant_id
                              AND started_at > NOW() - make_interval(days => 30)
                            GROUP BY run_id
                            HAVING bool_or(status = 'error')
                        ) runs_fail
                    ) as falhas,
                    ROUND(AVG(custo_usd)::numeric, 6) as custo_medio,
                    COALESCE(STDDEV(custo_usd), 0) as desvio
                FROM pipeline_run_spans s
                WHERE tenant_id = :tenant_id
                  AND started_at > NOW() - make_interval(days => 30)
            """),
            {"tenant_id": tenant_id},
        ).fetchone()

        if row and row[0] > 0:
            total = row[0]
            falhas = row[1] or 0
            taxa = falhas / max(total, 1)
            if taxa > 0.3:
                alertas.append(
                    {
                        "tipo": "taxa_falha_alta",
                        "valor": round(taxa, 2),
                        "falhas": falhas,
                        "total": total,
                    }
                )
            threshold = float(row[2] or 0) + 2 * float(row[3] or 0)
            if threshold > 0:
                caros = conn.execute(
                    text("""
                        SELECT run_id, fase_nome, custo_usd
                        FROM pipeline_run_spans
                        WHERE tenant_id = :tid
                          AND custo_usd > :thresh
                          AND started_at > NOW() - make_interval(days => :d)
                        ORDER BY custo_usd DESC LIMIT 5
                    """),
                    {"tid": tenant_id, "thresh": threshold, "d": dias},
                ).fetchall()
                for r in caros:
                    alertas.append(
                        {
                            "tipo": "custo_alto",
                            "run_id": r[0],
                            "fase": r[1],
                            "custo": round(r[2], 4),
                        }
                    )
    return alertas


@router.get("/traces")
async def obs_traces(
    dias: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=20, le=100),
    usuario: dict = Depends(get_current_user),
):
    tenant_id = _resolve_tenant(usuario)
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT DISTINCT ON (s.run_id)
                       s.run_id, s.trace_id, s.lead_id,
                       s.started_at as criado_em,
                       MAX(finished_at) as concluido_em,
                       bool_and(s.status = 'success') as status_ok,
                       SUM(s.duracao_ms) as duracao_total_ms,
                       SUM(s.custo_usd) as custo_total_usd,
                       COUNT(*) as total_fases
                FROM pipeline_run_spans s
                WHERE s.tenant_id = :tenant_id
                  AND s.started_at > NOW() - make_interval(days => :dias)
                GROUP BY s.run_id, s.trace_id, s.lead_id, s.started_at
                ORDER BY s.started_at DESC
                LIMIT :limit
            """),
            {"tenant_id": tenant_id, "dias": dias, "limit": limit},
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r._mapping)
        d["status"] = "success" if d.pop("status_ok") else "failed"
        d["nicho"] = ""
        result.append(d)
    return result


@router.get("/trace/{trace_id}")
async def obs_trace_detail(
    trace_id: str,
    usuario: dict = Depends(get_current_user),
):
    tenant_id = _resolve_tenant(usuario)
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT * FROM pipeline_run_spans
                WHERE trace_id = :tid AND tenant_id = :tenant_id
                ORDER BY fase_num ASC
            """),
            {"tid": trace_id, "tenant_id": tenant_id},
        ).fetchall()
    if not row:
        raise HTTPException(status_code=404, detail="trace não encontrado")
    return {
        "trace_id": trace_id,
        "spans": [dict(r._mapping) for r in row],
    }


# ══════════════════════════════════════════════════════════════
# ENDPOINTS POR RUN / SPAN / FASE (tenant-aware)
# ══════════════════════════════════════════════════════════════


@router.get("/spans/{run_id}")
async def obter_spans_por_run(
    run_id: str,
    usuario: dict = Depends(get_current_user),
):
    tenant_id = _resolve_tenant(usuario)
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, fase_num, fase_nome, agente, modelo,
                       started_at, finished_at, duracao_ms, status,
                       input_tokens, output_tokens, custo_usd, erro
                FROM pipeline_run_spans
                WHERE run_id = :run_id AND tenant_id = :tenant_id
                ORDER BY fase_num ASC
            """),
            {"run_id": run_id, "tenant_id": tenant_id},
        ).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/custos")
async def obter_custos(
    dias: int = Query(default=30, ge=1, le=90),
    _tenant_id: int = Query(None, alias="tenant_id"),
    usuario: dict = Depends(get_current_user),
):
    tenant_id = _resolve_tenant(usuario, _tenant_id)
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT
                    COUNT(*) as total_spans,
                    COUNT(DISTINCT run_id) as total_runs,
                    COALESCE(SUM(custo_usd), 0) as custo_total,
                    COALESCE(AVG(duracao_ms), 0)::int as duracao_media_ms,
                    COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                    COUNT(*) FILTER (WHERE status = 'error') as total_erros
                FROM pipeline_run_spans
                WHERE tenant_id = :tenant_id
                  AND started_at > NOW() - make_interval(days => :dias)
            """),
            {"tenant_id": tenant_id, "dias": dias},
        ).fetchone()
    return dict(row._mapping) if row else {}


@router.get("/gargalos-run")
async def obter_gargalos(
    dias: int = Query(default=30, ge=1, le=90),
    limite: int = Query(default=10, ge=1, le=50),
    _tenant_id: int = Query(None, alias="tenant_id"),
    usuario: dict = Depends(get_current_user),
):
    tenant_id = _resolve_tenant(usuario, _tenant_id)
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT fase_nome, agente, modelo, duracao_ms, custo_usd,
                       run_id, started_at, status
                FROM pipeline_run_spans
                WHERE tenant_id = :tenant_id
                  AND duracao_ms IS NOT NULL
                  AND started_at > NOW() - make_interval(days => :dias)
                ORDER BY duracao_ms DESC
                LIMIT :limite
            """),
            {"tenant_id": tenant_id, "dias": dias, "limite": limite},
        ).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/fases")
async def obter_fases_lentas(
    dias: int = Query(default=30, ge=1, le=90),
    _tenant_id: int = Query(None, alias="tenant_id"),
    usuario: dict = Depends(get_current_user),
):
    tenant_id = _resolve_tenant(usuario, _tenant_id)
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    fase_nome,
                    COUNT(*) as total,
                    ROUND(AVG(duracao_ms))::int as duracao_media_ms,
                    ROUND(AVG(custo_usd)::numeric, 4) as custo_medio,
                    ROUND(SUM(custo_usd)::numeric, 4) as custo_total,
                    COUNT(*) FILTER (WHERE status = 'error') as erros
                FROM pipeline_run_spans
                WHERE tenant_id = :tenant_id
                  AND started_at > NOW() - make_interval(days => :dias)
                GROUP BY fase_nome
                ORDER BY custo_total DESC
            """),
            {"tenant_id": tenant_id, "dias": dias},
        ).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/resumo")
async def obter_resumo(
    dias: int = Query(default=7, ge=1, le=90),
    _tenant_id: int = Query(None, alias="tenant_id"),
    usuario: dict = Depends(get_current_user),
):
    """Resumo completo de observabilidade para o tenant logado (1 chamada)."""
    tenant_id = _resolve_tenant(usuario, _tenant_id)

    with engine.connect() as conn:
        agg = conn.execute(
            text("""
                SELECT
                    COUNT(DISTINCT run_id) as total_runs,
                    COALESCE(SUM(custo_usd), 0) as custo_total,
                    COALESCE(AVG(duracao_ms), 0)::int as duracao_media_ms,
                    COUNT(*) FILTER (WHERE status = 'running') as fases_ativas,
                    COALESCE(SUM(input_tokens), 0) as input_total,
                    COALESCE(SUM(output_tokens), 0) as output_total,
                    MAX(started_at) as ultima_atividade
                FROM pipeline_run_spans
                WHERE tenant_id = :tenant_id
                  AND started_at > NOW() - make_interval(days => :dias)
            """),
            {"tenant_id": tenant_id, "dias": dias},
        ).fetchone()

        runs_sucesso = (
            conn.execute(
                text("""
                SELECT COUNT(*) FROM (
                    SELECT run_id
                    FROM pipeline_run_spans
                    WHERE tenant_id = :tenant_id
                      AND started_at > NOW() - make_interval(days => :dias)
                    GROUP BY run_id
                    HAVING bool_and(status = 'success')
                ) runs_ok
            """),
                {"tenant_id": tenant_id, "dias": dias},
            ).scalar()
            or 0
        )

        total_runs = agg[0] or 0

        fases = conn.execute(
            text("""
                SELECT fase_nome,
                       ROUND(AVG(duracao_ms))::int as duracao_media_ms,
                       ROUND(AVG(custo_usd)::numeric, 6) as custo_medio,
                       ROUND(SUM(custo_usd)::numeric, 6) as custo_total,
                       COUNT(*) as total
                FROM pipeline_run_spans
                WHERE tenant_id = :tenant_id
                  AND started_at > NOW() - make_interval(days => :dias)
                  AND duracao_ms IS NOT NULL
                GROUP BY fase_nome
                ORDER BY custo_total DESC
            """),
            {"tenant_id": tenant_id, "dias": dias},
        ).fetchall()

        runs = conn.execute(
            text("""
                SELECT
                    s.run_id,
                    s.lead_id,
                    MIN(s.started_at) as started_at,
                    bool_and(s.status = 'success') as success,
                    SUM(s.duracao_ms) as duracao_ms,
                    SUM(s.custo_usd) as custo_total,
                    COUNT(*) as total_fases
                FROM pipeline_run_spans s
                WHERE s.tenant_id = :tenant_id
                  AND s.started_at > NOW() - make_interval(days => :dias)
                GROUP BY s.run_id, s.lead_id
                ORDER BY MIN(s.started_at) DESC
                LIMIT 20
            """),
            {"tenant_id": tenant_id, "dias": dias},
        ).fetchall()

    return {
        "total_runs": total_runs,
        "custo_total": round(agg[1] or 0, 4),
        "custo_medio": round((agg[1] or 0) / max(total_runs, 1), 4),
        "duracao_media_ms": agg[2] or 0,
        "taxa_sucesso": round(runs_sucesso / max(total_runs, 1) * 100, 1),
        "fases_ativas": agg[3] or 0,
        "fases": [dict(r._mapping) for r in fases],
        "runs": [
            {
                "run_id": r[0],
                "lead_nome": str(r[1] or ""),
                "started_at": str(r[2]) if r[2] else None,
                "status": "success" if r[3] else "failed",
                "duracao_ms": r[4] or 0,
                "custo_total": round(r[5] or 0, 4),
                "total_fases": r[6] or 0,
            }
            for r in runs
        ],
    }
