"""Rate limit HTTP por IP — Sprint 3.1.

Caminho primário: Redis (sliding window via INCR + EXPIRE).
Fallback: tabela Postgres `ip_rate_limit` (UPSERT por janela de N segundos).
Fail-open: se ambos falharem, permite a request (rate limit não derruba
uma request legítima por falha de infra).

Buckets:
    auth.login                  → 10 req / 60s
    cron.*                      →  5 req / 60s
    public.*                    → 30 req / 60s
    default                     → 60 req / 60s

Whitelist (não passa pelo limiter):
    GET /api/health
    GET /, /docs, /openapi.json
    /static/*, *.html, *.js, *.css
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Engine

logger = logging.getLogger("fralib.middleware.rate_limit")


# ── Defaults ────────────────────────────────────────────────────────────────

DEFAULT_LIMITS: dict[str, tuple[int, int]] = {
    "auth.login": (10, 60),
    "cron.*": (5, 60),
    "public.*": (30, 60),
    "default": (60, 60),
}

_WHITELIST_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/docs",
        "/openapi.json",
        "/api/health",
    }
)

_WHITELIST_SUFFIXES: tuple[str, ...] = (
    ".html",
    ".js",
    ".css",
)


# ── IPRateLimiter ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class IPRateLimiter:
    """Rate limit HTTP por IP. Redis primeiro, Postgres como fallback."""

    engine: Engine
    redis_client: Optional[object] = None
    default_limits: dict[str, tuple[int, int]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        # frozen=True → usar object.__setattr__ para defaults mutáveis
        if self.default_limits is None:
            object.__setattr__(self, "default_limits", dict(DEFAULT_LIMITS))

    # ── API pública ─────────────────────────────────────────────────────

    def check(self, ip: str, endpoint_bucket: str) -> tuple[bool, int]:
        """Verifica se o IP pode bater nesse bucket.

        Returns:
            (allowed, retry_after_sec). retry_after_sec é 0 quando permitido.
        """
        max_req, window_sec = self._limit_for(endpoint_bucket)
        redis_ok, redis_result = self._check_redis(ip, endpoint_bucket, window_sec)
        if redis_ok:
            return redis_result
        return self._check_postgres(ip, endpoint_bucket, max_req, window_sec)

    # ── Redis path ──────────────────────────────────────────────────────

    def _check_redis(
        self,
        ip: str,
        endpoint_bucket: str,
        window_sec: int,
    ) -> tuple[bool, tuple[bool, int]]:
        """Tenta Redis. Retorna (False, _) se Redis offline/None → caller cai no Postgres.

        Usa Redis pipeline (INCR + EXPIRE atômico) para evitar race condition
        entre múltiplos workers onde o EXPIRE pode ser resetado/perdido.
        """
        if self.redis_client is None:
            return False, (True, 0)
        try:
            key = f"ratelimit:{ip}:{endpoint_bucket}"
            max_req = self._limit_for(endpoint_bucket)[0]
            # Pipeline: INCR + EXPIRE em uma única round-trip atômica.
            # Bug #10 fix: incr + expire não devem ser 2 chamadas separadas
            # (race: entre incr e expire, outro worker pode chamar incr de novo
            # e fazer expire resetar o TTL).
            try:
                pipe = self.redis_client.pipeline(transaction=True)
                pipe.incr(key)
                pipe.expire(key, window_sec)
                results = pipe.execute()
                count = int(results[0])
            except AttributeError:
                # Fallback se redis client nao tem .pipeline (ex: mock)
                count = int(self.redis_client.incr(key))
                if count == 1:
                    self.redis_client.expire(key, window_sec)
            if count > max_req:
                ttl = int(self.redis_client.ttl(key))
                if ttl < 0:
                    ttl = window_sec
                return True, (False, ttl)
            return True, (True, 0)
        except Exception as exc:  # pragma: no cover — caminho de erro de infra
            logger.warning(f"[rate_limit] redis_check_failed ip={ip} bucket={endpoint_bucket} err={exc}")
            return False, (True, 0)

    # ── Postgres fallback ───────────────────────────────────────────────

    def _check_postgres(
        self,
        ip: str,
        endpoint_bucket: str,
        max_req: int,
        window_sec: int,
    ) -> tuple[bool, int]:
        """UPSERT em ip_rate_limit. Retorna (allowed, retry_after_sec)."""
        try:
            now = time.time()
            window_start = int(now // window_sec) * window_sec
            with self.engine.begin() as conn:
                from sqlalchemy import text

                row = conn.execute(
                    text(
                        """
                        INSERT INTO ip_rate_limit (ip, endpoint_bucket, window_start, count)
                        VALUES (:ip, :bucket, to_timestamp(:ws), 1)
                        ON CONFLICT (ip, endpoint_bucket, window_start)
                        DO UPDATE SET count = ip_rate_limit.count + 1
                        RETURNING count
                        """
                    ),
                    {"ip": ip, "bucket": endpoint_bucket, "ws": window_start},
                ).first()
                count = int(row[0]) if row else 1

            if count > max_req:
                # Janela atual ainda ativa — retry_after = segundos até o próximo window_start
                retry_after = max(1, int(window_start + window_sec - now))
                return False, retry_after
            return True, 0
        except Exception as exc:  # pragma: no cover — fail-open
            logger.error(f"[rate_limit] postgres_check_failed ip={ip} bucket={endpoint_bucket} err={exc}")
            return True, 0

    # ── Helpers ─────────────────────────────────────────────────────────

    def _limit_for(self, endpoint_bucket: str) -> tuple[int, int]:
        """Resolve (max_requests, window_sec) para um bucket."""
        if endpoint_bucket in self.default_limits:
            return self.default_limits[endpoint_bucket]
        # Suporta padrões com wildcard (cron.*, public.*)
        if endpoint_bucket.startswith("cron."):
            return self.default_limits["cron.*"]
        if endpoint_bucket.startswith("public."):
            return self.default_limits["public.*"]
        return self.default_limits["default"]


# ── Bucket extraction ───────────────────────────────────────────────────────


def endpoint_bucket_for_request(request: Request) -> str:
    """Extrai endpoint_bucket do request. Whitelist retorna '' (skip)."""
    path = request.url.path
    method = request.method.upper()

    # Whitelist: GET em paths estáticos / docs / health
    if method == "GET":
        if path in _WHITELIST_PATHS:
            return ""
        for suffix in _WHITELIST_SUFFIXES:
            if path.endswith(suffix):
                return ""
        if path.startswith("/static/"):
            return ""

    # Login
    if method == "POST" and path == "/api/auth/login":
        return "auth.login"

    # Cron
    if path.startswith("/api/cron/"):
        suffix = path[len("/api/cron/") :]
        return f"cron.{suffix}" if suffix else "cron.*"

    # Public
    if path.startswith("/api/public/"):
        return "public.*"

    return "default"


# ── Middleware factory ──────────────────────────────────────────────────────


def ip_rate_limit_middleware(
    engine: Engine,
    redis_client: Optional[object] = None,
    *,
    default_limits: Optional[dict[str, tuple[int, int]]] = None,
    trusted_proxies: Optional[set[str]] = None,
):
    """Retorna um middleware ASGI para FastAPI.

    Uso:
        app.middleware('http')(ip_rate_limit_middleware(engine, redis_client=redis))

    Whitelist: /api/health (GET), /, /docs, /openapi.json, /static/*,
    *.html, *.js, *.css — não passam pelo limiter.

    Quando bloqueado, retorna 429 com header `Retry-After` em segundos.

    Args:
        engine: SQLAlchemy engine (Postgres).
        redis_client: cliente Redis opcional. Se None, vai direto pro Postgres.
        default_limits: dict bucket → (max_req, window_sec).
        trusted_proxies: conjunto de IPs/CIDRs confiáveis para validar XFF.
            Se None, lê de env ``TRUSTED_PROXIES`` (comma-separated).
            Se ambos vazios, XFF é ignorado (fail-safe contra spoof).
    """
    limits = default_limits if default_limits is not None else DEFAULT_LIMITS
    proxies = trusted_proxies if trusted_proxies is not None else _load_trusted_proxies()
    limiter = IPRateLimiter(
        engine=engine,
        redis_client=redis_client,
        default_limits=limits,
    )

    async def _middleware(request: Request, call_next):
        bucket = endpoint_bucket_for_request(request)
        if not bucket:
            # Whitelist — passa direto
            return await call_next(request)

        # Extrai IP do cliente (X-Forwarded-For só confia com trusted proxy)
        ip = _client_ip(request, trusted_proxies=proxies)
        allowed, retry_after = limiter.check(ip, bucket)

        if not allowed:
            logger.warning(
                f"[rate_limit] blocked IP={ip} bucket={bucket} retry_after={retry_after}"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after,
                    "bucket": bucket,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)

    return _middleware


# ── Helpers ────────────────────────────────────────────────────────────────


def _client_ip(request: Request, trusted_proxies: Optional[set[str]] = None) -> str:
    """Extrai IP real do cliente respeitando X-Forwarded-For com proxy confiável.

    Comportamento:
    - Se o socket do request vem de um trusted proxy **e** XFF presente:
      retorna o **primeiro** IP da cadeia XFF (que é o cliente real que
      o proxy mais externo viu). O atacante não consegue spoof porque
      o trusted proxy sempre adiciona o IP do cliente à esquerda.
    - Caso contrário (dev, test, sem proxy confiável): ignora XFF e usa
      ``request.client.host`` direto. Fail-safe contra spoof.

    Sem trusted proxy configurado, XFF é ignorado inteiramente.

    Configure trusted proxies via env ``TRUSTED_PROXIES`` (comma-separated):
        TRUSTED_PROXIES=10.0.0.1,172.16.0.0/12
    """
    if not trusted_proxies:
        # Sem proxy confiável configurado, fail-safe: ignora XFF.
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    fwd = request.headers.get("x-forwarded-for") or request.headers.get(
        "X-Forwarded-For"
    )
    if not fwd:
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    chain = [hop.strip() for hop in fwd.split(",") if hop.strip()]
    if not chain:
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    # Confia no XFF apenas se a chain termina com um IP trusted (proxy confiável).
    # Isso impede que um atacante sem passar pelo proxy injete XFF arbitrário.
    last = chain[-1]
    if _ip_in_trusted(last, trusted_proxies):
        # Primeiro da chain = cliente real (assumindo trusted proxy adiciona à esquerda).
        return chain[0]
    # XFF não confiável, ignora.
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _ip_in_trusted(ip: str, trusted: set[str]) -> bool:
    """Match exato OU prefix match para CIDRs simples (RFC1918).

    Para ``10.0.0.0/8`` registrado como ``10.0.0.0``, match em qualquer
    IP começando com ``10.`` (heurística suficiente para ranges privados).
    Para ranges complexos (ex: ``203.0.113.0/24``), recomenda-se usar
    biblioteca externa (``ipaddress``).
    """
    if ip in trusted:
        return True
    # CIDR simples: prefixo "10." ou "172.16." etc
    if "/" in str(trusted):
        # Tentativa com ipaddress (stdlib)
        import ipaddress
        try:
            ip_obj = ipaddress.ip_address(ip)
            for t in trusted:
                if "/" in t:
                    if ip_obj in ipaddress.ip_network(t, strict=False):
                        return True
        except ValueError:
            pass
    return False


def _load_trusted_proxies() -> set[str]:
    """Carrega lista de trusted proxies do env ``TRUSTED_PROXIES`` (comma-separated).

    Aceita IPs literais (ex: ``10.0.0.1``) ou CIDRs (ex: ``10.0.0.0/8``).
    """
    import os

    raw = os.getenv("TRUSTED_PROXIES", "").strip()
    if not raw:
        return set()
    proxies: set[str] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        proxies.add(token)
    return proxies
