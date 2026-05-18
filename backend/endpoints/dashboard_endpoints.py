from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import sys

sys.path.append('/root/fralib/backend')
sys.path.append('/root/fralib/backend/core')

from database import get_db
from auth import get_current_user

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
