"""Adiciona endpoints faltantes do admin: escalados, conversas-ativas, assumir, pipeline-analytics."""
import sys

sys.path.append("/opt/fralib/backend")
sys.path.append("/opt/fralib/backend/core")

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/leads", tags=["leads-missing"])


# ─── Leads Escalados (Human Followup) ───────────────────────────────────────

@router.get("/escalados")
async def get_escalados(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Lista leads que precisam de followup humano (erros, timeouts, sem contexto)."""
    uid = usuario.get("tenant_id", usuario["id"])
    try:
        rows = db.execute(text("""
            SELECT id, nome, telefone, whatsapp, cidade, segmento,
                   atualizado_em, status, sdr_stage,
                   COALESCE(observacoes, followup_reason, '') as followup_reason
            FROM leads
            WHERE user_id = :uid
              AND (
                sdr_stage IN ('escalated', 'human_followup', 'blocked', 'needs_human')
                OR status IN ('erro', 'failed', 'escalated')
                OR (observacoes ILIKE '%escalado%' OR observacoes ILIKE '%followup%')
              )
            ORDER BY atualizado_em DESC NULLS LAST
            LIMIT 50
        """), {"uid": uid}).fetchall()

        escalados = []
        for r in rows:
            d = dict(r._mapping)
            for k in ("atualizado_em", "criado_em"):
                if d.get(k):
                    d[k] = str(d[k])
            escalados.append(d)
        return {"escalados": escalados, "total": len(escalados)}
    except Exception as e:
        return {"escalados": [], "total": 0, "error": str(e)}


@router.post("/{lead_id}/assumir")
async def assumir_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Marca lead como assumido pelo humano (limpa sdr_stage)."""
    uid = usuario.get("tenant_id", usuario["id"])
    try:
        result = db.execute(text("""
            UPDATE leads
            SET sdr_stage = 'human_takeover',
                status = 'pendente',
                atualizado_em = NOW()
            WHERE id = :id AND user_id = :uid
            RETURNING id
        """), {"id": lead_id, "uid": uid}).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Lead nao encontrado")
        db.commit()
        return {"ok": True, "lead_id": lead_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Conversas Ativas ────────────────────────────────────────────────────────

@router.get("/conversas-ativas")
async def get_conversas_ativas(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Lista leads com conversa ativa (interações recentes WhatsApp)."""
    uid = usuario.get("tenant_id", usuario["id"])
    try:
        rows = db.execute(text("""
            SELECT
                l.id, l.nome, l.cidade, l.segmento, l.telefone, l.whatsapp,
                l.sdr_stage, l.url_site, l.status, l.atualizado_em,
                COUNT(i.id) FILTER (WHERE i.direcao = 'entrada' AND i.criado_em > NOW() - INTERVAL '48 hours') as msgs_recebidas,
                MAX(i.criado_em) as ultima_msg
            FROM leads l
            LEFT JOIN interacoes i ON i.lead_id = l.id
            WHERE l.user_id = :uid
              AND l.status NOT IN ('descartado', 'perdido')
            GROUP BY l.id
            HAVING COUNT(i.id) > 0
            ORDER BY ultima_msg DESC NULLS LAST
            LIMIT 30
        """), {"uid": uid}).fetchall()

        leads = []
        for r in rows:
            d = dict(r._mapping)
            for k in ("atualizado_em", "ultima_msg"):
                if d.get(k):
                    d[k] = str(d[k])
            leads.append(d)
        return {"leads": leads, "total": len(leads)}
    except Exception as e:
        return {"leads": [], "total": 0, "error": str(e)}


# ─── Pipeline Analytics ─────────────────────────────────────────────────────

router_analytics = APIRouter(prefix="/api/dashboard", tags=["dashboard-analytics"])


@router_analytics.get("/pipeline-analytics")
async def get_pipeline_analytics(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Analytics do pipeline por tenant (totais, conversão, timeline)."""
    uid = usuario.get("tenant_id", usuario["id"])
    try:
        # Totais
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

        # Por dia (últimos 30 dias)
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
            {"dia": str(r.dia), "leads": r.leads, "sites": r.sites}
            for r in por_dia
        ]

        # Por segmento
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
            {"segmento": r.segmento or "sem", "total": r.total, "score_medio": float(r.score_medio or 0)}
            for r in por_segmento
        ]

        return {
            "totais": {
                "total_leads": int(t.get("total_leads") or 0),
                "capturados": int(t.get("capturados") or 0),
                "concluidos": int(t.get("concluidos") or 0),
                "convertidos": int(t.get("convertidos") or 0),
                "perdidos": int(t.get("perdidos") or 0),
                "score_medio": float(t.get("score_medio") or 0),
                "receita_total": float(t.get("receita_total") or 0),
                "taxa_conversao": round(
                    (int(t.get("convertidos") or 0) / max(int(t.get("capturados") or 1), 1)) * 100, 1
                ),
            },
            "timeline": timeline,
            "segmentos": segmentos,
        }
    except Exception as e:
        return {
            "totais": {},
            "timeline": [],
            "segmentos": [],
            "error": str(e),
        }
