"""Dashboard Analytics — métricas e timelines para o admin."""
import sys
sys.path.append("/opt/fralib/backend")
sys.path.append("/opt/fralib/backend/core")

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard-analytics"])


@router.get("/pipeline-analytics")
async def get_pipeline_analytics(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Analytics do pipeline: totais, conversão, timeline, segmentos."""
    uid = usuario.get("tenant_id", usuario["id"])
    try:
        totais = db.execute(text("""
            SELECT
                COUNT(*) as total_leads,
                COUNT(*) FILTER (WHERE status = 'capturado') as capturados,
                COUNT(*) FILTER (WHERE status = 'concluido') as concluidos,
                COUNT(*) FILTER (WHERE status = 'convertido') as convertidos,
                COUNT(*) FILTER (WHERE status IN ('erro', 'descartado')) as perdidos,
                COALESCE(AVG(score) FILTER (WHERE score > 0), 0) as score_medio,
                COALESCE(SUM(valor_venda) FILTER (WHERE valor_venda > 0), 0) as receita_total
            FROM leads
            WHERE user_id = :uid
        """), {"uid": uid}).fetchone()
        t = dict(totais._mapping) if totais else {}

        por_dia = db.execute(text("""
            SELECT DATE(criado_em) as dia,
                   COUNT(*) as leads,
                   COUNT(*) FILTER (WHERE status = 'concluido') as sites
            FROM leads
            WHERE user_id = :uid AND criado_em > NOW() - INTERVAL '30 days'
            GROUP BY dia
            ORDER BY dia DESC
        """), {"uid": uid}).fetchall()
        timeline = [
            {"dia": str(r.dia), "leads": int(r.leads), "sites": int(r.sites)}
            for r in por_dia
        ]

        por_segmento = db.execute(text("""
            SELECT segmento,
                   COUNT(*) as total,
                   COALESCE(AVG(score) FILTER (WHERE score > 0), 0) as score_medio
            FROM leads
            WHERE user_id = :uid
            GROUP BY segmento
            ORDER BY total DESC
            LIMIT 10
        """), {"uid": uid}).fetchall()
        segmentos = [
            {"segmento": r.segmento or "sem", "total": int(r.total), "score_medio": float(r.score_medio or 0)}
            for r in por_segmento
        ]

        total_leads = int(t.get("total_leads") or 0)
        convertidos = int(t.get("convertidos") or 0)
        return {
            "totais": {
                "total_leads": total_leads,
                "capturados": int(t.get("capturados") or 0),
                "concluidos": int(t.get("concluidos") or 0),
                "convertidos": convertidos,
                "perdidos": int(t.get("perdidos") or 0),
                "score_medio": float(t.get("score_medio") or 0),
                "receita_total": float(t.get("receita_total") or 0),
                "taxa_conversao": round((convertidos / max(total_leads, 1)) * 100, 1),
            },
            "timeline": timeline,
            "segmentos": segmentos,
        }
    except Exception as e:
        return {
            "totais": {
                "total_leads": 0, "capturados": 0, "concluidos": 0,
                "convertidos": 0, "perdidos": 0, "score_medio": 0,
                "receita_total": 0, "taxa_conversao": 0,
            },
            "timeline": [],
            "segmentos": [],
            "error": str(e),
        }