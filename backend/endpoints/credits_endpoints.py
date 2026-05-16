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


@router.post('/portal')
async def criar_portal_session(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    """Cria sessao do Stripe Customer Portal.
    Cliente gerencia assinatura, troca de cartao, cancelamento e historico de pagamentos.
    """
    row = db.execute(text(
        'SELECT stripe_customer_id FROM users WHERE id=:id'
    ), {'id': usuario['id']}).fetchone()
    if not row or not row[0]:
        raise HTTPException(400, 'Voce ainda nao possui assinatura ativa. Assine um plano primeiro.')
    try:
        session = stripe.billing_portal.Session.create(
            customer=row[0],
            return_url=os.getenv('APP_URL', 'https://fralib.com') + '/dashboard',
        )
        return {'portal_url': session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(500, f'Stripe: {str(e)}')


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


def _resolver_user_id(conn, meta_user_id, customer_email, stripe_customer_id):
    """Resolve user_id com validacao cruzada — impede forja de metadata.

    Coleta candidatos das 3 fontes (metadata, email, stripe_customer_id) e:
    - 0 candidatos: retorna None.
    - 1 candidato: retorna direto.
    - >1 candidatos: conflito — confia em stripe_customer_id > email; metadata sozinho NAO basta.
    """
    candidatos = set()
    uid_via_cid = None
    uid_via_email = None
    if meta_user_id:
        try:
            candidatos.add(int(meta_user_id))
        except (TypeError, ValueError):
            pass
    if customer_email:
        row = conn.execute(text('SELECT id FROM users WHERE email=:e'), {'e': customer_email}).fetchone()
        if row:
            uid_via_email = int(row[0])
            candidatos.add(uid_via_email)
    if stripe_customer_id:
        row = conn.execute(text('SELECT id FROM users WHERE stripe_customer_id=:c'), {'c': stripe_customer_id}).fetchone()
        if row:
            uid_via_cid = int(row[0])
            candidatos.add(uid_via_cid)
    if not candidatos:
        return None
    if len(candidatos) == 1:
        return candidatos.pop()
    # Conflito: priorizar stripe_customer_id > email; metadata sozinho NAO eh aceito.
    print(f'[Stripe] CONFLITO _resolver_user_id: candidatos={candidatos} '
          f'meta={meta_user_id} email={customer_email} cid={stripe_customer_id}')
    if uid_via_cid is not None:
        return uid_via_cid
    if uid_via_email is not None:
        return uid_via_email
    return None


def _plano_from_price_id(price_id):
    """Mapeia stripe price_id -> plano interno (para customer.subscription.updated)."""
    if price_id == PRICE_PRO:
        return 'pro'
    if price_id == PRICE_STARTER:
        return 'starter'
    return None


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

    event_id = event.get('id', '')
    tipo = event.get('type', '')
    obj = event.get('data', {}).get('object', {}) or {}
    stripe_customer_id = obj.get('customer', '') or ''

    from database import engine
    # ── Idempotencia: ja processamos esse event_id? ──
    with engine.connect() as conn:
        existe = conn.execute(text(
            'SELECT processado FROM stripe_events WHERE event_id=:e'
        ), {'e': event_id}).fetchone()
        if existe and existe[0]:
            return {'status': 'duplicado', 'event_id': event_id}
        # Registra o evento como "recebido" (ainda nao processado)
        conn.execute(text('''
            INSERT INTO stripe_events (event_id, tipo, stripe_customer_id, processado)
            VALUES (:e, :t, :c, false)
            ON CONFLICT (event_id) DO NOTHING
        '''), {'e': event_id, 't': tipo, 'c': stripe_customer_id})
        conn.commit()

    # ── Processa o evento. Qualquer falha vai pra stripe_events.erro
    #    sem derrubar a resposta 200 (Stripe re-tentaria sozinho). ──
    try:
        resolved_user_id = await _processar_evento_stripe(event, tipo, obj, stripe_customer_id)
        with engine.connect() as conn:
            conn.execute(text('''
                UPDATE stripe_events
                SET processado=true, processado_em=NOW(), user_id=:u
                WHERE event_id=:e
            '''), {'e': event_id, 'u': resolved_user_id})
            conn.commit()
        return {'status': 'ok', 'tipo': tipo, 'user_id': resolved_user_id}
    except Exception as exc:
        err_msg = f'{type(exc).__name__}: {str(exc)[:500]}'
        print(f'[Stripe webhook] FALHA em {tipo} ({event_id}): {err_msg}')
        with engine.connect() as conn:
            conn.execute(text('''
                UPDATE stripe_events SET erro=:err WHERE event_id=:e
            '''), {'e': event_id, 'err': err_msg})
            conn.commit()
        # Retornar 200 mesmo em falha logica (signature ja foi validada).
        # Erros transientes ficam logados em stripe_events.erro.
        return {'status': 'erro_logado', 'tipo': tipo, 'erro': err_msg}


async def _processar_evento_stripe(event, tipo, obj, stripe_customer_id):
    """Roteia o evento para o handler certo. Retorna user_id resolvido (ou None)."""
    from database import engine

    if tipo in ('checkout.session.completed', 'invoice.payment_succeeded'):
        meta = obj.get('metadata') or {}
        plano = meta.get('plano', 'starter')
        customer_email = obj.get('customer_email') or (obj.get('customer_details') or {}).get('email', '')
        stripe_subscription_id = obj.get('subscription', '') or ''
        with engine.connect() as conn:
            user_id = _resolver_user_id(conn, meta.get('user_id'), customer_email, stripe_customer_id)
            if not user_id:
                print(f'[Stripe] usuario nao encontrado: email={customer_email} cid={stripe_customer_id}')
                return None
            if plano == 'tokens':
                bonus = PLANOS['tokens']['creditos_max']
                conn.execute(text('''
                    UPDATE users SET creditos = COALESCE(creditos,0) + :bonus,
                        stripe_customer_id=:cid
                    WHERE id=:uid
                '''), {'bonus': bonus, 'cid': stripe_customer_id, 'uid': user_id})
                conn.commit()
                print(f'[Stripe] tokens OK: user {user_id} -> +{bonus} creditos')
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
                    'cmax': creditos_max, 'exp': plan_expires_at, 'uid': user_id
                })
                conn.commit()
                print(f'[Stripe] checkout OK: user {user_id} -> plano {plano}, creditos {creditos_max}')
            return user_id

    elif tipo == 'customer.subscription.updated':
        # Upgrade ou downgrade. items.data[0].price.id da o novo plano.
        items = (obj.get('items') or {}).get('data') or []
        price_id = items[0].get('price', {}).get('id', '') if items else ''
        novo_plano = _plano_from_price_id(price_id)
        status = obj.get('status', '')
        if not stripe_customer_id:
            return None
        with engine.connect() as conn:
            row = conn.execute(text(
                'SELECT id FROM users WHERE stripe_customer_id=:c'
            ), {'c': stripe_customer_id}).fetchone()
            if not row:
                print(f'[Stripe] subscription.updated sem user para {stripe_customer_id}')
                return None
            user_id = int(row[0])
            if novo_plano and status in ('active', 'trialing'):
                creditos_max = PLANOS.get(novo_plano, {}).get('creditos_max', 5)
                conn.execute(text('''
                    UPDATE users SET plano=:plano, plan=:plano, plano_pago=true,
                        status='ativo', creditos_max=:cmax
                    WHERE id=:uid
                '''), {'plano': novo_plano, 'cmax': creditos_max, 'uid': user_id})
                conn.commit()
                print(f'[Stripe] subscription.updated: user {user_id} -> plano {novo_plano}')
            elif status == 'past_due':
                conn.execute(text('''
                    UPDATE users SET status='inadimplente' WHERE id=:uid
                '''), {'uid': user_id})
                conn.commit()
                print(f'[Stripe] subscription past_due: user {user_id}')
            return user_id

    elif tipo == 'invoice.payment_failed':
        if not stripe_customer_id:
            return None
        with engine.connect() as conn:
            row = conn.execute(text(
                'SELECT id FROM users WHERE stripe_customer_id=:c'
            ), {'c': stripe_customer_id}).fetchone()
            if not row:
                return None
            user_id = int(row[0])
            # Nao tira o plano imediatamente - Stripe ainda vai tentar de novo.
            # Marca status para o dashboard mostrar aviso.
            conn.execute(text('''
                UPDATE users SET status='inadimplente' WHERE id=:uid
            '''), {'uid': user_id})
            conn.commit()
            print(f'[Stripe] payment_failed: user {user_id} marcado inadimplente')
            return user_id

    elif tipo == 'customer.subscription.deleted':
        if not stripe_customer_id:
            return None
        with engine.connect() as conn:
            row = conn.execute(text(
                'SELECT id FROM users WHERE stripe_customer_id=:c'
            ), {'c': stripe_customer_id}).fetchone()
            user_id = int(row[0]) if row else None
            conn.execute(text('''
                UPDATE users SET plano='trial', plan='trial', plano_pago=false,
                    creditos=0, creditos_max=1, status='trial'
                WHERE stripe_customer_id=:cid
            '''), {'cid': stripe_customer_id})
            conn.commit()
            print(f'[Stripe] subscription cancelada: customer {stripe_customer_id}')
            return user_id

    else:
        # Tipo nao tratado - ignora silenciosamente (Stripe envia varios eventos)
        return None


PACOTES_CREDITOS = [
    {"valor": 5.00,  "creditos_base": 1,  "bonus_percentual": 0,  "creditos_totais": 1,  "custo_por_credito": 5.00},
    {"valor": 20.00, "creditos_base": 5,  "bonus_percentual": 10, "creditos_totais": 5,  "custo_por_credito": 4.00},
    {"valor": 50.00, "creditos_base": 15, "bonus_percentual": 20, "creditos_totais": 18, "custo_por_credito": 2.78},
    {"valor": 100.00,"creditos_base": 30, "bonus_percentual": 35, "creditos_totais": 40, "custo_por_credito": 2.50},
]


@router.get('/pricing')
async def get_pricing():
    """Retorna tabela de pacotes de creditos com bonus progressivo."""
    return PACOTES_CREDITOS


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
        stripe_link = os.getenv("STRIPE_PAYMENT_LINK", "#")
        alert = {"message": "Ultimo ciclo disponivel. Considere fazer upgrade para continuar gerando sites.", "icon": "⚠️", "color": "#f59e0b", "payment_link": stripe_link}
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
