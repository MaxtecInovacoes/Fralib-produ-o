from fastapi import APIRouter, Request, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
import os, stripe
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

from auth import get_current_user
from database import get_db

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

PRICE_STARTER = os.getenv('STRIPE_PRICE_STARTER', '')
PRICE_PRO     = os.getenv('STRIPE_PRICE_PRO', '')
PRICE_TOKENS  = os.getenv('STRIPE_PRICE_TOKENS', '')

PLANOS = {
    'starter': {'creditos_max': 5,  'price_id': PRICE_STARTER, 'mode': 'subscription'},
    'pro':     {'creditos_max': 20, 'price_id': PRICE_PRO,     'mode': 'subscription'},
    'tokens':  {'creditos_max': 10, 'price_id': PRICE_TOKENS,  'mode': 'payment'},
}

router = APIRouter(prefix='/api/credits', tags=['credits'])


class CheckoutRequest(BaseModel):
    plano: str  # 'starter' ou 'pro'


@router.post('/criar-checkout')
async def criar_checkout(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    plano = body.plano.lower()
    if plano not in PLANOS:
        raise HTTPException(400, f'Plano invalido: {plano}. Use starter ou pro.')

    price_id = PLANOS[plano]['price_id']
    if not price_id:
        raise HTTPException(500, f'STRIPE_PRICE_{plano.upper()} nao configurado no .env')

    mode = PLANOS[plano]['mode']
    session = stripe.checkout.Session.create(
        mode=mode,
        line_items=[{'price': price_id, 'quantity': 1}],
        metadata={'user_id': str(usuario['id']), 'plano': plano},
        customer_email=usuario.get('email'),
        success_url=os.getenv('APP_URL', 'https://fralib.com') + '/dashboard?upgrade=ok',
        cancel_url=os.getenv('APP_URL', 'https://fralib.com') + '/planos?cancel=1',
    )
    return {'checkout_url': session.url}


@router.get('/status')
async def get_status(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    row = db.execute(text(
        'SELECT plano, creditos, creditos_max, plano_pago, trial_expires_at FROM users WHERE id=:id'
    ), {'id': usuario['id']}).fetchone()
    if not row:
        raise HTTPException(404, 'Usuario nao encontrado')
    return {
        'plano': row[0],
        'creditos': row[1],
        'creditos_max': row[2],
        'plano_pago': row[3],
        'trial_expires_at': row[4],
    }


@router.post('/webhook/stripe')
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias='stripe-signature')
):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(400, 'Webhook invalido')

    if event['type'] in ('checkout.session.completed', 'invoice.payment_succeeded'):
        session = event['data']['object']
        meta = session.get('metadata') or {}
        user_id = meta.get('user_id')
        plano = meta.get('plano', 'starter')
        customer_email = session.get('customer_email') or session.get('customer_details', {}).get('email', '')
        stripe_customer_id = session.get('customer', '')
        stripe_subscription_id = session.get('subscription', '')

        from database import engine
        with engine.connect() as conn:
            if not user_id:
                row = conn.execute(text('SELECT id FROM users WHERE email=:e'), {'e': customer_email}).fetchone()
                if row:
                    user_id = str(row[0])

            if not user_id:
                print(f'Webhook: usuario nao encontrado para {customer_email}')
                return {'status': 'ignored'}

            if plano == 'tokens':
                # Compra avulsa: apenas adiciona creditos, nao muda plano
                bonus = PLANOS['tokens']['creditos_max']
                conn.execute(text('''
                    UPDATE users SET creditos = creditos + :bonus,
                        stripe_customer_id=:cid
                    WHERE id=:uid
                '''), {'bonus': bonus, 'cid': stripe_customer_id, 'uid': int(user_id)})
                conn.commit()
                print(f'Webhook tokens OK: user {user_id} -> +{bonus} creditos')
            else:
                creditos_max = PLANOS.get(plano, {}).get('creditos_max', 5)
                plan_expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
                conn.execute(text('''
                    UPDATE users SET
                        plano=:plano, plan=:plano, plano_pago=true, status='ativo',
                        stripe_customer_id=:cid, stripe_subscription_id=:sid,
                        creditos=:cmax, creditos_max=:cmax,
                        plan_expires_at=:exp
                    WHERE id=:uid
                '''), {
                    'plano': plano, 'cid': stripe_customer_id, 'sid': stripe_subscription_id,
                    'cmax': creditos_max, 'exp': plan_expires_at, 'uid': int(user_id)
                })
                conn.commit()
                print(f'Webhook OK: user {user_id} -> plano {plano}, creditos {creditos_max}')

    elif event['type'] == 'customer.subscription.deleted':
        session = event['data']['object']
        stripe_customer_id = session.get('customer', '')
        if stripe_customer_id:
            from database import engine
            with engine.connect() as conn:
                conn.execute(text('''
                    UPDATE users SET plano='trial', plan='trial', plano_pago=false,
                        creditos=0, creditos_max=1
                    WHERE stripe_customer_id=:cid
                '''), {'cid': stripe_customer_id})
                conn.commit()
                print(f'Webhook: assinatura cancelada para customer {stripe_customer_id}')

    return {'status': 'ok'}


@router.get('/balance')
async def credits_balance(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Retorna saldo de creditos do usuario - compatibilidade admin.html"""
    row = db.execute(text(
        "SELECT creditos, creditos_max, plano, plan_expires_at, trial_expires_at FROM users WHERE id=:id"
    ), {"id": usuario["id"]}).fetchone()
    if not row:
        raise HTTPException(404, "Usuario nao encontrado")
    return {
        "creditos_disponiveis": row[0] or 0,
        "creditos_max": row[1] or 0,
        "plano": row[2] or "trial",
        "plan_expires_at": row[3],
        "trial_expires_at": row[4],
    }


@router.get('/check')
async def credits_check(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Verifica se usuario pode iniciar pipeline"""
    row = db.execute(text(
        "SELECT creditos, creditos_max, plano FROM users WHERE id=:id"
    ), {"id": usuario["id"]}).fetchone()
    if not row:
        raise HTTPException(404, "Usuario nao encontrado")
    creditos = row[0] or 0
    plano = row[2] or "trial"
    can_proceed = creditos > 0
    alert = None
    if creditos == 1:
        alert = "Ultimo ciclo disponivel. Considere fazer upgrade."
    return {
        "can_proceed": can_proceed,
        "creditos": creditos,
        "creditos_max": row[1] or 0,
        "plano": plano,
        "alert": alert,
        "tokens_restantes": creditos,
        "reset_em": "proxima segunda-feira",
        "erro": "Sem ciclos disponiveis. Faca upgrade para continuar." if not can_proceed else None,
    }
