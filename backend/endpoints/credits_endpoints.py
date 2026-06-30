from decimal import Decimal, ROUND_DOWN
from typing import Optional
import hashlib
import hmac
import json
import os
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
import requests

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.domain.plans import SUBSCRIPTION_PLAN_IDS, get_plan_spec


MERCADOPAGO_API_BASE = "https://api.mercadopago.com"
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
MERCADOPAGO_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "")
RECARGA_MINIMA = Decimal("5.00")
RECARGA_MAXIMA = Decimal(os.getenv("MERCADOPAGO_RECHARGE_MAX_AMOUNT", "5000.00"))


def _payment_plan_config(plan_id: str) -> dict:
    spec = get_plan_spec(plan_id)
    amount = os.getenv(f"MERCADOPAGO_PLAN_{plan_id.upper()}_AMOUNT")
    return {
        "creditos_max": spec.monthly_credits,
        "mode": "subscription",
        "titulo": f"FraLib {spec.label}",
        "valor": float(amount or spec.monthly_brl or 0),
    }


PLANOS = {
    plan_id: _payment_plan_config(plan_id)
    for plan_id in SUBSCRIPTION_PLAN_IDS
}

PACOTES_CREDITOS = [
    {"valor": 5.00, "creditos_base": 1, "bonus_percentual": 0, "creditos_totais": 1, "custo_por_credito": 5.00},
    {"valor": 20.00, "creditos_base": 5, "bonus_percentual": 10, "creditos_totais": 5, "custo_por_credito": 4.00},
    {"valor": 50.00, "creditos_base": 15, "bonus_percentual": 20, "creditos_totais": 18, "custo_por_credito": 2.78},
    {"valor": 100.00, "creditos_base": 30, "bonus_percentual": 35, "creditos_totais": 40, "custo_por_credito": 2.50},
]

router = APIRouter(prefix="/api/credits", tags=["credits"])


class CheckoutRequest(BaseModel):
    plano: Optional[str] = Field(default=None, description="starter, pro, recarga ou tokens")
    valor: Optional[float] = Field(default=None, description="Valor livre da recarga em BRL")


class MercadoPagoSyncRequest(BaseModel):
    payment_id: Optional[str] = None
    collection_id: Optional[str] = None
    preference_id: Optional[str] = None
    preapproval_id: Optional[str] = None
    status: Optional[str] = None


def _app_url() -> str:
    return (
        os.getenv("APP_URL")
        or os.getenv("FRALIB_PUBLIC_URL")
        or "https://fralib.com"
    ).rstrip("/")


def _payment_provider() -> str:
    return "mercadopago"


def _mercadopago_headers() -> dict:
    token = os.getenv("MERCADOPAGO_ACCESS_TOKEN") or MERCADOPAGO_ACCESS_TOKEN
    if not token:
        raise HTTPException(503, "MERCADOPAGO_ACCESS_TOKEN nao configurado no backend")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _notification_url() -> str | None:
    app_url = _app_url()
    if "localhost" in app_url or "127.0.0.1" in app_url:
        return None
    return f"{app_url}/api/credits/webhook/mercadopago?source_news=webhooks"


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


def _extract_mp_signature_parts(x_signature: str) -> tuple[str | None, str | None]:
    ts = None
    v1 = None
    for part in (x_signature or "").split(","):
        key, _, value = part.strip().partition("=")
        if key == "ts":
            ts = value
        elif key == "v1":
            v1 = value
    return ts, v1


def _mercadopago_signature_valid(
    data_id: str,
    x_request_id: str,
    x_signature: str,
    secret: str,
) -> bool:
    ts, received = _extract_mp_signature_parts(x_signature)
    if not data_id or not x_request_id or not ts or not received or not secret:
        return False
    manifest = f"id:{data_id.lower()};request-id:{x_request_id};ts:{ts};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)


def _mercadopago_event_id(tipo: str, data_id: str, x_request_id: str, action: str) -> str:
    base = f"{tipo}:{data_id}:{action}:{x_request_id or uuid.uuid4().hex}"
    digest = hashlib.sha256(base.encode()).hexdigest()[:24]
    return f"mp_{digest}"


