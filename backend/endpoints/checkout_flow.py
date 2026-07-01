"""
Fluxo de checkout simplificado:
- POST /api/credits/checkout-trial          -> TESTAR GRATIS (cria user, libera trial)
- POST /api/credits/checkout-with-signup     -> ASSINAR DIRETO (cria user pending + MP order)
- POST /api/credits/checkout-resume         -> RETOMAR (user existente + nova order)
- POST /api/credits/checkout-trial-upgrade   -> TRIAL -> ASSINAR (user logado trialing)
- POST /api/credits/webhook/mercadopago      -> WEBHOOK (libera acesso quando approved)
- GET  /api/credits/me                       -> status do user (trialing/active/blocked)
"""
import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.core.rate_limiter import limiter
from backend.endpoints.credits_endpoints import (
    _app_url, _notification_url, _post_mercadopago, _get_mercadopago,
    PLANOS, _criar_assinatura_mercadopago
)

router = APIRouter(prefix="/api/checkout", tags=["checkout-flow"])


# ============================================================
# Schemas
# ============================================================
class CheckoutTrialRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    whatsapp: str = Field(..., min_length=8, max_length=50)
    password: str = Field(..., min_length=8, max_length=72)


class CheckoutWithSignupRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    whatsapp: str = Field(..., min_length=8, max_length=50)
    password: str = Field(..., min_length=8, max_length=72)
    plano: str = Field(..., description="starter | pro | agency")
    accept_terms: bool = Field(default=True)


class CheckoutResumeRequest(BaseModel):
    plano: str = Field(..., description="starter | pro | agency")


class CheckoutTrialUpgradeRequest(BaseModel):
    plano: str = Field(..., description="starter | pro | agency")


