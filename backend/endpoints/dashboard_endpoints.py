from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.core.database import get_db
from backend.endpoints.auth_endpoints import get_current_user

router = APIRouter(prefix='/api/dashboard', tags=['dashboard'])

class CRMData(BaseModel):
    pendente: List[Dict[str, Any]] = []
    enviado: List[Dict[str, Any]] = []
    respondeu: List[Dict[str, Any]] = []
    convertido: List[Dict[str, Any]] = []

@router.get('/incomplete')
async def get_incomplete(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        falhas = db.execute(text(
            "SELECT id, nome, cidade, segmento, score, status, tentativas FROM leads WHERE status = 'erro' AND user_id = :uid ORDER BY criado_em DESC LIMIT 50"
        ), {"uid": tenant_id}).fetchall()
        descartados = db.execute(text(
            "SELECT id, nome, cidade, segmento, score, status FROM leads WHERE status = 'descartado' AND user_id = :uid ORDER BY criado_em DESC LIMIT 50"
        ), {"uid": tenant_id}).fetchall()
        return {
            "falhas": [dict(r._mapping) for r in falhas],
            "descartados": [dict(r._mapping) for r in descartados]
        }
    except Exception as e:
        print(f"[Dashboard] Erro incomplete: {e}")
        return {"falhas": [], "descartados": []}

@router.get('/crm')
async def get_crm(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        result = db.execute(text("""
            SELECT
                l.id, l.nome, l.cidade, l.segmento, l.telefone,
                COALESCE(NULLIF(l.telefone_whatsapp,''), l.whatsapp, l.telefone) as telefone_whatsapp,
                l.score, l.status, l.sdr_stage, l.url_site, l.criado_em,
                l.valor_venda,
                COALESCE(v.views_count, 0) as views_count,
                COALESCE(v.clicks_count, 0) as clicks_count
            FROM leads l
            LEFT JOIN (
                SELECT lead_id,
                       COUNT(*) FILTER (WHERE evento = 'view') as views_count,
                       COUNT(*) FILTER (WHERE evento LIKE 'click_%') as clicks_count
                FROM site_visitas
                WHERE criado_em > NOW() - INTERVAL '30 days'
                GROUP BY lead_id
            ) v ON v.lead_id = l.id
            WHERE l.user_id = :uid
            ORDER BY l.score DESC
        """), {"uid": tenant_id}).fetchall()

        leads = []
        for r in result:
            d = dict(r._mapping)
            # PR15: serializar campos numericos/data pra JSON
            if d.get('valor_venda') is not None:
                d['valor_venda'] = float(d['valor_venda'])
            if d.get('criado_em') is not None:
                d['criado_em'] = str(d['criado_em'])
            leads.append(d)

        # Mapear status/sdr_stage do banco para colunas do Kanban
        data = {"fila": [], "intro": [], "f1": [], "f2": [], "negotiation": [], "qualificado": [], "lost": [], "won": []}

        for lead in leads:
            status = (lead.get('status') or 'pendente').lower()
            sdr_stage = (lead.get('sdr_stage') or 'hook').lower()

            # Leads sem site pronto NÃO aparecem no kanban
            if status in ('pendente', 'processando', 'capturado', 'erro'):
                continue
            elif status == 'concluido':
                if sdr_stage in ('hook', 'pendente_wpp'):
                    # Site pronto, aguardando SDR enviar primeira msg
                    data['fila'].append(lead)
                elif sdr_stage in ('qualify', 'intro'):
                    data['intro'].append(lead)
                elif sdr_stage in ('pain', 'amplify', 'followup1', 'f1', 'follow_up_1', 'followup_24h', 'scheduled'):
                    data['f1'].append(lead)
                elif sdr_stage in ('tease', 'proof', 'followup2', 'f2', 'follow_up_2', 'rapport', 'education', 'followup_72h'):
                    data['f2'].append(lead)
                elif sdr_stage in ('reveal', 'feedback', 'close', 'urgency', 'negotiation', 'negociacao'):
                    data['negotiation'].append(lead)
                elif sdr_stage in ('handoff', 'qualificado', 'qualified'):
                    data['qualificado'].append(lead)
                elif sdr_stage in ('won', 'ganho', 'convertido'):
                    data['won'].append(lead)
                elif sdr_stage in ('lost',):
                    data['lost'].append(lead)
                else:
                    data['intro'].append(lead)
            elif status in ('descartado', 'lost', 'perdido'):
                data['lost'].append(lead)
            elif status in ('convertido', 'won', 'ganho'):
                data['won'].append(lead)
            # Qualquer outro status: não aparece no kanban

        return data
    except Exception as e:
        print(f"[Dashboard] Erro ao carregar CRM: {e}")
        return {"fila": [], "intro": [], "f1": [], "f2": [], "negotiation": [], "qualificado": [], "lost": [], "won": []}


# ─── COST-PER-LEAD ───────────────────────────────────────────────────
# Preços por 1M tokens (USD) — atualizar conforme modelo usado
_INPUT_PRICE_PER_M = 3.0    # USD por 1M input tokens
_OUTPUT_PRICE_PER_M = 15.0  # USD por 1M output tokens
_USD_BRL = 5.6              # taxa USD→BRL


def _calc_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000 * _INPUT_PRICE_PER_M
            + output_tokens / 1_000_000 * _OUTPUT_PRICE_PER_M)


@router.get('/cost-per-lead')
async def get_cost_per_lead(
    limit: int = 50,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Custo de LLM por execução de pipeline (input/output tokens → USD/BRL)."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    try:
        limit = max(1, min(int(limit), 200))
        rows = db.execute(text("""
            SELECT
                id as run_id, lead_id, lead_nome, user_id,
                input_tokens, output_tokens,
                started_at, finished_at, plano_no_momento, status
            FROM pipeline_executions
            WHERE user_id = :uid
              AND input_tokens IS NOT NULL
            ORDER BY finished_at DESC NULLS LAST, started_at DESC
            LIMIT :lim
        """), {"uid": tenant_id, "lim": limit}).fetchall()

        items = []
        for r in rows:
            inp = int(r.input_tokens or 0)
            out = int(r.output_tokens or 0)
            cost_usd = _calc_cost_usd(inp, out)
            items.append({
                "run_id": str(r.id),
                "lead_id": r.lead_id,
                "lead_nome": r.lead_nome,
                "nicho": None,
                "calls": 1,
                "input_tokens": inp,
                "output_tokens": out,
                "cost_usd": round(cost_usd, 4),
                "cost_brl": round(cost_usd * _USD_BRL, 4),
                "atualizado_em": r.finished_at.isoformat() if r.finished_at else r.started_at.isoformat(),
            })
        return {"pipelines": items}
    except Exception as e:
        print(f"[Dashboard] Erro cost-per-lead: {e}")
        return {"pipelines": []}


# ─── PIPELINE ANALYTICS ──────────────────────────────────────────────

@router.get('/pipeline-analytics')
async def get_pipeline_analytics(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Analytics do pipeline: resumo, funil, taxas, distribuição por stage."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    try:
        # Summary: leads ativos (concluído + SDR em andamento)
        active_leads_row = db.execute(text("""
            SELECT COUNT(*) FROM leads
            WHERE user_id = :uid AND status = 'concluido'
        """), {"uid": tenant_id}).fetchone()
        active_leads = active_leads_row[0] if active_leads_row else 0

        # Pipeline: deals em negociação/handoff com valor
        pipeline_rows = db.execute(text("""
            SELECT COUNT(*) as cnt, COALESCE(SUM(COALESCE(valor_venda,0)),0) as total,
                   COALESCE(AVG(COALESCE(valor_venda,0)),0) as avg_val
            FROM leads
            WHERE user_id = :uid
              AND sdr_stage IN ('reveal','feedback','close','urgency','negotiation','negociacao','handoff','qualified','qualificado')
        """), {"uid": tenant_id}).fetchone()

        active_deals = pipeline_rows[0] if pipeline_rows else 0
        total_pipeline_value = float(pipeline_rows[1] or 0)
        avg_deal_value = float(pipeline_rows[2] or 0)

        # Won: leads ganhos
        won_rows = db.execute(text("""
            SELECT COUNT(*) as cnt, COALESCE(SUM(COALESCE(valor_venda,0)),0) as revenue
            FROM leads
            WHERE user_id = :uid
              AND status = 'concluido'
              AND sdr_stage IN ('won','ganho','convertido')
        """), {"uid": tenant_id}).fetchone()
        won_count = won_rows[0] if won_rows else 0
        won_revenue = float(won_rows[1] or 0)

        # Funnel: contar por sdr_stage (leads concluídos)
        funnel_stages = {
            "total_qualified": "SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='concluido'",
            "intro":       "SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='concluido' AND sdr_stage IN ('qualify','intro')",
            "f1":          "SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='concluido' AND sdr_stage IN ('pain','amplify','followup1','f1','follow_up_1','followup_24h','scheduled')",
            "f2":          "SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='concluido' AND sdr_stage IN ('tease','proof','followup2','f2','follow_up_2','rapport','education','followup_72h')",
            "negotiation": "SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='concluido' AND sdr_stage IN ('reveal','feedback','close','urgency','negotiation','negociacao')",
            "handoff":     "SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='concluido' AND sdr_stage IN ('handoff','qualified','qualificado')",
            "won":         "SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='concluido' AND sdr_stage IN ('won','ganho','convertido')",
            "lost":        "SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='concluido' AND sdr_stage IN ('lost','perdido')",
        }
        funnel = {}
        for key, sql in funnel_stages.items():
            row = db.execute(text(sql), {"uid": tenant_id}).fetchone()
            funnel[key] = row[0] if row else 0

        # Rates (% de cada etapa relativa ao total qualificado)
        tq = funnel.get("total_qualified") or 1  # avoid div/0
        rates = {
            "intro_rate":      round(funnel.get("intro", 0) / tq * 100, 1),
            "f1_rate":         round(funnel.get("f1", 0) / tq * 100, 1),
            "f2_rate":         round(funnel.get("f2", 0) / tq * 100, 1),
            "negotiation_rate":round(funnel.get("negotiation", 0) / tq * 100, 1),
            "handoff_rate":    round(funnel.get("handoff", 0) / tq * 100, 1),
            "won_rate":        round(funnel.get("won", 0) / tq * 100, 1),
            "lost_rate":       round(funnel.get("lost", 0) / tq * 100, 1),
        }

        # Stage distribution (todos os sdr_stage únicos com contagem)
        stage_rows = db.execute(text("""
            SELECT sdr_stage, COUNT(*) as cnt
            FROM leads
            WHERE user_id = :uid AND status = 'concluido' AND sdr_stage IS NOT NULL
            GROUP BY sdr_stage
            ORDER BY cnt DESC
        """), {"uid": tenant_id}).fetchall()
        stage_distribution = {str(r[0]): r[1] for r in stage_rows}

        return {
            "summary": {
                "active_leads": active_leads,
            },
            "pipeline": {
                "active_deals": active_deals,
                "total_pipeline_value": total_pipeline_value,
                "avg_deal_value": avg_deal_value,
            },
            "won": {
                "count": won_count,
                "revenue": won_revenue,
            },
            "rates": rates,
            "funnel": funnel,
            "stage_distribution": stage_distribution,
        }
    except Exception as e:
        print(f"[Dashboard] Erro pipeline-analytics: {e}")
        return {
            "summary": {"active_leads": 0},
            "pipeline": {"active_deals": 0, "total_pipeline_value": 0, "avg_deal_value": 0},
            "won": {"count": 0, "revenue": 0},
            "rates": {},
            "funnel": {},
            "stage_distribution": {},
        }