def _parse_external_reference(reference: str) -> tuple[Optional[int], Optional[str]]:
    parts = (reference or "").split(":")
    if len(parts) < 3 or parts[0] != "fralib":
        return None, None
    try:
        return int(parts[1]), parts[2]
    except (TypeError, ValueError):
        return None, parts[2] if len(parts) > 2 else None


def _mercadopago_marker_user_id(payload: dict) -> Optional[int]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    marker = metadata.get("user_id")
    if not marker:
        marker, _ = _parse_external_reference(payload.get("external_reference") or "")
    try:
        return int(marker) if marker else None
    except (TypeError, ValueError):
        return None


def _mercadopago_payload_matches_user(payload: dict, usuario: dict) -> bool:
    marker_user_id = _mercadopago_marker_user_id(payload)
    if marker_user_id is not None:
        return marker_user_id == int(usuario["id"])
    payer_email = ""
    payer = payload.get("payer")
    if isinstance(payer, dict):
        payer_email = (payer.get("email") or "").strip().lower()
    payer_email = payer_email or (payload.get("payer_email") or "").strip().lower()
    return bool(payer_email and payer_email == (usuario.get("email") or "").strip().lower())


def _upgrade_link() -> str:
    return os.getenv("MERCADOPAGO_PAYMENT_LINK") or os.getenv("PAYMENT_LINK") or "/planos.html"