# ============================================================
# Helpers
# ============================================================
def _hash_password(password: str) -> str:
    """Hash simples SHA256+salt (substitui bcrypt para performance em signup publico)."""
    salt = secrets.token_urlsafe(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"sha256${salt}${h}"


def _verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash or not stored_hash.startswith("sha256$"):
        return False
    try:
        _, salt, h = stored_hash.split("$", 2)
        return hmac.compare_digest(h, hashlib.sha256((salt + password).encode()).hexdigest())
    except Exception:
        return False


def _get_or_create_user_pending(db, nome, email, whatsapp, password_hash) -> dict:
    """Cria user com status=pending_payment, access=blocked, ou retorna existente."""
    row = db.execute(
        text("SELECT id, email, name, nome, whatsapp, status, access, current_plan_id, trial_ends_at FROM users WHERE email = :e LIMIT 1"),
        {"e": email.lower()},
    ).fetchone()
    if row:
        # Atualiza whatsapp se nao tiver
        if not row[4]:
            db.execute(text("UPDATE users SET whatsapp=:w WHERE id=:i"), {"w": whatsapp, "i": row[0]})
            db.commit()
        return {
            "id": int(row[0]),
            "email": row[1],
            "name": row[2] or row[3] or nome,
            "status": row[5] or "pending_payment",
            "access": row[6] or "blocked",
            "current_plan_id": row[7] or "trial",
            "trial_ends_at": row[8],
        }
    now = datetime.utcnow().isoformat()
    trial_end = (datetime.utcnow() + timedelta(days=7)).isoformat()
    result = db.execute(
        text("""
            INSERT INTO users (email, name, nome, password_hash, senha_hash, whatsapp,
                plano, plan, role, status, access, current_plan_id,
                creditos, creditos_max, trial_started_at, trial_ends_at,
                email_confirmado, criado_em, plan_expires_at, trial_expires_at,
                terms_accepted_at, terms_version, privacy_accepted_at, privacy_version)
            VALUES (:e, :n, :n, :h, :h, :w, :p, :p, 'user', :s, :a, :cid,
                0, 0, :now, :te, false, :now, :te, :te,
                :now, 'v1', :now, 'v1')
            RETURNING id, email, name, nome, status, access, current_plan_id, trial_ends_at
        """),
        {
            "e": email.lower(), "n": nome, "h": password_hash, "w": whatsapp,
            "p": "trial", "s": "pending_payment", "a": "blocked", "cid": "trial",
            "now": now, "te": trial_end,
        },
    ).fetchone()
    db.commit()
    if not result:
        raise HTTPException(500, "Falha ao criar usuario")
    return {
        "id": int(result[0]),
        "email": result[1],
        "name": result[2] or result[3] or nome,
        "status": result[4] or "pending_payment",
        "access": result[5] or "blocked",
        "current_plan_id": result[6] or "trial",
        "trial_ends_at": result[7],
    }


def _create_order(db, user_id: int, plan_id: str, amount_cents: int, flow: str) -> str:
    """Cria order no banco e retorna order_id."""
    order_id = f"fralib-{uuid.uuid4().hex[:16]}"
    db.execute(
        text("""
            INSERT INTO orders (order_id, user_id, plan_id, amount_cents, currency,
                payment_type, status, flow)
            VALUES (:oid, :uid, :pid, :amt, 'BRL', 'mercadopago', 'pending', :flow)
        """),
        {"oid": order_id, "uid": user_id, "pid": plan_id, "amt": amount_cents, "flow": flow},
    )
    db.commit()
    return order_id


# ============================================================
# ENDPOINT 1: TESTAR GRATIS (FLUXO 1)
# ============================================================
@router.post("/checkout-trial")
@limiter.limit("5/minute")
async def checkout_trial(request: Request, data: CheckoutTrialRequest, db: Session = Depends(get_db)):
    """
    FLUXO 1: TESTAR GRATIS
    - Cria usuario (se nao existe) com status=trialing, access=released
    - trial_ends_at = agora + 7 dias
    - current_plan_id = 'trial'
    - NAO cria checkout MP
    - Libera acesso imediato
    """
    email_lower = data.email.lower()

    # Verifica se email ja existe
    existing = db.execute(
        text("SELECT id, status, access, current_plan_id, trial_ends_at FROM users WHERE email = :e"),
        {"e": email_lower},
    ).fetchone()

    if existing:
        user_id = int(existing[0])
        # Se ja e trial ativo, retorna ok
        if existing[1] == "trialing" and existing[2] == "released" and existing[4] and existing[4] > datetime.utcnow().isoformat():
            return {
                "status": "ok",
                "flow": "trial_existing",
                "message": "Voce ja esta no teste gratis. Aproveite!",
                "user_id": user_id,
                "trial_ends_at": existing[4],
                "redirect": "/admin.html",
            }
        # Se ja pagou, redireciona para dashboard
        if existing[1] == "active":
            return {
                "status": "ok",
                "flow": "already_active",
                "message": "Voce ja e assinante ativo!",
                "user_id": user_id,
                "redirect": "/admin.html",
            }

    # Cria novo user trial
    password_hash = _hash_password(data.password)
    now = datetime.utcnow().isoformat()
    trial_end = (datetime.utcnow() + timedelta(days=7)).isoformat()

    if existing:
        # Atualiza user existente
        db.execute(
            text("""
                UPDATE users SET
                    status = 'trialing',
                    access = 'released',
                    current_plan_id = 'trial',
                    trial_started_at = :now,
                    trial_ends_at = :te,
                    plano = 'trial',
                    plan = 'free',
                    password_hash = :h,
                    senha_hash = :h,
                    whatsapp = COALESCE(NULLIF(:w, ''), whatsapp)
                WHERE id = :uid
            """),
            {"now": now, "te": trial_end, "h": password_hash, "w": data.whatsapp, "uid": existing[0]},
        )
        user_id = int(existing[0])
    else:
        result = db.execute(
            text("""
                INSERT INTO users (email, name, nome, password_hash, senha_hash, whatsapp,
                    plano, plan, role, status, access, current_plan_id,
                    creditos, creditos_max, trial_started_at, trial_ends_at,
                    email_confirmado, criado_em, plan_expires_at, trial_expires_at,
                    terms_accepted_at, terms_version, privacy_accepted_at, privacy_version)
                VALUES (:e, :n, :n, :h, :h, :w, 'trial', 'free', 'user', 'trialing', 'released', 'trial',
                    1, 1, :now, :te, true, :now, :te, :te,
                    :now, 'v1', :now, 'v1')
                RETURNING id
            """),
            {
                "e": email_lower, "n": data.nome, "h": password_hash, "w": data.whatsapp,
                "now": now, "te": trial_end,
            },
        ).fetchone()
        if not result:
            raise HTTPException(500, "Falha ao criar usuario")
        user_id = int(result[0])

    db.commit()

    return {
        "status": "ok",
        "flow": "trial_signup",
        "message": "Teste gratis ativado! Voce tem 7 dias para experimentar.",
        "user_id": user_id,
        "email": email_lower,
        "trial_started_at": now,
        "trial_ends_at": trial_end,
        "trial_days": 7,
        "credits": 1,
        "redirect": "/admin.html?welcome=trial",
    }


# ============================================================
# ENDPOINT 2: ASSINAR DIRETO (FLUXO 2)
# ============================================================
@router.post("/checkout-with-signup")
@limiter.limit("5/minute")
async def checkout_with_signup(request: Request, data: CheckoutWithSignupRequest, db: Session = Depends(get_db)):
    """
    FLUXO 2: ASSINAR DIRETO (sem testar)
    - Cria user com status=pending_payment, access=blocked
    - Cria order no banco
    - Cria preferencia MP com external_reference = order_id
    - Retorna checkout_url
    - Acesso so e liberado via webhook com status=approved
    """
    if data.plano not in PLANOS:
        raise HTTPException(400, f"Plano invalido. Use: {', '.join(PLANOS.keys())}")

    password_hash = _hash_password(data.password)
    user = _get_or_create_user_pending(db, data.nome, data.email, data.whatsapp, password_hash)

    if user["status"] == "active":
        return {
            "status": "ok",
            "flow": "already_active",
            "message": "Voce ja e assinante!",
            "user_id": user["id"],
            "redirect": "/admin.html",
        }

    # Cria order
    plan = PLANOS[data.plano]
    order_id = _create_order(db, user["id"], data.plano, int(plan["valor"] * 100), "direct_signup")

    # Cria preferencia MP via /preapproval (assinatura recorrente)
    external_reference = f"fralib:{user['id']}:{data.plano}:{order_id}"
    app_url = _app_url()
    notification_url = _notification_url()
    preapproval = {
        "reason": plan["titulo"],
        "external_reference": external_reference,
        "payer_email": user["email"],
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": plan["valor"],
            "currency_id": "BRL",
        },
        "back_url": f"{app_url}/pagamento/sucesso?order={order_id}&plano={data.plano}",
        "notification_url": notification_url,
        "status": "pending",
    }
    payment_methods_str = os.getenv("MERCADOPAGO_PAYMENT_METHODS", "pix,credit_card").strip()
    if payment_methods_str and payment_methods_str.lower() != "all":
        methods = [m.strip() for m in payment_methods_str.split(",") if m.strip()]
        if methods:
            preapproval["payment_methods_allowed"] = methods

    try:
        data_mp = _post_mercadopago("/preapproval", preapproval)
    except Exception as exc:
        raise HTTPException(502, f"Erro Mercado Pago: {exc}")

    checkout_url = data_mp.get("init_point") or data_mp.get("sandbox_init_point")
    if not checkout_url:
        raise HTTPException(502, "Mercado Pago nao retornou checkout_url")

    preapproval_id = data_mp.get("id")
    # Salva preapproval_id na order
    db.execute(
        text("UPDATE orders SET mercadopago_preference_id = :pid WHERE order_id = :oid"),
        {"pid": preapproval_id, "oid": order_id},
    )
    db.commit()

    return {
        "status": "ok",
        "flow": "direct_signup",
        "user_id": user["id"],
        "order_id": order_id,
        "preapproval_id": preapproval_id,
        "checkout_url": checkout_url,
        "plano": data.plano,
        "amount": plan["valor"],
        "redirect": checkout_url,
    }


