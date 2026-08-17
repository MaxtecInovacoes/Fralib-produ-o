"""
Webhook Cakto — processa eventos de pagamento, assinatura e afiliados.

Eventos: purchase_approved, purchase_refused, subscription_created,
subscription_canceled, subscription_renewed, subscription_renewal_refused,
pix_gerado, chargeback, refund.
"""
import hashlib
import hmac
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import text

from backend.core.database import engine as _engine
from backend.domain.plans import PLAN_SPECS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/credits", tags=["credits-webhook"])

CAKTO_WEBHOOK_SECRET = os.getenv("CAKTO_WEBHOOK_SECRET", "")


def _webhook_secret_valid(
    payload_body: bytes, x_cakto_hash: Optional[str]
) -> bool:
    """Valida hash SHA256 do webhook Cakto."""
    if not CAKTO_WEBHOOK_SECRET:
        logger.warning("CAKTO_WEBHOOK_SECRET nao configurado — webhook sem validacao")
        return True  # Dev/staging sem secret
    if not x_cakto_hash or not payload_body:
        return False
    expected = hmac.new(
        CAKTO_WEBHOOK_SECRET.encode("utf-8"), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, x_cakto_hash)


def _ativar_plano(conn, user_id: int, plano: str, subscription_id: str = "",
                  payment_id: str = "") -> None:
    """Ativa plano no usuario apos pagamento aprovado."""
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


@router.post("/webhook/cakto")
async def cakto_webhook(
    request: Request,
    x_cakto_hash: Optional[str] = Header(None, alias="x-cakto-hash"),
):
    """Processa webhook de pagamento/assinatura do Cakto."""
    raw_payload = await request.body()
    try:
        event = json.loads(raw_payload.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        raise HTTPException(400, "Webhook invalido")

    if not _webhook_secret_valid(raw_payload, x_cakto_hash):
        logger.warning("cakto_webhook_invalid_hash")
        raise HTTPException(400, "Assinatura webhook invalida")

    # Cakto envolve todo payload dentro de "data"
    data = event.get("data", {})

    evento = event.get("event", "")
    order_id = str(data.get("id") or data.get("order_id") or "")
    subscription_obj = data.get("subscription")
    subscription_id = str(subscription_obj.get("id")) if isinstance(subscription_obj, dict) else ""
    customer = data.get("customer", {}) if isinstance(data.get("customer"), dict) else {}

    # User identity do customer metadata
    customer_email = (customer.get("email") or event.get("customer_email") or "").strip().lower()
    external_ref = data.get("refId") or data.get("external_reference") or ""

    # Extrai user_id do external_reference: "fralib:{user_id}:{plano}:{order_id}"
    # ou "fralib:{user_id}:pix:{plano}:{uuid}" para pagamentos avulsos
    user_id = None
    plano = ""
    if external_ref:
        parts = external_ref.split(":")
        if len(parts) >= 3 and parts[0] == "fralib":
            try:
                user_id = int(parts[1])
            except (ValueError, TypeError):
                pass
            # Pula prefixo "pix" ou "recarga" se presente
            if len(parts) >= 4 and parts[2] in ("pix", "recarga"):
                plano = parts[3] if len(parts) >= 4 else ""
            else:
                plano = parts[2] if len(parts) >= 3 else ""

    # Dados de afiliado: pode vir como string (email) ou dict
    affiliate_raw = data.get("affiliate")
    if isinstance(affiliate_raw, dict):
        affiliate_data = affiliate_raw
    elif isinstance(affiliate_raw, str):
        affiliate_data = {"email": affiliate_raw} if affiliate_raw else None
    else:
        affiliate_data = None

    commissions = data.get("commissions") if isinstance(data.get("commissions"), list) else None

    logger.info(
        "cakto_webhook_received",
        extra={
            "evento": evento,
            "order_id": order_id,
            "subscription_id": subscription_id,
            "user_id": user_id,
            "plano": plano,
        },
    )

    # Idempotency: registra order_id em cakto_events ANTES de processar.
    # Se ja existe, webhook Cakto reenviou — retorna duplicate sem efeitos colaterais.
    if order_id:
        with _engine.begin() as idem_conn:
            # Ensure source column exists (cakto_events schema fix)
            result = idem_conn.execute(text("""
                INSERT INTO cakto_events (order_id, event_type, source, payload, user_id, plano)
                VALUES (:oid, :ev, 'webhook', CAST(:payload AS jsonb), :uid, :plano)
                ON CONFLICT (order_id) DO NOTHING
            """), {
                "oid": order_id,
                "ev": evento,
                "payload": json.dumps(event),
                "uid": user_id,
                "plano": plano or None,
            })
            if result.rowcount == 0:
                logger.info("cakto_webhook_duplicate", extra={"order_id": order_id, "evento": evento})
                return {"status": "duplicate", "order_id": order_id, "evento": evento}

    with _engine.begin() as conn:
        # Resolve user_id se veio via email
        if not user_id and customer_email:
            row = conn.execute(
                text("SELECT id FROM users WHERE email=:e LIMIT 1"),
                {"e": customer_email},
            ).fetchone()
            if row:
                user_id = int(row[0])

        if not user_id:
            logger.error("cakto_webhook_user_not_found", extra={"evento": evento, "email": customer_email})
            return {"status": "ok", "evento": evento}

        if evento == "purchase_approved":
            if not plano:
                logger.warning("cakto_webhook_no_plan_for_purchase_approved", extra={"order_id": order_id, "user_id": user_id})
                return {"status": "ok", "evento": evento}

            _ativar_plano(conn, user_id, plano or "starter",
                          subscription_id=subscription_id,
                          payment_id=order_id)

            # Se tem dados de afiliado, registra
            if affiliate_data:
                conn.execute(text("""
                    INSERT INTO affiliate_commissions
                        (user_id, order_id, affiliate_id, affiliate_name, commission_value, created_at)
                    VALUES (:uid, :oid, :aid, :aname, :cvalue, NOW())
                    ON CONFLICT (order_id) DO NOTHING
                """), {
                    "uid": user_id, "oid": order_id,
                    "aid": affiliate_data.get("id", ""),
                    "aname": affiliate_data.get("name", ""),
                    "cvalue": affiliate_data.get("commission_value", 0),
                })

            logger.info("cakto_subscription_activated", extra={"user_id": user_id, "plano": plano})

        elif evento == "purchase_refused":
            logger.warning("cakto_purchase_refused", extra={"user_id": user_id, "order_id": order_id})

        elif evento in ("subscription_canceled", "subscription_renewal_refused"):
            # Inicia grace period de 5 dias
            conn.execute(text("""
                UPDATE users SET plano_pago=false, status='past_due',
                    past_due_since=COALESCE(past_due_since, NOW())
                WHERE id=:uid
            """), {"uid": user_id})
            logger.info("cakto_subscription_past_due", extra={"user_id": user_id, "evento": evento})

        elif evento == "chargeback":
            conn.execute(text("""
                UPDATE users SET status='suspenso', chargeback_flag=true
                WHERE id=:uid
            """), {"uid": user_id})
            logger.warning("cakto_chargeback", extra={"user_id": user_id, "order_id": order_id})

        elif evento == "refund":
            logger.info("cakto_refund", extra={"user_id": user_id, "order_id": order_id})

        # Eventos informativos
        elif evento in ("subscription_created", "subscription_renewed", "pix_gerado"):
            logger.info(f"cakto_{evento}", extra={"user_id": user_id, "subscription_id": subscription_id})

    return {"status": "ok", "evento": evento}