@router.post("/portal")
async def criar_portal_session(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Mercado Pago nao expoe portal self-service equivalente no FraLib."""
    return {
        "provider": "mercadopago",
        "portal_url": "/planos.html",
        "message": "Gerenciamento de plano Mercado Pago: use a pagina de planos ou suporte FraLib.",
    }


@router.post("/criar-checkout")
async def criar_checkout(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    plano = (body.plano or "").strip().lower()
    if body.valor is not None:
        return _criar_recarga_mercadopago(body.valor, usuario)
    if plano in {"recarga", "tokens", "creditos"}:
        valor = float(os.getenv("MERCADOPAGO_PLAN_TOKENS_AMOUNT", "50"))
        return _criar_recarga_mercadopago(valor, usuario)
    if plano in PLANOS:
        return _criar_assinatura_mercadopago(plano, usuario)
    raise HTTPException(400, "Plano invalido. Use starter, pro, agency ou informe valor para recarga.")


def _post_mercadopago(path: str, payload: dict) -> dict:
    try:
        response = requests.post(
            f"{MERCADOPAGO_API_BASE}{path}",
            headers=_mercadopago_headers(),
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        detail = getattr(exc.response, "text", "")[:300] if getattr(exc, "response", None) is not None else str(exc)
        raise HTTPException(502, f"Mercado Pago indisponivel: {detail}")
    return response.json()


def _criar_assinatura_mercadopago(plano: str, usuario: dict) -> dict:
    config = PLANOS[plano]
    external_reference = f"fralib:{usuario['id']}:{plano}:{uuid.uuid4().hex[:12]}"
    app_url = _app_url()
    notification_url = _notification_url()
    preapproval = {
        "reason": config["titulo"],
        "external_reference": external_reference,
        "payer_email": usuario.get("email") or "",
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": config["valor"],
            "currency_id": "BRL",
        },
        "back_url": f"{app_url}/admin.html?upgrade=ok&provider=mercadopago&plano={plano}",
        "status": "pending",
    }
    if notification_url:
        preapproval["notification_url"] = notification_url
    data = _post_mercadopago("/preapproval", preapproval)
    checkout_url = data.get("init_point") or data.get("sandbox_init_point")
    if not checkout_url:
        raise HTTPException(502, "Mercado Pago nao retornou init_point da assinatura")
    return {
        "checkout_url": checkout_url,
        "provider": "mercadopago",
        "checkout_type": "subscription",
        "preapproval_id": data.get("id"),
        "plano": plano,
    }


def _criar_recarga_mercadopago(valor: float | Decimal, usuario: dict) -> dict:
    pacote = _credit_package_for_value(valor)
    external_reference = f"fralib:{usuario['id']}:recarga:{uuid.uuid4().hex[:12]}"
    app_url = _app_url()
    preference = {
        "items": [
            {
                "title": f"FraLib recarga de {pacote['creditos_totais']} creditos",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": pacote["valor"],
            }
        ],
        "payer": {"email": usuario.get("email") or ""},
        "external_reference": external_reference,
        "metadata": {
            "user_id": str(usuario["id"]),
            "plano": "recarga",
            "provider": "mercadopago",
            "valor": f"{pacote['valor']:.2f}",
            "creditos": str(pacote["creditos_totais"]),
        },
        "back_urls": {
            "success": f"{app_url}/admin.html?credits=ok&provider=mercadopago",
            "failure": f"{app_url}/admin.html?credits=cancel&provider=mercadopago",
            "pending": f"{app_url}/admin.html?credits=pending&provider=mercadopago",
        },
        "auto_return": "approved",
        "payment_methods": {
            "installments": 12,
        },
    }
    notification_url = _notification_url()
    if notification_url:
        preference["notification_url"] = notification_url
    data = _post_mercadopago("/checkout/preferences", preference)
    checkout_url = data.get("init_point") or data.get("sandbox_init_point")
    if not checkout_url:
        raise HTTPException(502, "Mercado Pago nao retornou init_point da recarga")
    return {
        "checkout_url": checkout_url,
        "provider": "mercadopago",
        "checkout_type": "recharge",
        "preference_id": data.get("id"),
        "creditos": pacote["creditos_totais"],
        "valor": pacote["valor"],
    }


def _criar_checkout_mercadopago(plano: str, usuario: dict) -> dict:
    """Compatibilidade dos testes antigos: planos viram assinatura, tokens viram recarga."""
    normalized = (plano or "").lower()
    if normalized in PLANOS:
        return _criar_assinatura_mercadopago(normalized, usuario)
    if normalized in {"tokens", "recarga", "creditos"}:
        return _criar_recarga_mercadopago(float(os.getenv("MERCADOPAGO_PLAN_TOKENS_AMOUNT", "50")), usuario)
    raise HTTPException(400, "Plano invalido")


@router.post("/sync-mercadopago")
async def sync_mercadopago_payment(
    body: MercadoPagoSyncRequest,
    usuario: dict = Depends(get_current_user),
):
    """Reconcilia retorno do Mercado Pago quando o redirect/webhook atrasar."""
    payment_id = (body.payment_id or body.collection_id or "").strip()
    preapproval_id = (body.preapproval_id or "").strip()
    if not payment_id and not preapproval_id:
        return {
            "status": "pending",
            "message": "Pagamento ainda sem identificador. Clique em Voltar a loja no Mercado Pago e aguarde a confirmacao.",
        }

    if payment_id:
        payment = _fetch_mercadopago_payment(payment_id)
        if not _mercadopago_payload_matches_user(payment, usuario):
            raise HTTPException(403, "Pagamento nao pertence ao usuario autenticado")
        if (payment.get("status") or "").lower() != "approved":
            return {
                "status": payment.get("status") or "pending",
                "provider": "mercadopago",
                "message": "Pagamento ainda nao aprovado pelo Mercado Pago.",
            }
        resolved_user_id = await _processar_evento_mercadopago(payment)
        return {
            "status": "ok",
            "provider": "mercadopago",
            "tipo": "payment",
            "user_id": resolved_user_id,
        }

    preapproval = _fetch_mercadopago_preapproval(preapproval_id)
    if not _mercadopago_payload_matches_user(preapproval, usuario):
        raise HTTPException(403, "Assinatura nao pertence ao usuario autenticado")
    resolved_user_id = await _processar_preapproval_mercadopago(preapproval)
    return {
        "status": "ok" if resolved_user_id else (preapproval.get("status") or "pending"),
        "provider": "mercadopago",
        "tipo": "preapproval",
        "user_id": resolved_user_id,
    }


@router.get("/status")
async def get_status(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    row = db.execute(text(
        "SELECT plano, creditos, creditos_max, plano_pago, trial_expires_at FROM users WHERE id=:id"
    ), {"id": usuario["id"]}).fetchone()
    if not row:
        raise HTTPException(404, "Usuario nao encontrado")
    return {
        "plano": row[0],
        "creditos": row[1],
        "creditos_max": row[2],
        "plano_pago": row[3],
        "trial_expires_at": row[4],
    }


def _resolver_user_id_mercadopago(conn, meta_user_id, external_user_id, payer_email, payer_id):
    candidatos = set()
    uid_via_payer = None
    uid_via_email = None
    for raw_uid in (external_user_id, meta_user_id):
        if raw_uid:
            try:
                candidatos.add(int(raw_uid))
            except (TypeError, ValueError):
                pass
    if payer_id:
        row = conn.execute(
            text("SELECT id FROM users WHERE mercadopago_payer_id=:payer"),
            {"payer": str(payer_id)},
        ).fetchone()
        if row:
            uid_via_payer = int(row[0])
            candidatos.add(uid_via_payer)
    if payer_email:
        row = conn.execute(text("SELECT id FROM users WHERE email=:e"), {"e": payer_email}).fetchone()
        if row:
            uid_via_email = int(row[0])
            candidatos.add(uid_via_email)
    if not candidatos:
        return None
    if len(candidatos) == 1:
        return candidatos.pop()
    print(f"[MercadoPago] CONFLITO user_id: candidatos={candidatos} email={payer_email} payer={payer_id}")
    if uid_via_payer is not None:
        return uid_via_payer
    if uid_via_email is not None:
        return uid_via_email
    return None


def _get_mercadopago(path: str) -> dict:
    try:
        response = requests.get(
            f"{MERCADOPAGO_API_BASE}{path}",
            headers=_mercadopago_headers(),
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        detail = getattr(exc.response, "text", "")[:300] if getattr(exc, "response", None) is not None else str(exc)
        raise RuntimeError(f"falha ao consultar Mercado Pago: {detail}")


def _fetch_mercadopago_payment(payment_id: str) -> dict:
    return _get_mercadopago(f"/v1/payments/{payment_id}")


def _fetch_mercadopago_preapproval(preapproval_id: str) -> dict:
    return _get_mercadopago(f"/preapproval/{preapproval_id}")


@router.post("/webhook/mercadopago")
async def mercadopago_webhook(
    request: Request,
    x_signature: str = Header(None, alias="x-signature"),
    x_request_id: str = Header(None, alias="x-request-id"),
):
    raw_payload = await request.body()
    try:
        event = json.loads(raw_payload.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        raise HTTPException(400, "Webhook invalido")

    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    data_id = (
        request.query_params.get("data.id")
        or request.query_params.get("id")
        or str(data.get("id") or event.get("id") or "").strip()
    )
    secret = os.getenv("MERCADOPAGO_WEBHOOK_SECRET") or MERCADOPAGO_WEBHOOK_SECRET
    if secret and not _mercadopago_signature_valid(data_id, x_request_id or "", x_signature or "", secret):
        print(f"[MercadoPago webhook] assinatura invalida: data_id={data_id or '-'} request_id={x_request_id or '-'}")
        raise HTTPException(400, "Webhook Mercado Pago invalido")
    if not secret and (os.getenv("FRALIB_ENV") or "").lower() == "prod":
        raise HTTPException(503, "MERCADOPAGO_WEBHOOK_SECRET nao configurado")

    tipo = (
        event.get("type")
        or event.get("topic")
        or request.query_params.get("type")
        or request.query_params.get("topic")
        or ""
    ).lower()
    action = event.get("action") or ""
    event_id = _mercadopago_event_id(tipo or "unknown", data_id, x_request_id or "", action)

    from database import engine

    with engine.connect() as conn:
        existe = conn.execute(
            text("SELECT processado FROM mercadopago_events WHERE event_id=:e"),
            {"e": event_id},
        ).fetchone()
        if existe and existe[0]:
            return {"status": "duplicado", "event_id": event_id}
        conn.execute(text("""
            INSERT INTO mercadopago_events (event_id, tipo, payment_id, processado, raw_payload)
            VALUES (:e, :t, :p, false, :raw)
            ON CONFLICT (event_id) DO NOTHING
        """), {"e": event_id, "t": tipo, "p": data_id, "raw": raw_payload.decode("utf-8", "replace")[:10000]})
        conn.commit()

    try:
        if _is_preapproval_event(tipo):
            if not data_id:
                raise HTTPException(400, "preapproval id ausente")
            preapproval = _fetch_mercadopago_preapproval(data_id)
            resolved_user_id = await _processar_preapproval_mercadopago(preapproval)
        elif (not tipo) or tipo == "payment":
            if not data_id:
                raise HTTPException(400, "payment id ausente")
            payment = _fetch_mercadopago_payment(data_id)
            resolved_user_id = await _processar_evento_mercadopago(payment)
        else:
            return {"status": "ignorado", "tipo": tipo}

        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE mercadopago_events
                SET processado=true, processado_em=NOW(), user_id=:u
                WHERE event_id=:e
            """), {"e": event_id, "u": resolved_user_id})
            conn.commit()
        return {"status": "ok", "tipo": tipo or "payment", "user_id": resolved_user_id}
    except HTTPException:
        raise  # Re-raise HTTPException para resposta correta ao MercadoPago
    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {str(exc)[:500]}"
        print(f"[MercadoPago webhook] FALHA em {tipo} ({event_id}): {err_msg}")
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE mercadopago_events SET erro=:err WHERE event_id=:e"),
                {"e": event_id, "err": err_msg},
            )
            conn.commit()
        raise HTTPException(500, f"Falha no processamento: {err_msg}")


