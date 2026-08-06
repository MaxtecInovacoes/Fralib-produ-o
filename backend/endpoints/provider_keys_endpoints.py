"""
CRUD de API keys de provedores de IA — restrito a superadmin.

Tabela: provider_keys (criada pela migration provider_keys.py).
Cripto: utils.secrets_crypto (Fernet).
"""
import time
import json
import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from auth import get_current_user
from core.config import is_superadmin
from utils.secrets_crypto import encriptar, decriptar, mascarar_key


router = APIRouter(prefix='/api/provider-keys', tags=['provider-keys'])

ALLOWED_PROVIDERS = {'anthropic', 'openai', 'google', 'groq', 'custom'}


def require_superadmin(user: dict = Depends(get_current_user)):
    if not is_superadmin(user.get('email', '')):
        raise HTTPException(status_code=403, detail='Acesso negado: Super Admin apenas')
    return user


def _audit(db, actor, action, target_id=None, metadata=None, request=None):
    try:
        db.execute(text("""
            INSERT INTO audit_log (actor_id, action, target_type, target_id, metadata, ip, user_agent)
            VALUES (:actor, :action, 'provider_key', :target_id, CAST(:meta AS JSONB), :ip, :ua)
        """), {
            'actor': actor.get('id'),
            'action': action,
            'target_id': str(target_id) if target_id is not None else None,
            'meta': json.dumps(metadata or {}),
            'ip': (request.client.host if request and request.client else None),
            'ua': (request.headers.get('user-agent') if request else None),
        })
        db.commit()
    except Exception as e:
        print(f'[audit_log] falha em {action}: {e}')
        try:
            db.rollback()
        except Exception:
            pass


def _row_to_dict(r) -> dict:
    """Converte linha do SELECT em dict seguro pra cliente. Mascarando a key."""
    # r: (id, provider, label, encrypted_key, base_url, enabled, cooldown_until,
    #     last_error, last_used_at, success_count, failure_count, criado_em)
    plain = decriptar(r[3])
    return {
        'id': r[0],
        'provider': r[1],
        'label': r[2],
        'apikey_masked': mascarar_key(plain),
        'base_url': r[4] or '',
        'enabled': bool(r[5]),
        'cooldown_until': r[6].isoformat() if r[6] else None,
        'in_cooldown': bool(r[6]) and r[6].timestamp() > time.time() if r[6] else False,
        'last_error': r[7] or '',
        'last_used_at': r[8].isoformat() if r[8] else None,
        'success_count': r[9] or 0,
        'failure_count': r[10] or 0,
        'criado_em': r[11].isoformat() if r[11] else None,
    }


# ============================================================
# CRUD
# ============================================================