# ============================================================
# ENDPOINT 3: RETOMAR PAGAMENTO (FLUXO 5)
# ============================================================
@router.post("/checkout-resume")
@limiter.limit("10/minute")
async def checkout_resume(request: Request, data: CheckoutResumeRequest, db: Session = Depends(get_db)):
    """
    FLUXO 5: RETOMAR pagamento (user ja existe, com pendencia).
    Cria NOVA order + checkout MP. NAO duplica usuario.
    """
    if data.plano not in PLANOS:
        raise HTTPException(400, f"Plano invalido. Use: {', '.join(PLANOS.keys())}")

    # Detecta user logado (cookie ou Bearer)
    from backend.endpoints.credits_endpoints import _extrair_usuario_request
    try:
        user = _extrair_usuario_request(request)
    except HTTPException:
        raise HTTPException(401, "Autenticacao necessaria para retomar pagamento")

    if user["status"] == "active":
        return {
            "status": "ok",
            "message": "Voce ja e assinante ativo!",
            "redirect": "/admin.html",
        }

    plan = PLANOS[data.plano]
    order_id = _create_order(db, user["id"], data.plano, int(plan["valor"] * 100), "abandoned_recovery")

    external_reference = f"fralib:{user['id']}:{data.plano}:{order_id}"
    app_url = _app_url()
    notification_url = _notification_url()
    preapproval = {
        "reason": plan["titulo"],
        "external_reference": external_reference,
        "payer_email": user["email"],
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": plan["valor"],
            "currency_id": "BRL",
        },
        "back_url": f"{app_url}/pagamento/sucesso?order={order_id}&plano={data.plano}",
        "notification_url": notification_url,
        "status": "pending",
    }
    payment_methods_str = os.getenv("MERCADOPAGO_PAYMENT_METHODS", "pix,credit_card").strip()
    if payment_methods_str and payment_methods_str.lower() != "all":
        methods = [m.strip() for m in payment_methods_str.split(",") if m.strip()]
        if methods:
            preapproval["payment_methods_allowed"] = methods

    data_mp = _post_mercadopago("/preapproval", preapproval)
    checkout_url = data_mp.get("init_point") or data_mp.get("sandbox_init_point")
    if not checkout_url:
        raise HTTPException(502, "Mercado Pago nao retornou checkout_url")

    db.execute(
        text("UPDATE orders SET mercadopago_preference_id = :pid WHERE order_id = :oid"),
        {"pid": data_mp.get("id"), "oid": order_id},
    )
    db.commit()

    return {
        "status": "ok",
        "flow": "abandoned_recovery",
        "user_id": user["id"],
        "order_id": order_id,
        "checkout_url": checkout_url,
        "plano": data.plano,
        "amount": plan["valor"],
        "redirect": checkout_url,
    }