def _is_preapproval_event(tipo: str) -> bool:
    normalized = (tipo or "").lower()
    return "preapproval" in normalized or "subscription" in normalized


def _safe_creditos_from_metadata(metadata: dict, default: int) -> int:
    try:
        creditos = int(metadata.get("creditos") or default)
    except (TypeError, ValueError):
        creditos = default
    return max(1, min(creditos, 10000))


def _ativar_plano(conn, user_id: int, plano: str, payer_id: str = "", payment_id: str = "", subscription_id: str = "") -> None:
    creditos_max = PLANOS.get(plano, {}).get("creditos_max", 5)
    conn.execute(text("""
        UPDATE users SET
            plano=:plano, plan=:plano, plano_pago=true, status='ativo',
            payment_provider='mercadopago',
            mercadopago_payer_id=COALESCE(NULLIF(:payer,''), mercadopago_payer_id),
            mercadopago_subscription_id=COALESCE(NULLIF(:sub,''), mercadopago_subscription_id),
            mercadopago_last_payment_id=COALESCE(NULLIF(:payment,''), mercadopago_last_payment_id),
            creditos=:cmax, creditos_max=:cmax,
            plan_expires_at=NOW() + INTERVAL '30 days',
            last_reset_date=CURRENT_DATE
        WHERE id=:uid
    """), {
        "plano": plano,
        "payer": payer_id,
        "sub": subscription_id,
        "payment": payment_id,
        "cmax": creditos_max,
        "uid": user_id,
    })


