"""Unit tests for backend.middleware.rate_limit (Sprint 3.1).

Cobre:
  - IPRateLimiter.check() — caminho Redis (INCR + EXPIRE)
  - IPRateLimiter.check() — fallback Postgres (Redis None)
  - endpoint_bucket_for_request — extração de bucket + whitelist
  - Middleware FastAPI — 429 com Retry-After
  - Fail-open quando Redis E Postgres falham

Convenções:
  - pytest.mark.unit em todas as classes
  - MagicMock para engine e redis_client
  - httpx.AsyncClient para testes de middleware
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# Path setup — middleware mora em backend/middleware/, testes em tests/unit/
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))

from middleware.rate_limit import (  # noqa: E402
    IPRateLimiter,
    endpoint_bucket_for_request,
    ip_rate_limit_middleware,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. IPRateLimiter.check() — caminho Redis puro
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestRedisPath:
    """Sliding window via Redis: INCR + EXPIRE."""

    def test_redis_path_allows_under_limit(self):
        redis = MagicMock()
        # INCR retorna 1 (primeiro hit, dentro do limite)
        redis.incr.return_value = 1
        redis.expire.return_value = True

        limiter = IPRateLimiter(engine=MagicMock(), redis_client=redis)
        allowed, retry_after = limiter.check("1.2.3.4", "auth.login")

        assert allowed is True
        assert retry_after == 0
        redis.incr.assert_called_once()
        redis.expire.assert_called_once()

    def test_redis_path_blocks_over_limit(self):
        redis = MagicMock()
        # 11º hit — acima do limite de 10 para auth.login
        redis.incr.return_value = 11
        redis.ttl.return_value = 42  # segundos restantes na chave

        limiter = IPRateLimiter(engine=MagicMock(), redis_client=redis)
        allowed, retry_after = limiter.check("1.2.3.4", "auth.login")

        assert allowed is False
        assert retry_after == 42
        redis.ttl.assert_called()

    def test_redis_path_uses_bucket_limit(self):
        """Cada bucket tem seu próprio (max_requests, window_sec)."""
        redis = MagicMock()
        redis.incr.return_value = 6  # > 5 do bucket cron.*
        redis.ttl.return_value = 30

        limiter = IPRateLimiter(engine=MagicMock(), redis_client=redis)
        allowed, retry_after = limiter.check("1.2.3.4", "cron.refresh-provider-health")

        assert allowed is False
        assert retry_after == 30


# ─────────────────────────────────────────────────────────────────────────────
# 2. endpoint_bucket_for_request — extração + whitelist
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestEndpointBucketExtraction:
    """Mapeia método+path → endpoint_bucket."""

    def test_login_endpoint(self):
        req = MagicMock()
        req.method = "POST"
        req.url.path = "/api/auth/login"
        assert endpoint_bucket_for_request(req) == "auth.login"

    def test_cron_endpoint(self):
        req = MagicMock()
        req.method = "POST"
        req.url.path = "/api/cron/refresh-provider-health"
        assert endpoint_bucket_for_request(req) == "cron.refresh-provider-health"

    def test_whitelist_health_endpoint(self):
        req = MagicMock()
        req.method = "GET"
        req.url.path = "/api/health"
        # Whitelist retorna string vazia → middleware não aplica limite
        assert endpoint_bucket_for_request(req) == ""

    def test_public_endpoint_returns_wildcard(self):
        req = MagicMock()
        req.method = "GET"
        req.url.path = "/api/public/some-page"
        assert endpoint_bucket_for_request(req) == "public.*"

    def test_unknown_endpoint_returns_default(self):
        req = MagicMock()
        req.method = "GET"
        req.url.path = "/api/admin/health"
        assert endpoint_bucket_for_request(req) == "default"

    def test_static_assets_whitelisted(self):
        for path in ("/", "/static/logo.png", "/app.js", "/styles.css", "/docs", "/openapi.json"):
            req = MagicMock()
            req.method = "GET"
            req.url.path = path
            assert endpoint_bucket_for_request(req) == "", f"{path} deveria estar na whitelist"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Fallback Postgres — Redis offline
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPostgresFallback:
    """Quando redis_client é None, usar tabela ip_rate_limit via UPSERT."""

    def test_redis_offline_uses_postgres(self):
        engine = MagicMock()
        conn = MagicMock()
        engine.begin.return_value.__enter__.return_value = conn
        # rowcount = 1 → primeira inserção na janela (ainda não atingiu limite)
        conn.execute.return_value.rowcount = 1

        limiter = IPRateLimiter(engine=engine, redis_client=None)
        allowed, retry_after = limiter.check("1.2.3.4", "auth.login")

        assert allowed is True
        assert retry_after == 0
        engine.begin.assert_called_once()

    def test_postgres_window_resets_after_window_sec(self):
        """Próxima janela (window_start novo) começa com count=1, mesmo IP."""
        engine = MagicMock()
        conn = MagicMock()
        engine.begin.return_value.__enter__.return_value = conn
        conn.execute.return_value.rowcount = 1  # primeira inserção da nova janela

        limiter = IPRateLimiter(engine=engine, redis_client=None)
        allowed, _ = limiter.check("5.6.7.8", "public.*")

        assert allowed is True
        # O SQL executado deve incluir ON CONFLICT (upsert) na janela
        assert conn.execute.called


# ─────────────────────────────────────────────────────────────────────────────
# 4. Fail-open — Postgres E Redis falhando
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestFailOpen:
    """Infra caída não pode derrubar request legítima."""

    def test_redis_failure_falls_back_to_postgres(self):
        redis = MagicMock()
        redis.incr.side_effect = ConnectionError("redis offline")
        engine = MagicMock()
        conn = MagicMock()
        engine.begin.return_value.__enter__.return_value = conn
        conn.execute.return_value.rowcount = 1

        limiter = IPRateLimiter(engine=engine, redis_client=redis)
        allowed, retry_after = limiter.check("1.2.3.4", "auth.login")

        # Cai no Postgres — request permitida
        assert allowed is True
        assert retry_after == 0

    def test_postgres_failure_fails_open(self):
        """Se Postgres também falha → allow (não derruba request legítima)."""
        redis = MagicMock()
        redis.incr.side_effect = ConnectionError("redis offline")
        engine = MagicMock()
        engine.begin.side_effect = Exception("postgres offline")

        limiter = IPRateLimiter(engine=engine, redis_client=redis)
        allowed, retry_after = limiter.check("1.2.3.4", "auth.login")

        # Fail-open: permite a request
        assert allowed is True
        assert retry_after == 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Middleware FastAPI — integração via httpx.AsyncClient
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
class TestMiddlewareIntegration:
    """Testa o middleware completo: 200 / 401 / 429 com Retry-After."""

    async def _make_client(self, redis_mock, engine_mock):
        app = FastAPI()
        # Registra o middleware sob o mesmo engine/redis dos mocks
        app.middleware("http")(ip_rate_limit_middleware(engine_mock, redis_client=redis_mock))

        @app.post("/api/auth/login")
        async def login():
            from fastapi.responses import JSONResponse
            # 401 normal — o middleware injeta 429 se limite for excedido
            return JSONResponse(status_code=401, content={"detail": "invalid credentials"})

        @app.post("/api/cron/refresh-provider-health")
        async def cron():
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=403, content={"detail": "forbidden"})

        @app.get("/api/health")
        async def health():
            return {"status": "ok"}

        @app.get("/api/public/page")
        async def public_page():
            return {"ok": True}

        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    async def test_allows_first_5_logins_in_a_minute(self):
        redis = MagicMock()
        # Simula 5 hits, todos abaixo do limite (1..5)
        redis.incr.side_effect = list(range(1, 6))
        redis.expire.return_value = True
        engine = MagicMock()

        async with await self._make_client(redis, engine) as client:
            statuses = []
            for _ in range(5):
                resp = await client.post("/api/auth/login")
                statuses.append(resp.status_code)
            assert all(s == 401 for s in statuses), statuses

    async def test_blocks_11th_login_returns_429(self):
        redis = MagicMock()
        # Simula sequência de hits: 1,2,...,10 (allow), 11 (block)
        redis.incr.side_effect = list(range(1, 12))
        redis.expire.return_value = True
        redis.ttl.return_value = 25
        engine = MagicMock()

        async with await self._make_client(redis, engine) as client:
            # 10 primeiros → 401
            for _ in range(10):
                resp = await client.post("/api/auth/login")
                assert resp.status_code == 401
            # 11º → 429
            resp = await client.post("/api/auth/login")
            assert resp.status_code == 429

    async def test_retry_after_header_present_on_429(self):
        redis = MagicMock()
        redis.incr.side_effect = list(range(1, 12))
        redis.expire.return_value = True
        redis.ttl.return_value = 17
        engine = MagicMock()

        async with await self._make_client(redis, engine) as client:
            for _ in range(10):
                await client.post("/api/auth/login")
            resp = await client.post("/api/auth/login")
            assert resp.status_code == 429
            assert "Retry-After" in resp.headers
            assert resp.headers["Retry-After"] == "17"

    async def test_cron_endpoint_5_per_minute_limit(self):
        redis = MagicMock()
        # cron.* tem limite 5 — hits 1..5 (allow), 6 (block)
        redis.incr.side_effect = list(range(1, 7))
        redis.expire.return_value = True
        redis.ttl.return_value = 30
        engine = MagicMock()

        async with await self._make_client(redis, engine) as client:
            for _ in range(5):
                resp = await client.post("/api/cron/refresh-provider-health")
                assert resp.status_code == 403
            resp = await client.post("/api/cron/refresh-provider-health")
            assert resp.status_code == 429

    async def test_health_endpoint_not_rate_limited(self):
        """Whitelist: /api/health (GET) não passa pelo Redis."""
        redis = MagicMock()
        redis.incr.return_value = 1
        engine = MagicMock()

        async with await self._make_client(redis, engine) as client:
            for _ in range(20):
                resp = await client.get("/api/health")
                assert resp.status_code == 200
            # Redis.incr NUNCA deve ser chamado para health
            redis.incr.assert_not_called()