# ============================================================
# ENDPOINT 4: TRIAL -> ASSINAR (FLUXO 3)
# ============================================================
@router.post("/checkout-trial-upgrade")
@limiter.limit("10/minute")
async def checkout_trial_upgrade(request: Request, data: CheckoutTrialUpgradeRequest, db: Session = Depends(get_db)):
    """
    FLUXO 3: User em TRIAL clica "Assinar agora".
    - Nao cria user novo
    - Cria order com flow=trial_upgrade
    - Cria checkout MP
    - Mantem acesso trial ate webhook confirmar pagamento
    """
    if data.plano not in PLANOS:
        raise HTTPException(400, f"Plano invalido. Use: {', '.join(PLANOS.keys())}")

    from backend.endpoints.credits_endpoints import _extrair_usuario_request
    user = _extrair_usuario_request(request)

    if user["status"] != "trialing":
        # Se ja pagou, redireciona
        if user["status"] == "active":
            return {"status": "ok", "message": "Voce ja e assinante ativo!", "redirect": "/admin.html"}
        # Se trial expirou, redireciona para retomar
        if user["status"] == "trial_expired":
            return {"status": "expired", "message": "Seu teste expirou. Retome o pagamento.", "redirect": "/pagamento/renovar"}

    plan = PLANOS[data.plano]
    order_id = _create_order(db, user["id"], data.plano, int(plan["valor"] * 100), "trial_upgrade")

    external_reference = f"fralib:{user['id']}:{data.plano}:{order_id}"
    app_url = _app_url()
    notification_url = _notification_url()
    preapproval = {
        "reason": plan["titulo"],
        "external_reference": external_reference,
        "payer_email": user["email"],
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": plan["valor"],
            "currency_id": "BRL",
        },
        "back_url": f"{app_url}/pagamento/sucesso?order={order_id}&plano={data.plano}",
        "notification_url": notification_url,
        "status": "pending",
    }
    payment_methods_str = os.getenv("MERCADOPAGO_PAYMENT_METHODS", "pix,credit_card").strip()
    if payment_methods_str and payment_methods_str.lower() != "all":
        methods = [m.strip() for m in payment_methods_str.split(",") if m.strip()]
        if methods:
            preapproval["payment_methods_allowed"] = methods

    data_mp = _post_mercadopago("/preapproval", preapproval)
    checkout_url = data_mp.get("init_point") or data_mp.get("sandbox_init_point")
    if not checkout_url:
        raise HTTPException(502, "Mercado Pago nao retornou checkout_url")

    db.execute(
        text("UPDATE orders SET mercadopago_preference_id = :pid WHERE order_id = :oid"),
        {"pid": data_mp.get("id"), "oid": order_id},
    )
    db.commit()

    return {
        "status": "ok",
        "flow": "trial_upgrade",
        "user_id": user["id"],
        "order_id": order_id,
        "checkout_url": checkout_url,
        "plano": data.plano,
        "amount": plan["valor"],
        "redirect": checkout_url,
    }


