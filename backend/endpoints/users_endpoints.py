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

_WPP_CONNECTED_STATES = ("connected", "open", "authenticated")


async def _check_whatsapp_connected(user_id: int) -> bool:
    """Checa se o WhatsApp do user esta conectado no meowhats.

    Tem dois caminhos: rota direta /api/sessions/{tenant}/status e fallback
    listando todas as sessoes. Timeout maior (8s) + 1 retry para evitar
    falso 'desconectado' quando o meowhats demora a responder.
    """
    import httpx, asyncio, logging
    _log = logging.getLogger(__name__)

    meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001")
    meowhats_key = os.getenv("MEOWHATS_KEY", "1763kovQ@")
    tenant_id = f"fralib_user_{user_id}"
    headers = {"X-API-Key": meowhats_key}

    async def _try_direct():
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"{meowhats_url}/api/sessions/{tenant_id}/status", headers=headers)
            if r.status_code == 200:
                return r.json().get("status") in _WPP_CONNECTED_STATES
            return None

    async def _try_list():
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"{meowhats_url}/api/sessions", headers=headers)
            if r.status_code == 200:
                for s in r.json():
                    if s.get("tenantId") == tenant_id or s.get("id") == tenant_id:
                        return s.get("status") in _WPP_CONNECTED_STATES
                return False
            return None

    for tentativa in (1, 2):
        try:
            v = await _try_direct()
            if v is True:
                return True
            if v is False:
                # rota direta confirmou desconectado — tenta listar antes de aceitar
                v2 = await _try_list()
                if v2 is True:
                    return True
                if v2 is False:
                    return False
                # listar nao respondeu — segue retry
            # v is None (status != 200) — tenta listar
            v2 = await _try_list()
            if v2 is not None:
                return bool(v2)
        except Exception as e:
            _log.warning(f"[wpp_check] user={user_id} tentativa={tentativa} erro={e}")
            if tentativa == 1:
                await asyncio.sleep(0.4)
                continue

    return False

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

_ALLOWED_PROFILE_FIELDS = {
    "nome", "telefone", "endereco", "nicho", "origem",
    "cep", "rua", "bairro", "cidade", "estado",
}

@router.put("/profile")
async def update_profile(data: UserProfileUpdate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    user_id = user["id"]
    update_data = data.model_dump(exclude_unset=True)

    update_data = {k: v for k, v in update_data.items() if k in _ALLOWED_PROFILE_FIELDS}

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

    # Verificar WhatsApp conectado — 2 caminhos com fallback + retry
    wpp_ok = await _check_whatsapp_connected(user_id)

    # Verificar se tem lead demo
    lead_demo = db.execute(text(
        "SELECT id FROM leads WHERE user_id=:uid AND status='demo' LIMIT 1"
    ), {"uid": user_id}).fetchone()

    # PR9: ja rodou pelo menos um pipeline real (lead concluido nao-demo)?
    pipeline_ok_row = db.execute(text(
        "SELECT 1 FROM leads WHERE user_id=:uid AND status='concluido' "
        "AND (status IS DISTINCT FROM 'demo') LIMIT 1"
    ), {"uid": user_id}).fetchone()
    pipeline_ok = bool(pipeline_ok_row)

    return {
        "perfil_ok": perfil_ok,
        "wpp_ok": wpp_ok,
        "pipeline_ok": pipeline_ok,
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


# ─── PR8: BYOK Anthropic (plano Pro) ─────────────────────────────────
class AnthropicKeyRequest(BaseModel):
    api_key: str


@router.get('/anthropic-key/status')
async def status_anthropic_key(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Retorna se o usuario ja configurou a key e um hint (sem expor)."""
    from utils.secrets_crypto import decriptar, mascarar_key
    row = db.execute(text(
        'SELECT plano, anthropic_key_encrypted FROM users WHERE id=:id'
    ), {'id': user['id']}).fetchone()
    if not row:
        raise HTTPException(404, 'Usuario nao encontrado')
    plano = (row[0] or '').lower()
    enc = row[1] or ''
    if not enc:
        return {'configurada': False, 'hint': '', 'plano': plano}
    plain = decriptar(enc)
    return {'configurada': bool(plain), 'hint': mascarar_key(plain), 'plano': plano}


@router.put('/anthropic-key')
async def salvar_anthropic_key(
    body: AnthropicKeyRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Salva a Anthropic API key (criptografada). So plano=pro pode."""
    from utils.secrets_crypto import encriptar
    row = db.execute(text('SELECT plano FROM users WHERE id=:id'), {'id': user['id']}).fetchone()
    if not row:
        raise HTTPException(404, 'Usuario nao encontrado')
    if (row[0] or '').lower() != 'pro':
        raise HTTPException(403, 'BYOK disponivel apenas no plano Pro')
    key = (body.api_key or '').strip()
    if not key.startswith('sk-ant-') or len(key) < 30:
        raise HTTPException(400, 'API key invalida. Deve comecar com sk-ant- e ter ao menos 30 chars.')
    enc = encriptar(key)
    db.execute(text('UPDATE users SET anthropic_key_encrypted=:k WHERE id=:id'),
               {'k': enc, 'id': user['id']})
    db.commit()
    try:
        from agents.llm_direct import invalidar_byok_cache
        invalidar_byok_cache(user['id'])
    except Exception:
        pass
    return {'status': 'ok'}


@router.delete('/anthropic-key')
async def remover_anthropic_key(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    db.execute(text('UPDATE users SET anthropic_key_encrypted=NULL WHERE id=:id'),
               {'id': user['id']})
    db.commit()
    try:
        from agents.llm_direct import invalidar_byok_cache
        invalidar_byok_cache(user['id'])
    except Exception:
        pass
    return {'status': 'ok'}
