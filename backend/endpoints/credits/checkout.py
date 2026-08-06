"""
Endpoints de checkout Cakto — recargas, PIX avulso, recorrência.

Migra de credits_endpoints.py:
- /criar-checkout (recarga ou assinatura)
- /criar-checkout-anonimo (visitante nao logado)
- /criar-pagamento-pix (PIX avulso mensal)
- /sync-cakto (reconcilia webhook atrasado)
"""
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from backend.core.auth_helpers import _app_url, _extrair_usuario_request, _notification_url
from backend.core.database import get_db, engine as _engine
from backend.core.auth import get_current_user
from backend.domain.plans import PLAN_SPECS, get_plan_spec
from backend.services.cakto_client import get_cakto_client, ensure_cakto_authenticated
from backend.shared.password import hash_password
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/credits", tags=["credits-checkout"])

RECARGA_MINIMA = Decimal("5.00")
RECARGA_MAXIMA = Decimal(os.getenv("CAKTO_RECHARGE_MAX_AMOUNT", "5000.00"))

PACOTES_CREDITOS = [
    {"valor": 5.00, "creditos_base": 1, "bonus_percentual": 0, "creditos_totais": 1, "custo_por_credito": 5.00},
    {"valor": 20.00, "creditos_base": 5, "bonus_percentual": 10, "creditos_totais": 5, "custo_por_credito": 4.00},
    {"valor": 50.00, "creditos_base": 15, "bonus_percentual": 20, "creditos_totais": 18, "custo_por_credito": 2.78},
    {"valor": 100.00, "creditos_base": 30, "bonus_percentual": 35, "creditos_totais": 40, "custo_por_credito": 2.50},
]

PAID_PLANS = [p for p in PLAN_SPECS if p != "free"]


def _cakto_checkout_url(offer_id: str) -> str:
    return f"https://pay.cakto.com.br/{offer_id}"


def _normalize_amount(valor: float | Decimal | None) -> Decimal:
    if valor is None:
        raise HTTPException(400, "Informe o valor da recarga")
    try:
        amount = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    except Exception:
        raise HTTPException(400, "Valor de recarga invalido")
    if amount < RECARGA_MINIMA:
        raise HTTPException(400, f"Recarga minima R$ {RECARGA_MINIMA}")
    if amount > RECARGA_MAXIMA:
        raise HTTPException(400, f"Recarga maxima R$ {RECARGA_MAXIMA}")
    return amount


def _credit_package_for_value(valor: float | Decimal) -> dict:
    amount = _normalize_amount(valor)
    amount_float = float(amount)
    for pacote in PACOTES_CREDITOS:
        if abs(pacote["valor"] - amount_float) < 0.01:
            return {**pacote, "valor": amount_float, "custom": False}

    if amount < Decimal("20.00"):
        cost_per_credit = Decimal("5.00")
        bonus = 0
    elif amount < Decimal("50.00"):
        cost_per_credit = Decimal("4.00")
        bonus = 10
    elif amount < Decimal("100.00"):
        cost_per_credit = Decimal("2.78")
        bonus = 20
    else:
        cost_per_credit = Decimal("2.50")
        bonus = 35

    creditos_totais = max(1, int((amount / cost_per_credit).to_integral_value(rounding=ROUND_DOWN)))
    creditos_base = max(1, int((amount / Decimal("5.00")).to_integral_value(rounding=ROUND_DOWN)))
    custo_por_credito = float((amount / Decimal(creditos_totais)).quantize(Decimal("0.01"), rounding=ROUND_DOWN))
    return {
        "valor": amount_float,
        "creditos_base": creditos_base,
        "bonus_percentual": bonus,
        "creditos_totais": creditos_totais,
        "custo_por_credito": custo_por_credito,
        "custom": True,
    }


class CheckoutRequest(BaseModel):
    plano: Optional[str] = Field(default=None, description="starter, pro, recarga ou tokens")
    valor: Optional[float] = Field(default=None, description="Valor livre da recarga em BRL")
    email: Optional[str] = Field(default=None, description="Email do pagador (quando nao logado)")


class CheckoutAnonimoRequest(BaseModel):
    plano: str = Field(..., description="starter, pro ou agency")
    email: str = Field(..., description="Email para vinculacao pos-cadastro")


class CheckoutPixUnicoRequest(BaseModel):
    plano: str = Field(..., description="starter, pro ou agency")
    email: str = Field(..., description="Email do pagador para recibo/PIX")


