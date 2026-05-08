from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any
from pydantic import BaseModel

import sys
import os

# Adicionar caminhos para importar os módulos core
sys.path.append('/root/fralib/backend')
sys.path.append('/root/fralib/backend/core')

from core.database import get_db
from core.auth import get_current_user

router = APIRouter(prefix='/api/users', tags=['users'])

class UserProfileUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    nicho: Optional[str] = None
    origem: Optional[str] = None
    cep: Optional[str] = None
    rua: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None

@router.get("/profile")
async def get_profile(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    user_id = user["id"]
    query = text("SELECT id, email, nome, telefone, endereco, nicho, origem, cep, rua, bairro, cidade, estado FROM users WHERE id = :user_id")
    result = db.execute(query, {"user_id": user_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    return dict(result._mapping)

@router.put("/profile")
async def update_profile(data: UserProfileUpdate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    user_id = user["id"]
    update_data = data.model_dump(exclude_unset=True)
    
    if not update_data:
        return {"status": "ok", "mensagem": "Nenhum dado para atualizar"}
        
    set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
    query = text(f"UPDATE users SET {set_clause} WHERE id = :user_id")
    
    db.execute(query, {**update_data, "user_id": user_id})
    db.commit()
    
    return {"status": "ok", "mensagem": "Perfil atualizado com sucesso"}


@router.get("/onboarding-status")
async def onboarding_status(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    import httpx, os
    user_id = user["id"]
    row = db.execute(text(
        "SELECT nome, telefone, nicho, plano, creditos, creditos_max, trial_expires_at FROM users WHERE id=:id"
    ), {"id": user_id}).fetchone()
    if not row:
        raise HTTPException(404, "Usuario nao encontrado")

    perfil_ok = bool(row[0] and row[2])  # nome + nicho preenchidos

    # Verificar WhatsApp conectado
    wpp_ok = False
    try:
        meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001")
        meowhats_key = os.getenv("MEOWHATS_KEY", "1763kovQ@")
        async with httpx.AsyncClient(timeout=3) as c:
            tenant_id = f"fralib_user_{user_id}"
            r = await c.get(f"{meowhats_url}/api/sessions/{tenant_id}/status", headers={"X-API-Key": meowhats_key})
            if r.status_code == 200:
                data = r.json()
                wpp_ok = data.get("status") in ("connected", "open", "authenticated")
    except Exception:
        pass

    # Verificar se tem lead demo
    lead_demo = db.execute(text(
        "SELECT id FROM leads WHERE user_id=:uid AND status='demo' LIMIT 1"
    ), {"uid": user_id}).fetchone()

    return {
        "perfil_ok": perfil_ok,
        "wpp_ok": wpp_ok,
        "plano": row[3],
        "creditos": row[4],
        "creditos_max": row[5],
        "trial_expires_at": row[6],
        "tem_lead_demo": bool(lead_demo),
    }


@router.post("/criar-lead-demo")
async def criar_lead_demo(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    import uuid
    from datetime import datetime
    user_id = user["id"]

    # Verificar se ja tem lead demo
    existing = db.execute(text(
        "SELECT id FROM leads WHERE user_id=:uid AND status='demo' LIMIT 1"
    ), {"uid": user_id}).fetchone()
    if existing:
        return {"status": "ok", "mensagem": "Lead demo ja existe", "lead_id": existing[0]}

    lead_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    db.execute(text("""
        INSERT INTO leads (id, nome, cidade, segmento, telefone, whatsapp, telefone_whatsapp,
            score, status, criado_em, atualizado_em, processado, tentativas, user_id,
            url_site, observacoes)
        VALUES (:id, :nome, :cidade, :seg, :tel, :tel, :tel,
            85, 'demo', :now, :now, false, 0, :uid,
            NULL, 'Lead de demonstracao — assine um plano para gerar leads reais')
    """), {
        "id": lead_id,
        "nome": "Academia Exemplo (DEMO)",
        "cidade": "São Paulo",
        "seg": "Academia",
        "tel": "(11) 99999-0000",
        "now": now,
        "uid": user_id,
    })
    db.commit()
    return {"status": "ok", "mensagem": "Lead demo criado", "lead_id": lead_id}