@router.get('')
async def list_keys(db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    rows = db.execute(text("""
        SELECT id, provider, label, encrypted_key, base_url, enabled,
               cooldown_until, last_error, last_used_at,
               success_count, failure_count, criado_em
        FROM provider_keys
        ORDER BY provider, id
    """)).fetchall()
    return {'ok': True, 'keys': [_row_to_dict(r) for r in rows]}


@router.post('')
async def create_key(request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    body = await request.json()
    provider = (body.get('provider') or '').strip().lower()
    label = (body.get('label') or '').strip()
    apikey = (body.get('apikey') or '').strip()
    base_url = (body.get('base_url') or '').strip() or None

    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f'Provider invalido. Use: {sorted(ALLOWED_PROVIDERS)}')
    if not label:
        raise HTTPException(status_code=400, detail='Label obrigatorio')
    if not apikey:
        raise HTTPException(status_code=400, detail='API key obrigatoria')
    if provider == 'custom' and not base_url:
        raise HTTPException(status_code=400, detail='base_url obrigatorio para provider custom')

    enc = encriptar(apikey)
    try:
        row = db.execute(text("""
            INSERT INTO provider_keys (provider, label, encrypted_key, base_url, criado_por)
            VALUES (:p, :l, :e, :b, :u)
            RETURNING id
        """), {'p': provider, 'l': label, 'e': enc, 'b': base_url, 'u': user.get('id')}).fetchone()
        db.commit()
        new_id = row[0]
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Erro ao gravar: {e}')

    _audit(db, user, 'provider_key_create', target_id=new_id,
           metadata={'provider': provider, 'label': label, 'apikey_masked': mascarar_key(apikey)},
           request=request)
    return {'ok': True, 'id': new_id}


@router.put('/{key_id}')
async def update_key(key_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    body = await request.json()

    existing = db.execute(text("SELECT id, provider FROM provider_keys WHERE id = :id"),
                          {'id': key_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail='Key nao encontrada')

    updates = []
    params = {'id': key_id}
    audit_meta = {}

    if 'label' in body:
        label = (body.get('label') or '').strip()
        if not label:
            raise HTTPException(status_code=400, detail='Label nao pode ser vazio')
        updates.append('label = :label')
        params['label'] = label
        audit_meta['label'] = label

    if 'apikey' in body and body.get('apikey'):
        apikey = body['apikey'].strip()
        updates.append('encrypted_key = :enc')
        params['enc'] = encriptar(apikey)
        # zera cooldown ao trocar key (assumimos que a nova precisa ser testada)
        updates.append('cooldown_until = NULL')
        updates.append('last_error = NULL')
        audit_meta['apikey_rotated'] = True
        audit_meta['apikey_masked'] = mascarar_key(apikey)

    if 'base_url' in body:
        base_url = (body.get('base_url') or '').strip() or None
        if existing[1] == 'custom' and not base_url:
            raise HTTPException(status_code=400, detail='base_url obrigatorio para provider custom')
        updates.append('base_url = :burl')
        params['burl'] = base_url
        audit_meta['base_url'] = base_url

    if 'enabled' in body:
        updates.append('enabled = :en')
        params['en'] = bool(body.get('enabled'))
        audit_meta['enabled'] = bool(body.get('enabled'))

    if not updates:
        raise HTTPException(status_code=400, detail='Nada para atualizar')

    updates.append('atualizado_em = NOW()')
    try:
        db.execute(text(f"UPDATE provider_keys SET {', '.join(updates)} WHERE id = :id"), params)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Erro ao atualizar: {e}')

    _audit(db, user, 'provider_key_update', target_id=key_id, metadata=audit_meta, request=request)
    return {'ok': True, 'id': key_id}


@router.delete('/{key_id}')
async def delete_key(key_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    row = db.execute(text("SELECT provider, label FROM provider_keys WHERE id = :id"),
                     {'id': key_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Key nao encontrada')
    try:
        db.execute(text("DELETE FROM provider_keys WHERE id = :id"), {'id': key_id})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Erro ao excluir: {e}')

    _audit(db, user, 'provider_key_delete', target_id=key_id,
           metadata={'provider': row[0], 'label': row[1]}, request=request)
    return {'ok': True, 'id': key_id}


@router.post('/{key_id}/toggle')
async def toggle_key(key_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    row = db.execute(text("SELECT enabled FROM provider_keys WHERE id = :id"),
                     {'id': key_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Key nao encontrada')
    new_state = not bool(row[0])
    try:
        db.execute(text("UPDATE provider_keys SET enabled = :en, atualizado_em = NOW() WHERE id = :id"),
                   {'en': new_state, 'id': key_id})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    _audit(db, user, 'provider_key_toggle', target_id=key_id, metadata={'enabled': new_state}, request=request)
    return {'ok': True, 'enabled': new_state}


@router.post('/{key_id}/reset-cooldown')
async def reset_cooldown(key_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    row = db.execute(text("SELECT id FROM provider_keys WHERE id = :id"), {'id': key_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Key nao encontrada')
    try:
        db.execute(text("""
            UPDATE provider_keys SET cooldown_until = NULL, last_error = NULL, atualizado_em = NOW()
            WHERE id = :id
        """), {'id': key_id})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    _audit(db, user, 'provider_key_reset_cooldown', target_id=key_id, request=request)
    return {'ok': True, 'id': key_id}


# ============================================================
# Teste de conexao
# ============================================================

def _test_provider(provider: str, apikey: str, base_url: str | None) -> dict:
    """Faz uma chamada minimal pra validar key+base_url. Nao persiste nada."""
    t0 = time.time()
    try:
        if provider == 'anthropic':
            url = (base_url or 'https://api.anthropic.com').rstrip('/') + '/v1/messages'
            r = requests.post(url, timeout=10, json={
                'model': 'claude-haiku-4-5',
                'max_tokens': 1,
                'messages': [{'role': 'user', 'content': 'hi'}],
            }, headers={
                'x-api-key': apikey,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json',
            })
        elif provider == 'openai':
            url = (base_url or 'https://api.openai.com/v1').rstrip('/') + '/chat/completions'
            r = requests.post(url, timeout=10, json={
                'model': 'gpt-4o-mini',
                'max_tokens': 1,
                'messages': [{'role': 'user', 'content': 'hi'}],
            }, headers={
                'Authorization': f'Bearer {apikey}',
                'Content-Type': 'application/json',
            })
        elif provider == 'google':
            base = (base_url or 'https://generativelanguage.googleapis.com/v1beta').rstrip('/')
            url = f'{base}/models/gemini-2.0-flash:generateContent?key={apikey}'
            r = requests.post(url, timeout=10, json={
                'contents': [{'parts': [{'text': 'hi'}]}],
                'generationConfig': {'maxOutputTokens': 1},
            }, headers={'Content-Type': 'application/json'})
        elif provider == 'custom':
            if not base_url:
                return {'ok': False, 'error': 'base_url obrigatorio para custom'}
            url = base_url.rstrip('/') + '/chat/completions'
            r = requests.post(url, timeout=10, json={
                'model': 'gpt-3.5-turbo',
                'max_tokens': 1,
                'messages': [{'role': 'user', 'content': 'hi'}],
            }, headers={
                'Authorization': f'Bearer {apikey}',
                'Content-Type': 'application/json',
            })
        elif provider == 'groq':
            url = (base_url or 'https://api.groq.com/openai/v1').rstrip('/') + '/chat/completions'
            r = requests.post(url, timeout=10, json={
                'model': 'llama-3.1-8b-instant',
                'max_tokens': 1,
                'messages': [{'role': 'user', 'content': 'hi'}],
            }, headers={
                'Authorization': f'Bearer {apikey}',
                'Content-Type': 'application/json',
            })
        else:
            return {'ok': False, 'error': 'provider invalido'}
        return {'ok': False, 'error': 'timeout (10s)'}
    except requests.ConnectionError:
        return {'ok': False, 'error': 'network (host inacessivel)'}
    except Exception as e:
        return {'ok': False, 'error': f'erro: {type(e).__name__}'}

    latency_ms = int((time.time() - t0) * 1000)
    if 200 <= r.status_code < 300:
        return {'ok': True, 'latency_ms': latency_ms, 'status': r.status_code}
    # Mapeia codigos sem vazar payload
    msg = {
        400: '400 requisicao invalida (modelo/payload nao aceito)',
        401: '401 nao autorizado (key invalida)',
        403: '403 proibido (key sem permissao)',
        404: '404 endpoint nao encontrado (base_url errada?)',
        429: '429 rate limit',
    }.get(r.status_code, f'{r.status_code} erro')
    return {'ok': False, 'error': msg, 'latency_ms': latency_ms, 'status': r.status_code}


@router.post('/test')
async def test_unsaved(request: Request, user: dict = Depends(require_superadmin)):
    """Testa uma key SEM salvar (botao 'Testar conexao' no modal)."""
    body = await request.json()
    provider = (body.get('provider') or '').strip().lower()
    apikey = (body.get('apikey') or '').strip()
    base_url = (body.get('base_url') or '').strip() or None
    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail='Provider invalido')
    if not apikey:
        raise HTTPException(status_code=400, detail='API key obrigatoria')
    return _test_provider(provider, apikey, base_url)


@router.post('/{key_id}/test')
async def test_saved(key_id: int, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Testa uma key JA cadastrada."""
    row = db.execute(text(
        "SELECT provider, encrypted_key, base_url FROM provider_keys WHERE id = :id"
    ), {'id': key_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Key nao encontrada')
    plain = decriptar(row[1])
    if not plain:
        return {'ok': False, 'error': 'falha ao decriptar (FERNET_KEY trocada?)'}
    return _test_provider(row[0], plain, row[2])
