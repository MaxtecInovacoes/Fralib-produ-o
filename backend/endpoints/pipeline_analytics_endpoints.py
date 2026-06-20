from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.core.database import get_db
from backend.core.auth import get_current_user

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


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
    total_sites = db.execute(text(f"SELECT COUNT(*) FROM leads {where} AND (site_url IS NOT NULL AND site_url != '' OR url_site IS NOT NULL AND url_site != '')"), params).scalar() or 0
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

