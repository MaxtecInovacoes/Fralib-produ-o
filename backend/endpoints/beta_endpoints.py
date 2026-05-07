from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
import sys
sys.path.append('/root/fralib/backend')
sys.path.append('/root/fralib/backend/core')
from database import get_db
import uuid
from datetime import datetime

router = APIRouter(prefix='/api/beta', tags=['beta'])

def criar_tabela_se_nao_existe(db: Session):
    db.execute(text('''
        CREATE TABLE IF NOT EXISTS beta_leads (
            id TEXT PRIMARY KEY,
            nome TEXT,
            email TEXT UNIQUE,
            whatsapp TEXT,
            origem TEXT,
            criado_em TEXT
        )
    '''))
    db.commit()

class BetaLeadRequest(BaseModel):
    nome: str
    email: str
    whatsapp: str
    origem: Optional[str] = 'landing'

@router.post('/lead')
async def salvar_beta_lead(req: BetaLeadRequest, db: Session = Depends(get_db)):
    try:
        criar_tabela_se_nao_existe(db)

        existente = db.execute(
            text('SELECT id FROM beta_leads WHERE email = :email'),
            {'email': req.email}
        ).fetchone()

        if existente:
            return {'ok': True, 'mensagem': 'Lead ja cadastrado', 'novo': False}

        lead_id = str(uuid.uuid4())
        agora = datetime.now().isoformat()

        db.execute(text('''
            INSERT INTO beta_leads (id, nome, email, whatsapp, origem, criado_em)
            VALUES (:id, :nome, :email, :whatsapp, :origem, :criado_em)
            ON CONFLICT (email) DO NOTHING
        '''), {
            'id': lead_id,
            'nome': req.nome,
            'email': req.email,
            'whatsapp': req.whatsapp,
            'origem': req.origem,
            'criado_em': agora
        })
        db.commit()

        return {'ok': True, 'mensagem': 'Lead salvo com sucesso', 'novo': True}

    except Exception as e:
        print(f'[BetaLead] Erro: {e}')
        return {'ok': False, 'mensagem': 'Erro ao salvar lead'}

@router.get('/leads')
async def listar_beta_leads(db: Session = Depends(get_db)):
    try:
        criar_tabela_se_nao_existe(db)
        result = db.execute(text('''
            SELECT id, nome, email, whatsapp, origem, criado_em
            FROM beta_leads
            ORDER BY criado_em DESC
        ''')).fetchall()
        leads = [dict(r._mapping) for r in result]
        return {'ok': True, 'total': len(leads), 'leads': leads}
    except Exception as e:
        return {'ok': False, 'leads': [], 'total': 0}