class CaktoSyncRequest(BaseModel):
    payment_id: Optional[str] = None
    subscription_id: Optional[str] = None
    status: Optional[str] = None


@router.post("/criar-checkout")
async def criar_checkout(
    body: CheckoutRequest,
    request: Request,
):
    """Cria checkout Cakto via sessao de cookie (sem Bearer token).
    Se nao autenticado, retorna 401 para o frontend redirecionar para cadastro.
    """
    plano = (body.plano or "").strip().lower()
    if not plano:
        raise HTTPException(400, "Plano invalido.")

    usuario = _extrair_usuario_request(request)

    if body.valor is not None:
        return await _criar_recarga_cakto(body.valor, usuario)
    if plano in {"recarga", "tokens", "creditos"}:
        valor = float(os.getenv("CAKTO_TOKENS_AMOUNT", "50"))
        return await _criar_recarga_cakto(valor, usuario)
    if plano in PAID_PLANS:
        return await _criar_assinatura_cakto(plano, usuario)
    raise HTTPException(400, "Plano invalido. Use starter, pro, agency ou informe valor para recarga.")


@router.post("/criar-checkout-anonimo")
async def criar_checkout_anonimo(
    body: CheckoutAnonimoRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Cria checkout Cakto para visitante NAO logado.
    - Requer apenas email + plano
    - Cria usuario com senha temporaria (NAO zumbi — pode fazer login)
    - Webhook Cakto vincula pagamento ao user_id quando confirmar
    - Retorna checkout_url + signup_url com pre-fill de email + senha temporaria
    """
    email = (body.email or "").strip().lower()
    plano = (body.plano or "").strip().lower()

    if not email or "@" not in email or len(email) < 5:
        raise HTTPException(400, "Email invalido.")
    if plano not in PAID_PLANS:
        raise HTTPException(400, "Plano invalido. Use starter, pro ou agency.")

    spec = get_plan_spec(plano)
    if not spec:
        raise HTTPException(400, f"Plano nao encontrado: {plano}")

    app_url = _app_url()
    notification_url = _notification_url()

    temp_password = secrets.token_urlsafe(16)
    password_hash = hash_password(temp_password)

    with _engine.connect() as conn:
        existing = conn.execute(
            text("SELECT id, plano, status FROM users WHERE email=:e LIMIT 1"),
            {"e": email},
        ).fetchone()

        if existing:
            user_id = int(existing[0])
        else:
            # NORMALIZADO 2026-07-28: senha_hash removida. Apenas password_hash.
            result = conn.execute(
                text("""
                    INSERT INTO users (email, plano, status, password_hash,
                                      criado_em, trial_expires_at, plano_pago)
                    VALUES (:email, 'trial', 'pending', :hash,
                            NOW(), NOW() + INTERVAL '7 days', false)
                    ON CONFLICT (email) DO UPDATE SET email=EXCLUDED.email
                    RETURNING id
                """),
                {"email": email, "hash": password_hash},
            )
            row = result.fetchone()
            user_id = int(row[0])
        conn.commit()

    checkout = await _criar_assinatura_cakto(plano, {"id": user_id, "email": email})

    return {
        "checkout_url": checkout["checkout_url"],
        "provider": "cakto",
        "checkout_type": "subscription",
        "offer_id": checkout.get("offer_id"),
        "plano": plano,
        "user_id": user_id,
        "email": email,
        "signup_url": f"/login?signup=1&email={email}&plan={plano}&from=cakto",
        "temp_password": temp_password,
    }


@router.post("/criar-pagamento-pix")
async def criar_pagamento_pix_unico(
    body: CheckoutPixUnicoRequest,
    request: Request,
    usuario: dict = Depends(get_current_user),
):
    """Cria pagamento PIX unico (sem recorrencia) via Cakto.

    Limitação: Cakto gera PIX recorrente automaticamente na assinatura.
    Este endpoint cria pagamento avulso para quem quer pagar mes a mes.

    Fluxo:
      1. Cliente clica ASSINAR PRO -> escolhe "Pagar via PIX"
      2. Backend cria pagamento avulso com expiracao de 24h
      3. Retorna qr_code (texto copia-cola) e qr_code_base64 (imagem PNG)
      4. Frontend exibe tela /pagamento/pix-manual com QR Code
      5. Cliente paga no app do banco
      6. Webhook dispara -> libera 30 dias de acesso
      7. Mes seguinte: cliente gera novo pagamento PIX manualmente
    """
    # Auth + checagem de status
    user_id_logado = int(usuario["id"])
    user_status = (usuario.get("status") or "").lower()

    if user_status in {"inadimplente", "bloqueado", "suspenso", "cancelado"}:
        raise HTTPException(
            403,
            f"Sua conta esta em status '{user_status}' e nao pode gerar pagamento. "
            f"Regularize sua situacao ou entre em contato com o suporte.",
        )

    # Se ja tem assinatura recorrente ativa, PIX avulso nao faz sentido.
    if usuario.get("cakto_subscription_id"):
        logger.info(
            "pix_avulso_bloqueado_user_tem_subscription",
            extra={"user_id": user_id_logado, "subscription_id": usuario["cakto_subscription_id"]},
        )
        raise HTTPException(
            400,
            "Voce ja tem assinatura recorrente ativa via cartao. "
            "Use o painel de gerenciamento de assinatura para cancelar antes de gerar PIX avulso, "
            "ou aguarde a proxima renovacao automatica.",
        )

    email_logado = (usuario.get("email") or "").strip().lower()
    email_body = (body.email or "").strip().lower()
    if email_body and email_body != email_logado:
        logger.warning(
            "pix_avulso_email_body_divergente",
            extra={"user_id": user_id_logado, "email_body": email_body, "email_logado": email_logado},
        )
    email = email_logado

    plano = (body.plano or "").strip().lower()
    if not email or "@" not in email or len(email) < 5:
        raise HTTPException(400, "Email invalido para geracao do PIX.")
    if plano not in PAID_PLANS:
        raise HTTPException(400, f"Plano invalido. Use: {', '.join(PAID_PLANS)}.")

    spec = get_plan_spec(plano)
    if not spec:
        raise HTTPException(400, f"Plano nao encontrado: {plano}")

    app_url = _app_url()
    notification_url = _notification_url()

    # Nome derivado do email (PIX exige first/last name)
    email_user = email.split("@")[0]
    nome_parte = email_user.replace(".", " ").replace("_", " ").title()
    nome_parts = nome_parte.split(" ", 1)
    first_name = nome_parts[0] if len(nome_parts) >= 1 else "Cliente"
    last_name = nome_parts[1] if len(nome_parts) >= 2 else "FraLib"

    # external_reference: fralib:{user_id}:pix:{plano}:{uuid}
    external_reference = f"fralib:{user_id_logado}:pix:{plano}:{uuid.uuid4().hex[:12]}"
    idempotency_key = f"fralib_pix_{uuid.uuid4().hex}"

    cakto = get_cakto_client()
    await ensure_cakto_authenticated()

    # Cria charge PIX
    charge = await cakto._request("POST", "/charges/pix/", json={
        "amount": int(spec.monthly_brl * 100),
        "description": spec.label,
        "customer": {
            "name": f"{first_name} {last_name}",
            "email": email,
            "document": "",
        },
        "external_reference": external_reference,
        "notification_url": notification_url,
        "expires_in": 86400,  # 24h
    })

    qr_code = charge.get("qr_code", "")
    qr_base64 = charge.get("qr_code_base64", "")
    ticket_url = charge.get("ticket_url", "")

    return {
        "status": "ok",
        "payment_id": charge.get("id"),
        "external_reference": external_reference,
        "plano": plano,
        "valor": float(spec.monthly_brl),
        "qr_code": qr_code,
        "qr_code_base64": qr_base64,
        "ticket_url": ticket_url,
        "expira_em": charge.get("expires_at"),
        "redirect": f"/pagamento/pix-manual?payment_id={charge.get('id')}&plano={plano}",
        "payment_methods_available": ["pix"],
        "kind": "pix_unique_monthly",
    }


async def _criar_assinatura_cakto(plano: str, usuario: dict) -> dict:
    """Cria produto/oferta no Cakto e retorna URL de checkout."""
    spec = get_plan_spec(plano)
    if not spec or not spec.monthly_brl:
        raise HTTPException(400, f"Plano invalido: {plano}")

    user_id = int(usuario.get("id") or 0)
    external_reference = f"fralib:{user_id}:{plano}:{uuid.uuid4().hex[:12]}"

    # Offer ID pre-configurado via env var (produção)
    env_key = f"CAKTO_OFFER_{plano.upper()}"
    cached_offer_id = os.getenv(env_key, "").strip()
    if cached_offer_id:
        return {
            "checkout_url": _cakto_checkout_url(cached_offer_id),
            "provider": "cakto",
            "offer_id": cached_offer_id,
            "plano": plano,
            "external_reference": external_reference,
        }

    # Sem offer cacheada — cria dinamicamente
    cakto = get_cakto_client()
    await ensure_cakto_authenticated()

    # Cria produto (idempotente por nome)
    products = await cakto.list_products()
    product_id = None
    for p in products:
        if p.get("name") == "FraLib":
            product_id = p["id"]
            break
    if not product_id:
        product = await cakto.create_product(
            name="FraLib",
            description="Geracao de sites profissionais com IA",
            type_="subscription",
            category="software",
        )
        product_id = product.get("id")
        if not product_id:
            raise HTTPException(502, "Cakto nao retornou product_id")

    # Cria oferta com trial
    offer = await cakto.create_offer(
        name=spec.label,
        price=spec.monthly_brl,
        product_id=product_id,
        trial_days=spec.trial_days,
        recurrence_period="monthly",
        max_retries=spec.max_retries,
        retry_interval=spec.retry_interval_days,
        external_reference=external_reference,
    )
    offer_id = offer.get("id")
    if not offer_id:
        raise HTTPException(502, "Cakto nao retornou offer_id")

    return {
        "checkout_url": _cakto_checkout_url(offer_id),
        "provider": "cakto",
        "offer_id": offer_id,
        "plano": plano,
        "external_reference": external_reference,
    }


async def _criar_recarga_cakto(valor: float | Decimal, usuario: dict) -> dict:
    pacote = _credit_package_for_value(valor)
    external_reference = f"fralib:{usuario['id']}:recarga:{uuid.uuid4().hex[:12]}"
    app_url = _app_url()

    cakto = get_cakto_client()
    await ensure_cakto_authenticated()

    charge = await cakto._request("POST", "/charges/pix/", json={
        "amount": int(pacote["valor"] * 100),
        "description": f"FraLib recarga de {pacote['creditos_totais']} creditos",
        "customer": {
            "name": usuario.get("name") or usuario.get("email") or "Cliente",
            "email": usuario.get("email") or "",
        },
        "external_reference": external_reference,
        "notification_url": _notification_url(),
        "expires_in": 86400,
    })

    qr_code = charge.get("qr_code", "")
    qr_base64 = charge.get("qr_code_base64", "")
    ticket_url = charge.get("ticket_url", "")

    return {
        "checkout_url": ticket_url or _cakto_checkout_url(charge.get("id", "")),
        "provider": "cakto",
        "checkout_type": "recharge",
        "payment_id": charge.get("id"),
        "creditos": pacote["creditos_totais"],
        "valor": pacote["valor"],
    }


@router.post("/sync-cakto")
async def sync_cakto_payment(
    body: CaktoSyncRequest,
    usuario: dict = Depends(get_current_user),
):
    """Reconcilia retorno do Cakto quando o redirect/webhook atrasar."""
    subscription_id = (body.subscription_id or "").strip()
    payment_id = (body.payment_id or "").strip()

    if not subscription_id and not payment_id:
        return {
            "status": "pending",
            "message": "Pagamento ainda sem identificador. Clique em Voltar a loja no Cakto e aguarde a confirmacao.",
        }

    cakto = get_cakto_client()
    await ensure_cakto_authenticated()

    if payment_id:
        try:
            payment = await cakto._request("GET", f"/charges/{payment_id}/")
        except Exception as exc:
            raise HTTPException(502, f"Erro consultando Cakto: {exc}")

        if not _cakto_payload_matches_user(payment, usuario):
            raise HTTPException(403, "Pagamento nao pertence ao usuario autenticado")

        if (payment.get("status") or "").lower() != "approved":
            return {
                "status": payment.get("status") or "pending",
                "provider": "cakto",
                "message": "Pagamento ainda nao aprovado pelo Cakto.",
            }

        resolved_user_id = await _processar_pagamento_cakto(payment)
        return {
            "status": "ok",
            "provider": "cakto",
            "tipo": "payment",
            "user_id": resolved_user_id,
        }

    # subscription_id
    try:
        subscription = await cakto.get_subscription(subscription_id)
    except Exception as exc:
        raise HTTPException(502, f"Erro consultando Cakto: {exc}")

    if not _cakto_payload_matches_user(subscription, usuario):
        raise HTTPException(403, "Assinatura nao pertence ao usuario autenticado")

    resolved_user_id = await _processar_assinatura_cakto(subscription)
    return {
        "status": "ok" if resolved_user_id else (subscription.get("status") or "pending"),
        "provider": "cakto",
        "tipo": "subscription",
        "user_id": resolved_user_id,
    }


def _cakto_payload_matches_user(payload: dict, usuario: dict) -> bool:
    """Verifica se payload Cakto pertence ao usuario autenticado."""
    customer = payload.get("customer")
    if isinstance(customer, dict):
        payer_email = (customer.get("email") or "").strip().lower()
    else:
        payer_email = (payload.get("customer_email") or "").strip().lower()
    return bool(payer_email and payer_email == (usuario.get("email") or "").strip().lower())


async def _processar_pagamento_cakto(payment: dict) -> Optional[int]:
    """Processa pagamento Cakto aprovado (recarga)."""
    status = (payment.get("status") or "").lower()
    if status != "approved":
        return None

    external_ref = payment.get("external_reference") or ""
    metadata = payment.get("metadata") if isinstance(payment.get("metadata"), dict) else {}
    plano = (metadata.get("plano") or "recarga").lower()

    # Resolve user_id
    user_id = None
    try:
        parts = external_ref.split(":")
        if len(parts) >= 2 and parts[0] == "fralib":
            user_id = int(parts[1])
    except (ValueError, TypeError):
        pass

    if not user_id:
        customer = payment.get("customer", {})
        payer_email = (customer.get("email") or payment.get("customer_email") or "").strip()
        if payer_email:
            row = _engine.execute(
                text("SELECT id FROM users WHERE email=:e LIMIT 1"),
                {"e": payer_email},
            ).fetchone()
            if row:
                user_id = int(row[0])

    if not user_id:
        logger.warning(
            "cakto_payment_user_not_found",
            extra={"payer_email": payer_email, "payment_id": payment.get("id")},
        )
        return None

    with _engine.begin() as conn:
        if plano in {"recarga", "tokens", "creditos"}:
            pacote = _credit_package_for_value(metadata.get("valor") or os.getenv("CAKTO_TOKENS_AMOUNT", "50"))
            bonus = _safe_creditos_from_metadata(metadata, pacote["creditos_totais"])
            conn.execute(text("""
                UPDATE users SET creditos = COALESCE(creditos,0) + :bonus,
                    payment_provider='cakto',
                    cakto_last_payment_id=:payment
                WHERE id=:uid
            """), {"bonus": bonus, "payment": str(payment.get("id")), "uid": user_id})
            logger.info(
                "cakto_recharge_ok",
                extra={"user_id": user_id, "bonus": bonus, "payment_id": payment.get("id")},
            )
        elif plano in PAID_PLANS:
            await _ativar_plano_assinatura(conn, user_id, plano, payment.get("id"), subscription_id="")
        else:
            logger.warning(
                "cakto_plano_ignored",
                extra={"plano": plano, "payment_id": payment.get("id")},
            )
    return user_id


async def _processar_assinatura_cakto(subscription: dict) -> Optional[int]:
    """Processa assinatura Cakto (recorrente)."""
    status = (subscription.get("status") or "").lower()
    external_ref = subscription.get("external_reference") or ""
    plano = ""
    if external_ref:
        parts = external_ref.split(":")
        if len(parts) >= 3 and parts[0] == "fralib":
            plano = parts[2]

    if plano not in PAID_PLANS:
        return None

    customer = subscription.get("customer", {})
    payer_email = (customer.get("email") or subscription.get("customer_email") or "").strip()
    subscription_id = str(subscription.get("id") or "")

    user_id = None
    try:
        parts = external_ref.split(":")
        if len(parts) >= 2 and parts[0] == "fralib":
            user_id = int(parts[1])
    except (ValueError, TypeError):
        pass

    if not user_id and payer_email:
        row = _engine.execute(
            text("SELECT id FROM users WHERE email=:e LIMIT 1"),
            {"e": payer_email},
        ).fetchone()
        if row:
            user_id = int(row[0])

    if not user_id:
        logger.warning(
            "cakto_subscription_no_user",
            extra={"payer_email": payer_email, "subscription_id": subscription_id},
        )
        return None

    with _engine.begin() as conn:
        if status in {"active", "trialing"}:
            await _ativar_plano_assinatura(conn, user_id, plano, "", subscription_id)
            logger.info(
                "cakto_subscription_ok",
                extra={"user_id": user_id, "plano": plano, "subscription_id": subscription_id},
            )
        elif status in {"cancelled", "paused", "rejected"}:
            conn.execute(text("""
                UPDATE users SET plano_pago=false, status='past_due',
                    past_due_since=COALESCE(past_due_since, NOW())
                WHERE id=:uid
            """), {"uid": user_id})
            logger.info(
                "cakto_subscription_past_due",
                extra={"user_id": user_id, "status": status, "subscription_id": subscription_id},
            )
    return user_id


def _safe_creditos_from_metadata(metadata: dict, default: int) -> int:
    try:
        creditos = int(metadata.get("creditos") or default)
    except (TypeError, ValueError):
        creditos = default
    return max(1, min(creditos, 10000))


async def _ativar_plano_assinatura(conn, user_id: int, plano: str, payment_id: str = "", subscription_id: str = "") -> None:
    spec = PLAN_SPECS.get(plano)
    creditos_max = spec.monthly_credits if spec else 5
    conn.execute(text("""
        UPDATE users SET
            plano=:plano, plan=:plano, plano_pago=true, status='ativo',
            payment_provider='cakto',
            cakto_subscription_id=COALESCE(NULLIF(:sub,''), cakto_subscription_id),
            cakto_last_payment_id=COALESCE(NULLIF(:payment,''), cakto_last_payment_id),
            creditos=:cmax, creditos_max=:cmax,
            plan_expires_at=NOW() + INTERVAL '30 days',
            last_reset_date=CURRENT_DATE,
            past_due_since=NULL
        WHERE id=:uid
    """), {
        "plano": plano, "sub": subscription_id,
        "payment": payment_id, "cmax": creditos_max, "uid": user_id,
    })


@router.get("/pricing")
async def get_pricing():
    """Tabela de pacotes e contrato de recarga livre via Cakto."""
    return {
        "provider": "cakto",
        "currency": "BRL",
        "payment_methods": ["pix", "credit_card", "boleto"],
        "pacotes": PACOTES_CREDITOS,
        "recarga_livre": {
            "min": float(RECARGA_MINIMA),
            "max": float(RECARGA_MAXIMA),
            "default": 50.00,
            "step": 1.00,
        },
        "plans": [
            {"plano": key, "valor": value.monthly_brl, "creditos_max": value.monthly_credits, "trial_days": value.trial_days}
            for key, value in PLAN_SPECS.items()
            if key != "free"
        ],
    }


@router.get("/balance")
async def credits_balance(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Retorna saldo de creditos do usuario - compatibilidade admin.html."""
    row = db.execute(text(
        "SELECT creditos, creditos_max, plano, trial_expires_at FROM users WHERE id=:id"
    ), {"id": usuario["id"]}).fetchone()
    if not row:
        raise HTTPException(404, "Usuario nao encontrado")
    return {
        "creditos_disponiveis": row[0] or 0,
        "creditos_max": row[1] or 0,
        "plano": row[2] or "trial",
        "trial_expires_at": row[3],
    }


@router.get("/check")
async def credits_check(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Verifica se usuario pode iniciar pipeline."""
    row = db.execute(text(
        "SELECT creditos, creditos_max, plano FROM users WHERE id=:id"
    ), {"id": usuario["id"]}).fetchone()
    if not row:
        raise HTTPException(404, "Usuario nao encontrado")
    creditos = row[0] or 0
    plano = row[2] or "trial"
    is_unlimited = plano.lower() in ("ilimitado", "agency", "admin", "beta")
    role = (usuario.get("role") or "").lower()
    can_proceed = creditos > 0 or is_unlimited or role == "superadmin"
    alert = None
    if creditos == 1:
        payment_link = os.getenv("CAKTO_PAYMENT_LINK", "/planos")
        alert = {
            "message": "Ultimo ciclo disponivel. Considere fazer upgrade ou recarregar creditos.",
            "icon": "!",
            "color": "#f59e0b",
            "payment_link": payment_link,
        }
    return {
        "can_proceed": can_proceed,
        "creditos": creditos,
        "creditos_max": row[1] or 0,
        "plano": plano,
        "alert": alert,
        "is_unlimited": is_unlimited or role == "superadmin",
        "tokens_restantes": creditos,
        "reset_em": None if plano == "trial" else "proximo mes",
        "erro": None if is_unlimited or role == "superadmin" else ("Voce usou seu site gratuito. Assine um plano para continuar gerando sites." if (not can_proceed and plano == "trial") else ("Sem ciclos disponiveis. Faca upgrade ou recarregue creditos para continuar." if not can_proceed else None)),
    }