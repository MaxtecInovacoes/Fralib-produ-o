"""
CRUD de API keys de provedores de IA — restrito a superadmin.

Tabela: provider_keys (criada pela migration provider_keys.py).
Cripto: utils.secrets_crypto (Fernet).
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from auth import get_current_user
from core.config import is_superadmin
from backend.schemas.provider_keys import (
    ProviderKeyCreateRequest,
    ProviderKeyUpdateRequest,
    ProviderKeyTestRequest,
)
from backend.services.provider_keys_service import (
    ALLOWED_PROVIDERS,
    create_provider_key,
    delete_provider_key,
    get_provider_key,
    list_provider_keys,
    reset_provider_cooldown,
    row_to_dict,
    test_provider,
    toggle_provider_key,
)
from utils.secrets_crypto import decriptar


router = APIRouter(prefix='/api/provider-keys', tags=['provider-keys'])


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


# ============================================================
# CRUD
# ============================================================

@router.get('')
def list_keys(db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    rows = list_provider_keys(db)
    return {'ok': True, 'keys': [row_to_dict(r) for r in rows]}


@router.post('')
def create_key(body: ProviderKeyCreateRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    provider = body.provider.strip().lower()
    label = body.label.strip()
    apikey = body.apikey.strip()
    base_url = body.base_url.strip() if body.base_url else None

    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f'Provider invalido. Use: {sorted(ALLOWED_PROVIDERS)}')
    if not label:
        raise HTTPException(status_code=400, detail='Label obrigatorio')
    if not apikey:
        raise HTTPException(status_code=400, detail='API key obrigatoria')
    if provider == 'custom' and not base_url:
        raise HTTPException(status_code=400, detail='base_url obrigatorio para provider custom')

    try:
        new_id = create_provider_key(db, provider, label, apikey, base_url, user.get('id'))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Erro ao gravar: {e}')

    _audit(db, user, 'provider_key_create', target_id=new_id,
           metadata={'provider': provider, 'label': label, 'apikey_masked': mascarar_key(apikey)},
           request=request)
    return {'ok': True, 'id': new_id}


@router.put('/{key_id}')
def update_key(key_id: int, body: ProviderKeyUpdateRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    existing = get_provider_key(db, key_id)
    if not existing:
        raise HTTPException(status_code=404, detail='Key nao encontrada')

    updates = []
    params = {'id': key_id}
    audit_meta = {}

    if body.label is not None:
        label = body.label.strip()
        if not label:
            raise HTTPException(status_code=400, detail='Label nao pode ser vazio')
        updates.append('label = :label')
        params['label'] = label
        audit_meta['label'] = label

    if body.apikey:
        apikey = body.apikey.strip()
        updates.append('encrypted_key = :enc')
        from utils.secrets_crypto import encriptar, mascarar_key
        params['enc'] = encriptar(apikey)
        # zera cooldown ao trocar key (assumimos que a nova precisa ser testada)
        updates.append('cooldown_until = NULL')
        updates.append('last_error = NULL')
        audit_meta['apikey_rotated'] = True
        audit_meta['apikey_masked'] = mascarar_key(apikey)

    if body.base_url is not None:
        base_url = body.base_url.strip() or None
        if existing[1] == 'custom' and not base_url:
            raise HTTPException(status_code=400, detail='base_url obrigatorio para provider custom')
        updates.append('base_url = :burl')
        params['burl'] = base_url
        audit_meta['base_url'] = base_url

    if body.enabled is not None:
        updates.append('enabled = :en')
        params['en'] = bool(body.enabled)
        audit_meta['enabled'] = bool(body.enabled)

    if not updates:
        raise HTTPException(status_code=400, detail='Nada para atualizar')

    updates.append('atualizado_em = NOW()')
    try:
        from backend.services.provider_keys_service import update_provider_key
        update_provider_key(db, key_id, {"sql": updates, "params": params})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Erro ao atualizar: {e}')

    _audit(db, user, 'provider_key_update', target_id=key_id, metadata=audit_meta, request=request)
    return {'ok': True, 'id': key_id}


@router.delete('/{key_id}')
def delete_key(key_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    row = delete_provider_key(db, key_id)
    if not row:
        raise HTTPException(status_code=404, detail='Key nao encontrada')

    _audit(db, user, 'provider_key_delete', target_id=key_id,
           metadata={'provider': row[0], 'label': row[1]}, request=request)
    return {'ok': True, 'id': key_id}


@router.post('/{key_id}/toggle')
def toggle_key(key_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    row = db.execute(text("SELECT enabled FROM provider_keys WHERE id = :id"),
                     {'id': key_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Key nao encontrada')
    new_state = toggle_provider_key(db, key_id)
    _audit(db, user, 'provider_key_toggle', target_id=key_id, metadata={'enabled': new_state}, request=request)
    return {'ok': True, 'enabled': new_state}


@router.post('/{key_id}/reset-cooldown')
def reset_cooldown(key_id: int, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    row = db.execute(text("SELECT id FROM provider_keys WHERE id = :id"), {'id': key_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Key nao encontrada')
    reset_provider_cooldown(db, key_id)
    _audit(db, user, 'provider_key_reset_cooldown', target_id=key_id, request=request)
    return {'ok': True, 'id': key_id}


# ============================================================
# Teste de conexao
# ============================================================

@router.post('/test')
def test_unsaved(body: ProviderKeyTestRequest, user: dict = Depends(require_superadmin)):
    """Testa uma key SEM salvar (botao 'Testar conexao' no modal)."""
    provider = body.provider.strip().lower()
    apikey = body.apikey.strip()
    base_url = body.base_url.strip() if body.base_url else None
    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail='Provider invalido')
    if not apikey:
        raise HTTPException(status_code=400, detail='API key obrigatoria')
    return test_provider(provider, apikey, base_url)


@router.post('/{key_id}/test')
def test_saved(key_id: int, db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Testa uma key JA cadastrada."""
    row = db.execute(text(
        "SELECT provider, encrypted_key, base_url FROM provider_keys WHERE id = :id"
    ), {'id': key_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Key nao encontrada')
    plain = decriptar(row[1])
    if not plain:
        return {'ok': False, 'error': 'falha ao decriptar (FERNET_KEY trocada?)'}
    return test_provider(row[0], plain, row[2])