# ============================================================
# ENDPOINT 5: ME - status do user (trialing/active/blocked)
# ============================================================
@router.get("/me")
async def checkout_me(request: Request, db: Session = Depends(get_db)):
    """Retorna status de acesso do user (trialing valido, active, blocked, etc)."""
    from backend.endpoints.credits_endpoints import _extrair_usuario_request
    try:
        user = _extrair_usuario_request(request)
    except HTTPException:
        return {
            "status": "anonymous",
            "access": "blocked",
            "can_access_dashboard": False,
            "message": "Nao logado",
        }

    now = datetime.utcnow().isoformat()
    trial_ends = user.get("trial_ends_at")
    if trial_ends and isinstance(trial_ends, str):
        trial_ends_dt = trial_ends
    else:
        trial_ends_dt = None

    # Calcular acesso
    can_access = False
    reason = ""
    if user["status"] == "active" and user["access"] == "released":
        can_access = True
        reason = "active_paid"
    elif user["status"] == "trialing" and user["access"] == "released":
        if trial_ends_dt and trial_ends_dt > now:
            can_access = True
            reason = "trial_valid"
        else:
            reason = "trial_expired_needs_payment"
    elif user["status"] == "trial_expired" or user["access"] == "blocked":
        reason = "blocked_pending_payment"
    elif user["status"] == "pending_payment":
        reason = "pending_payment"

    return {
        "user_id": user["id"],
        "email": user["email"],
        "status": user["status"],
        "access": user["access"],
        "current_plan_id": user.get("current_plan_id"),
        "trial_ends_at": trial_ends_dt,
        "can_access_dashboard": can_access,
        "reason": reason,
        "redirect": "/admin.html" if can_access else "/pagamento/renovar",
    }
