"""
Alertas de provider keys — restrito a superadmin.

Eventos sao gravados pelo ia_manager (rate_limit, key_invalid, all_keys_failed,
test_failed). Este modulo so expoe leitura e gestao (marcar lido / deletar).
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from core.config import is_superadmin


router = APIRouter(prefix='/api/provider-alerts', tags=['provider-alerts'])


def require_superadmin(user: dict = Depends(get_current_user)):
    if not is_superadmin(user.get('email', '')):
        raise HTTPException(status_code=403, detail='Acesso negado: Super Admin apenas')
    return user


def _audit(db, actor, action, target_id=None, metadata=None, request=None):
    try:
        db.execute(text("""
            INSERT INTO audit_log (actor_id, action, target_type, target_id, metadata, ip, user_agent)
            VALUES (:actor, :action, 'provider_alert', :target_id, CAST(:meta AS JSONB), :ip, :ua)
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
        print(f'[audit] falha {action}: {e}')
        try:
            db.rollback()
        except Exception as rollback_err:
            print(f'[audit] rollback falhou: {rollback_err}')


@router.get('')
async def list_alerts(only_unread: bool = False, limit: int = 100,
                      db: Session = Depends(get_db),
                      user: dict = Depends(require_superadmin)):
    """Lista alertas, mais recentes primeiro. ?only_unread=true filtra so nao-lidos."""
    where = 'WHERE NOT lido' if only_unread else ''
    rows = db.execute(text(f"""
        SELECT a.id, a.tipo, a.key_id, a.mensagem, a.lead_id, a.user_id_afetado,
               a.lido, a.criado_em, a.lido_em,
               pk.label AS key_label, pk.provider AS key_provider,
               u.email AS user_email,
               l.nome AS lead_nome
        FROM provider_alerts a
        LEFT JOIN provider_keys pk ON pk.id = a.key_id
        LEFT JOIN users u          ON u.id = a.user_id_afetado
        LEFT JOIN leads l          ON l.id = a.lead_id
        {where}
        ORDER BY a.criado_em DESC
        LIMIT :lim
    """), {'lim': max(1, min(int(limit), 500))}).fetchall()

    alerts = []
    for r in rows:
        alerts.append({
            'id': r[0],
            'tipo': r[1],
            'key_id': r[2],
            'mensagem': r[3],
            'lead_id': r[4],
            'user_id_afetado': r[5],
            'lido': bool(r[6]),
            'criado_em': r[7].isoformat() if r[7] else None,
            'lido_em': r[8].isoformat() if r[8] else None,
            'key_label': r[9] or '',
            'key_provider': r[10] or '',
            'user_email': r[11] or '',
            'lead_nome': r[12] or '',
        })

    # Contador rapido de nao-lidos pro badge do sino
    unread = db.execute(text("SELECT COUNT(*) FROM provider_alerts WHERE NOT lido")).scalar() or 0

    return {'ok': True, 'alerts': alerts, 'unread': int(unread)}


@router.get('/unread-count')
async def unread_count(db: Session = Depends(get_db), user: dict = Depends(require_superadmin)):
    """Endpoint barato para poll do sino."""
    c = db.execute(text("SELECT COUNT(*) FROM provider_alerts WHERE NOT lido")).scalar() or 0
    return {'ok': True, 'unread': int(c)}


@router.post('/{alert_id}/read')
async def mark_read(alert_id: int, request: Request,
                    db: Session = Depends(get_db),
                    user: dict = Depends(require_superadmin)):
    row = db.execute(text("SELECT id, lido FROM provider_alerts WHERE id = :id"),
                     {'id': alert_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Alerta nao encontrado')
    if row[1]:
        return {'ok': True, 'already_read': True}
    db.execute(text("UPDATE provider_alerts SET lido = TRUE, lido_em = NOW() WHERE id = :id"),
               {'id': alert_id})
    db.commit()
    _audit(db, user, 'provider_alert_read', target_id=alert_id, request=request)
    return {'ok': True}


@router.post('/read-all')
async def mark_all_read(request: Request, db: Session = Depends(get_db),
                        user: dict = Depends(require_superadmin)):
    res = db.execute(text("""
        UPDATE provider_alerts SET lido = TRUE, lido_em = NOW()
        WHERE NOT lido
    """))
    db.commit()
    _audit(db, user, 'provider_alert_read_all', metadata={'rows': res.rowcount}, request=request)
    return {'ok': True, 'marked': res.rowcount}


@router.delete('/{alert_id}')
async def delete_alert(alert_id: int, request: Request,
                       db: Session = Depends(get_db),
                       user: dict = Depends(require_superadmin)):
    row = db.execute(text("SELECT id FROM provider_alerts WHERE id = :id"),
                     {'id': alert_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Alerta nao encontrado')
    db.execute(text("DELETE FROM provider_alerts WHERE id = :id"), {'id': alert_id})
    db.commit()
    _audit(db, user, 'provider_alert_delete', target_id=alert_id, request=request)
    return {'ok': True}


@router.delete('')
async def delete_all_read(db: Session = Depends(get_db),
                          user: dict = Depends(require_superadmin),
                          request: Request = None):
    """Limpa todos os alertas ja lidos."""
    res = db.execute(text("DELETE FROM provider_alerts WHERE lido = TRUE"))
    db.commit()
    _audit(db, user, 'provider_alert_delete_all_read', metadata={'rows': res.rowcount}, request=request)
    return {'ok': True, 'deleted': res.rowcount}