async def _processar_evento_mercadopago(payment: dict):
    from database import engine

    status = (payment.get("status") or "").lower()
    if status != "approved":
        return None
    metadata = payment.get("metadata") if isinstance(payment.get("metadata"), dict) else {}
    external_user_id, external_plano = _parse_external_reference(payment.get("external_reference") or "")
    plano = (metadata.get("plano") or external_plano or "starter").lower()
    payer = payment.get("payer") if isinstance(payment.get("payer"), dict) else {}
    payer_email = (payer.get("email") or "").strip()
    payer_id = str(payer.get("id") or "")
    payment_id = str(payment.get("id") or "")
    subscription_id = str(payment.get("preapproval_id") or metadata.get("preapproval_id") or "")

    with engine.connect() as conn:
        user_id = _resolver_user_id_mercadopago(
            conn,
            metadata.get("user_id"),
            external_user_id,
            payer_email,
            payer_id,
        )
        if not user_id:
            print(f"[MercadoPago] usuario nao encontrado: email={payer_email} payer={payer_id} payment={payment_id}")
            return None
        if payment_id:
            processed = conn.execute(
                text("""
                    SELECT user_id FROM mercadopago_events
                    WHERE payment_id=:payment AND processado=true
                    ORDER BY processado_em DESC, criado_em DESC
                    LIMIT 1
                """),
                {"payment": payment_id},
            ).fetchone()
            if processed:
                print(f"[MercadoPago] pagamento ja processado: payment={payment_id} user={processed[0] or user_id}")
                return processed[0] or user_id
        if plano in {"recarga", "tokens", "creditos"}:
            pacote = _credit_package_for_value(metadata.get("valor") or os.getenv("MERCADOPAGO_PLAN_TOKENS_AMOUNT", "50"))
            bonus = _safe_creditos_from_metadata(metadata, pacote["creditos_totais"])
            conn.execute(text("""
                UPDATE users SET creditos = COALESCE(creditos,0) + :bonus,
                    payment_provider='mercadopago',
                    mercadopago_payer_id=COALESCE(NULLIF(:payer,''), mercadopago_payer_id),
                    mercadopago_last_payment_id=:payment
                WHERE id=:uid
            """), {"bonus": bonus, "payer": payer_id, "payment": payment_id, "uid": user_id})
            print(f"[MercadoPago] recarga OK: user {user_id} -> +{bonus} creditos")
        elif plano in PLANOS:
            _ativar_plano(conn, user_id, plano, payer_id=payer_id, payment_id=payment_id, subscription_id=subscription_id)
            print(f"[MercadoPago] pagamento OK: user {user_id} -> plano {plano}")
        else:
            print(f"[MercadoPago] plano ignorado: {plano}")
        conn.commit()
        return user_id


