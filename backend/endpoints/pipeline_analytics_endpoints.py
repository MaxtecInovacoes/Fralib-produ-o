"""
Pipeline Analytics Endpoints — métricas e médias históricas para a waveform do admin.

Adicionado PRD #65: GET /api/pipeline/avg-by-macro retorna a média de duração por
macro (buscar / analisar / produzir / publicar) para o tenant atual, agregando
spans de `pipeline_run_spans` dos últimos N dias.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.core.database import get_db
from backend.core.auth import get_current_user

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


# Mapeia fase_nome (de pipeline_run_spans) para a macro correspondente
# na waveform. Mantém paridade com macroFromKey/macroFromNum em
# frontend/js/admin/pipeline-waveform.js.
_MACRO_MAP = {
    'hunter': 'buscar',
    'caio': 'analisar', 'jina': 'analisar', 'mercado': 'analisar',
    'midia': 'analisar', 'agente_nicho': 'analisar',
    'prompt': 'produzir', 'designer': 'produzir', 'builder': 'produzir',
    'arquiteto': 'produzir',
    'deploy': 'publicar', 'franz': 'publicar', 'bryan': 'publicar',
}


@router.get("/analytics/overview")
async def get_analytics(
    periodo: str = "mes",
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    from datetime import datetime, timedelta

    agora = datetime.now()
    if periodo == "hoje":
        inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "semana":
        inicio = agora - timedelta(days=7)
    elif periodo == "mes":
        inicio = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "ano":
        inicio = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        inicio = None

    tenant_id_a = usuario.get("tenant_id", usuario["id"])
    if inicio:
        where = "WHERE user_id = :uid AND criado_em >= :inicio"
        params = {"uid": tenant_id_a, "inicio": inicio.isoformat()}
    else:
        where = "WHERE user_id = :uid"
        params = {"uid": tenant_id_a}

    total_leads = db.execute(text(f"SELECT COUNT(*) FROM leads {where}"), params).scalar() or 0
    total_sites = db.execute(text(f"SELECT COUNT(*) FROM leads {where} AND ((site_url IS NOT NULL AND site_url != '') OR (url_site IS NOT NULL AND url_site != ''))"), params).scalar() or 0
    total_vendidos = db.execute(text(f"SELECT COUNT(*) FROM leads {where} AND valor_venda > 0"), params).scalar() or 0
    receita = db.execute(text(f"SELECT COALESCE(SUM(valor_venda),0) FROM leads {where} AND valor_venda > 0"), params).scalar() or 0
    conversao_site = round((total_sites / total_leads * 100), 1) if total_leads > 0 else 0
    conversao_venda = round((total_vendidos / total_sites * 100), 1) if total_sites > 0 else 0

    sql_por_dia = "SELECT DATE(criado_em::timestamp) as dia, COUNT(*) as total FROM leads WHERE user_id = :uid AND criado_em IS NOT NULL AND criado_em != '' GROUP BY dia ORDER BY dia DESC LIMIT 30"
    leads_por_dia_rows = db.execute(text(sql_por_dia), {"uid": tenant_id_a}).fetchall()
    sql_cidades = f"SELECT cidade, COUNT(*) as total FROM leads {where} GROUP BY cidade ORDER BY total DESC LIMIT 8"
    top_cidades_rows = db.execute(text(sql_cidades), params).fetchall()
    sql_nichos = f"SELECT segmento, COUNT(*) as total FROM leads {where} GROUP BY segmento ORDER BY total DESC LIMIT 8"
    top_nichos_rows = db.execute(text(sql_nichos), params).fetchall()
    total_ciclos = db.execute(text("SELECT COUNT(*) FROM ciclos WHERE user_id = :uid"), {"uid": tenant_id_a}).scalar() or 0

    return {
        "periodo": periodo,
        "total_leads": total_leads,
        "total_sites": total_sites,
        "total_vendidos": total_vendidos,
        "receita": float(receita),
        "conversao": conversao_site,
        "conversao_venda": conversao_venda,
        "total_ciclos": total_ciclos,
        "leads_qualificados": total_sites,
        "taxa_conversao": conversao_site,
        "por_dia": [{"dia": str(r.dia), "total": r.total} for r in leads_por_dia_rows],
        "por_cidade": [{"nome": r.cidade or "-", "total": r.total} for r in top_cidades_rows],
        "por_nicho": [{"nome": r.segmento or "-", "total": r.total} for r in top_nichos_rows],
    }


@router.get("/avg-by-macro")
async def pipeline_avg_by_macro(
    dias: int = Query(default=30, ge=1, le=180),
    min_samples: int = Query(default=3, ge=1, le=50),
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Media de duracao por macro (4 etapas) para o tenant atual.

    Cada macro agrega a media ponderada de duracao de todos os spans
    (fase_nome) que pertencem a ela, calculado sobre os ultimos `dias`
    runs com status='success'.

    Retorna `total_avg_seconds` apenas se TODAS as 4 macros tem pelo
    menos `min_samples` (default 3). Caso contrario retorna null e a UI
    mostra 'calculando media'.
    """
    tenant_id = usuario.get("tenant_id", usuario["id"])
    rows = db.execute(
        text("""
            SELECT fase_nome,
                   COUNT(*) as samples,
                   ROUND(AVG(duracao_ms) / 1000.0, 1) as avg_seconds
            FROM pipeline_run_spans
            WHERE tenant_id = :tenant_id
              AND status = 'success'
              AND started_at > NOW() - make_interval(days => :dias)
            GROUP BY fase_nome
        """),
        {"tenant_id": tenant_id, "dias": dias},
    ).fetchall()

    macros = {
        'buscar':   {'avg_seconds': 0.0, 'samples': 0},
        'analisar': {'avg_seconds': 0.0, 'samples': 0},
        'produzir': {'avg_seconds': 0.0, 'samples': 0},
        'publicar': {'avg_seconds': 0.0, 'samples': 0},
    }
    for r in rows:
        macro = _MACRO_MAP.get(r.fase_nome)
        if macro and macro in macros:
            m = macros[macro]
            new_samples = m['samples'] + int(r.samples)
            # media ponderada: soma das medias * samples, dividido pelo total de samples
            if new_samples > 0:
                m['avg_seconds'] = round(
                    (m['avg_seconds'] * m['samples'] + float(r.avg_seconds) * int(r.samples)) / new_samples,
                    1,
                )
            m['samples'] = new_samples

    has_all = all(macros[m]['samples'] >= min_samples for m in macros)
    total = round(sum(macros[m]['avg_seconds'] for m in macros), 1) if has_all else None

    return {
        "macros": macros,
        "total_avg_seconds": total,
        "window_days": dias,
        "min_samples": min_samples,
    }
