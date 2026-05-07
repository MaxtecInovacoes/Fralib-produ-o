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
        falhas = db.execute(text(
            "SELECT id, nome, cidade, segmento, score, status, tentativas FROM leads WHERE status = 'erro' ORDER BY criado_em DESC LIMIT 50"
        )).fetchall()
        descartados = db.execute(text(
            "SELECT id, nome, cidade, segmento, score, status FROM leads WHERE status = 'descartado' ORDER BY criado_em DESC LIMIT 50"
        )).fetchall()
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
        result = db.execute(text(
            "SELECT id, nome, cidade, segmento, telefone, COALESCE(NULLIF(telefone_whatsapp,''), whatsapp, telefone) as telefone_whatsapp, score, status, sdr_stage, url_site, criado_em FROM leads ORDER BY score DESC"
        )).fetchall()

        leads = [dict(r._mapping) for r in result]

        # Mapear status/sdr_stage do banco para colunas do Kanban
        data = {"fila": [], "intro": [], "f1": [], "f2": [], "negotiation": [], "qualificado": [], "lost": [], "won": []}

        for lead in leads:
            status = (lead.get('status') or 'pendente').lower()
            sdr_stage = (lead.get('sdr_stage') or 'intro').lower()

            if status == 'pendente':
                data['fila'].append(lead)
            elif status == 'processando':
                data['fila'].append(lead)
            elif status == 'concluido':
                if sdr_stage == 'intro':
                    data['intro'].append(lead)
                elif sdr_stage in ('followup1', 'f1', 'follow_up_1'):
                    data['f1'].append(lead)
                elif sdr_stage in ('followup2', 'f2', 'follow_up_2', 'rapport', 'education'):
                    data['f2'].append(lead)
                elif sdr_stage in ('negotiation', 'negociacao'):
                    data['negotiation'].append(lead)
                elif sdr_stage in ('qualificado', 'qualified'):
                    data['qualificado'].append(lead)
                elif sdr_stage in ('won', 'ganho', 'convertido'):
                    data['won'].append(lead)
                else:
                    data['intro'].append(lead)
            elif status in ('descartado', 'lost', 'perdido'):
                data['lost'].append(lead)
            elif status in ('convertido', 'won', 'ganho'):
                data['won'].append(lead)
            else:
                data['fila'].append(lead)

        return data
    except Exception as e:
        print(f"[Dashboard] Erro ao carregar CRM: {e}")
        return {"fila": [], "intro": [], "f1": [], "f2": [], "negotiation": [], "qualificado": [], "lost": [], "won": []}