async def _processar_preapproval_mercadopago(preapproval: dict):
    from database import engine

    status = (preapproval.get("status") or "").lower()
    external_user_id, external_plano = _parse_external_reference(preapproval.get("external_reference") or "")
    plano = (external_plano or "").lower()
    payer_email = (preapproval.get("payer_email") or "").strip()
    payer_id = str(preapproval.get("payer_id") or "")
    subscription_id = str(preapproval.get("id") or "")
    if plano not in PLANOS:
        return None

    with engine.connect() as conn:
        user_id = _resolver_user_id_mercadopago(conn, None, external_user_id, payer_email, payer_id)
        if not user_id:
            print(f"[MercadoPago] assinatura sem usuario: email={payer_email} payer={payer_id} sub={subscription_id}")
            return None
        if status in {"authorized", "active"}:
            _ativar_plano(conn, user_id, plano, payer_id=payer_id, subscription_id=subscription_id)
            print(f"[MercadoPago] assinatura OK: user {user_id} -> plano {plano}")
        elif status in {"cancelled", "paused", "rejected"}:
            conn.execute(text("""
                UPDATE users SET plano_pago=false, status='inadimplente',
                    mercadopago_subscription_id=COALESCE(NULLIF(:sub,''), mercadopago_subscription_id)
                WHERE id=:uid
            """), {"sub": subscription_id, "uid": user_id})
            print(f"[MercadoPago] assinatura {status}: user {user_id}")
        conn.commit()
        return user_id


@router.get("/pricing")
async def get_pricing():
    """Tabela de pacotes e contrato de recarga livre via Mercado Pago."""
    return {
        "provider": "mercadopago",
        "currency": "BRL",
        "payment_methods": ["pix", "credit_card", "debit_card"],
        "pacotes": PACOTES_CREDITOS,
        "recarga_livre": {
            "min": float(RECARGA_MINIMA),
            "max": float(RECARGA_MAXIMA),
            "default": 50.00,
            "step": 1.00,
        },
        "plans": [
            {"plano": key, "valor": value["valor"], "creditos_max": value["creditos_max"], "mode": value["mode"]}
            for key, value in PLANOS.items()
        ],
    }


@router.get("/balance")
async def credits_balance(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Retorna saldo de creditos do usuario - compatibilidade admin.html."""
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
    can_proceed = creditos > 0
    alert = None
    if creditos == 1:
        payment_link = _upgrade_link()
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
        "tokens_restantes": creditos,
        "reset_em": None if plano == "trial" else "proximo mes",
        "erro": "Voce usou seu site gratuito. Assine um plano para continuar gerando sites." if (not can_proceed and plano == "trial") else ("Sem ciclos disponiveis. Faca upgrade ou recarregue creditos para continuar." if not can_proceed else None),
    }
