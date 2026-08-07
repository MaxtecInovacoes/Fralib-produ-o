"""
Cakto API HTTP client — assinaturas, pagamentos, afiliados.

API: https://api.cakto.com.br/public_api/
Auth: OAuth2 client_credentials → Bearer token (10h expiry, sem refresh endpoint).
"""
import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class CaktoError(Exception):
    """Erro base da API Cakto."""


class CaktoAuthError(CaktoError):
    """Falha de autenticacao."""


class CaktoNotFoundError(CaktoError):
    """Recurso nao encontrado (404)."""


class CaktoValidationError(CaktoError):
    """Erro de validacao (422)."""


@dataclass
class CaktoClient:
    """Cliente HTTP para API Cakto com cache de token OAuth2."""

    _client_id: str = field(default_factory=lambda: os.getenv("CAKTO_CLIENT_ID", ""))
    _client_secret: str = field(default_factory=lambda: os.getenv("CAKTO_CLIENT_SECRET", ""))
    _base_url: str = "https://api.cakto.com.br/public_api"
    _token: Optional[str] = None
    _token_expires_at: float = 0.0

    @property
    def is_configured(self) -> bool:
        return bool(self._client_id) and bool(self._client_secret)

    def _token_valid(self) -> bool:
        return bool(self._token) and time.time() < self._token_expires_at - 120

    async def authenticate(self) -> None:
        """OAuth2 client_credentials grant."""
        if not self.is_configured:
            raise CaktoAuthError("CAKTO_CLIENT_ID e CAKTO_CLIENT_SECRET obrigatorios no .env")

        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{self._base_url}/token/",
                data={"client_id": self._client_id, "client_secret": self._client_secret},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if r.status_code != 200:
            raise CaktoAuthError(
                f"Falha autenticacao Cakto: HTTP {r.status_code} {r.text[:200]}"
            )
        data = r.json()
        self._token = data.get("access_token")
        if not self._token:
            raise CaktoAuthError("Resposta de token sem access_token")
        expires_in = data.get("expires_in", 36000)  # 10h default
        self._token_expires_at = time.time() + expires_in
        logger.info("cakto_auth_ok", extra={"expires_in_s": expires_in})

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        if not self._token_valid():
            await self.authenticate()

        url = f"{self._base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        async with httpx.AsyncClient(timeout=kwargs.pop("timeout", 20)) as client:
            r = await client.request(method, url, headers=headers, **kwargs)

        # Token expirado (401) — tenta renovar uma vez
        if r.status_code == 401:
            logger.info("cakto_token_expired_reauthenticating")
            await self.authenticate()
            headers["Authorization"] = f"Bearer {self._token}"
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.request(method, url, headers=headers, **kwargs)

        if r.status_code == 404:
            raise CaktoNotFoundError(f"{method} {path}: 404")
        if r.status_code == 422:
            body = r.text[:500]
            raise CaktoValidationError(f"{method} {path}: 422 {body}")
        if r.status_code >= 400:
            body = r.text[:500]
            raise CaktoError(f"{method} {path}: {r.status_code} {body}")

        if not r.text.strip():
            return {}
        return r.json()

    # ── Products ──────────────────────────────────────────────────────────────

    async def create_product(
        self,
        name: str,
        description: str,
        type_: str = "subscription",
        category: str = "software",
        guarantee_days: int = 7,
    ) -> dict:
        """Cria produto no Cakto."""
        return await self._request("POST", "/products/", json={
            "name": name,
            "description": description,
            "type": type_,
            "category": category,
            "guarantee_days": guarantee_days,
        })

    async def get_product(self, product_id: str) -> dict:
        return await self._request("GET", f"/products/{product_id}/")

    async def list_products(self) -> list[dict]:
        return await self._request("GET", "/products/")

    # ── Offers ────────────────────────────────────────────────────────────────

    async def create_offer(
        self,
        name: str,
        price: float,
        product_id: str,
        trial_days: int = 0,
        recurrence_period: str = "monthly",
        quantity_recurrences: int = 0,
        max_retries: int = 3,
        retry_interval: int = 3,
        external_reference: str = "",
    ) -> dict:
        """Cria oferta (preco + trial + recorrencia) para um produto.

        Retorna dict com ``id`` da oferta — checkout URL e ``pay.cakto.com.br/{id}``.
        """
        payload = {
            "name": name,
            "price": price,
            "product_id": product_id,
            "trial_days": trial_days,
            "recurrence_period": recurrence_period,
            "quantity_recurrences": quantity_recurrences,
            "max_retries": max_retries,
            "retry_interval": retry_interval,
        }
        if external_reference:
            payload["external_reference"] = external_reference
        return await self._request("POST", "/offers/", json=payload)

    async def get_offer(self, offer_id: str) -> dict:
        return await self._request("GET", f"/offers/{offer_id}/")

    async def list_offers(self, **params) -> list[dict]:
        return await self._request("GET", "/offers/", params=params or None)

    # ── Subscriptions ─────────────────────────────────────────────────────────

    async def create_subscription(
        self,
        offer_id: str,
        customer: dict,
        payment_method: str = "credit_card",
        external_reference: str = "",
    ) -> dict:
        """Cria assinatura manualmente (quando usuario ja foi checkout externo).

        ``customer``: {"name", "email", "phone", "document"}.
        ``payment_method``: "credit_card" | "pix" | "boleto".
        ``external_reference``: Referencia externa para vincular ao webhook (ex: "fralib:123:starter:order_abc").
        """
        payload = {
            "offer_id": offer_id,
            "customer": customer,
            "payment_method": payment_method,
        }
        if external_reference:
            payload["external_reference"] = external_reference
        return await self._request("POST", "/subscriptions/", json=payload)

    async def get_subscription(self, subscription_id: str) -> dict:
        return await self._request("GET", f"/subscriptions/{subscription_id}/")

    async def list_subscriptions(self, **params) -> list[dict]:
        return await self._request("GET", "/subscriptions/", params=params or None)

    async def cancel_subscription(self, subscription_id: str) -> dict:
        return await self._request("POST", f"/subscriptions/{subscription_id}/cancel/")

    async def change_payment_method(
        self, subscription_id: str, payment_method: str
    ) -> dict:
        """Altera forma de pagamento: "credit_card" | "pix" | "boleto"."""
        return await self._request(
            "POST",
            f"/subscriptions/{subscription_id}/change-payment-method/",
            json={"payment_method": payment_method},
        )

    # ── Orders ────────────────────────────────────────────────────────────────

    async def get_order(self, order_id: str) -> dict:
        return await self._request("GET", f"/orders/{order_id}/")

    # ── Webhooks ──────────────────────────────────────────────────────────────

    async def create_webhook(self, event: str, url: str) -> dict:
        """Registra webhook para evento especifico.

        Eventos: purchase_approved, purchase_refused, subscription_created,
        subscription_canceled, subscription_renewed, subscription_renewal_refused,
        pix_gerado, chargeback, refund.
        """
        return await self._request("POST", "/webhooks/", json={
            "event": event,
            "url": url,
        })

    @staticmethod
    def webhook_validate(
        secret: str, payload_body: bytes, received_hash: str
    ) -> bool:
        """Valida hash SHA256 do webhook Cakto (header ``x-cakto-hash``).

        Expected = SHA256(payload_body + webhook_secret).
        """
        if not secret or not payload_body or not received_hash:
            return False
        expected = hashlib.sha256(
            payload_body + secret.encode("utf-8")
        ).hexdigest()
        return hmac.compare_digest(expected, received_hash)


# ── Singleton factory ─────────────────────────────────────────────────────────

_client_instance: Optional[CaktoClient] = None


def get_cakto_client() -> CaktoClient:
    """Retorna singleton do CaktoClient."""
    global _client_instance
    if _client_instance is None:
        _client_instance = CaktoClient()
    return _client_instance


async def ensure_cakto_authenticated() -> bool:
    """Autentica se necessario. Retorna False se credenciais ausentes."""
    client = get_cakto_client()
    if not client.is_configured:
        logger.warning("CAKTO_CLIENT_ID/CAKTO_CLIENT_SECRET nao configurados")
        return False
    if not client._token_valid():
        await client.authenticate()
    return True
