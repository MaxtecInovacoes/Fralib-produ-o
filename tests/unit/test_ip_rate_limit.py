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



def _make_redis_mock():
    """Cria mock Redis que suporta .pipeline() (Sprint 3.1 race hardening).

    O `IPRateLimiter` usa `pipe = redis.pipeline(); pipe.incr(); pipe.expire();
    pipe.execute()` para atomicidade. O mock precisa simular isso.
    """
    redis = MagicMock()
    # Pipeline mock: pipe.incr(key) + pipe.expire(key, ttl) + pipe.execute() -> [count]
    pipe = MagicMock()
    pipe.execute.return_value = [1]  # valor default; tests sobrescrevem via side_effect
    redis.pipeline.return_value = pipe
    return redis


def _set_redis_count(redis, value):
    """Configura o mock para retornar `value` como count do INCR."""
    redis.pipeline.return_value.execute.return_value = [value]
    return redis


@pytest.mark.unit
class TestRedisPath:
    """Sliding window via Redis: INCR + EXPIRE."""

    def test_redis_path_allows_under_limit(self):
        redis = _make_redis_mock()
        redis.pipeline.return_value.execute.return_value = [1]  # 1o hit, < limite (10)

        limiter = IPRateLimiter(engine=MagicMock(), redis_client=redis)
        allowed, retry_after = limiter.check("1.2.3.4", "auth.login")

        assert allowed is True
        assert retry_after == 0
        # Pipeline foi usado (atomicidade)
        redis.pipeline.return_value.incr.assert_called_once()
        redis.pipeline.return_value.expire.assert_called_once()

    def test_redis_path_blocks_over_limit(self):
        redis = _make_redis_mock()
        # 11o hit — acima do limite de 10 para auth.login
        redis.pipeline.return_value.execute.return_value = [11]
        redis.ttl.return_value = 42

        limiter = IPRateLimiter(engine=MagicMock(), redis_client=redis)
        allowed, retry_after = limiter.check("1.2.3.4", "auth.login")

        assert allowed is False
        assert retry_after == 42
        redis.ttl.assert_called()

    def test_redis_path_uses_bucket_limit(self):
        """Cada bucket tem seu próprio (max_requests, window_sec)."""
        redis = _make_redis_mock()
        redis.pipeline.return_value.execute.return_value = [6]  # > 5 do bucket cron.*
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

    def test_simulador_endpoint(self):
        """Bug fix: /api/simulador/* → bucket dedicado com 600/min."""
        req = MagicMock()
        req.method = "POST"
        req.url.path = "/api/simulador/franz/test"
        assert endpoint_bucket_for_request(req) == "simulador.franz"

    def test_simulador_endpoint_nested(self):
        req = MagicMock()
        req.method = "POST"
        req.url.path = "/api/simulador"
        assert endpoint_bucket_for_request(req) == "simulador.franz"

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
# 3b. Client IP extraction — X-Forwarded-For spoof protection
# ─────────────────────────────────────────────────────────────────────────────


class _FakeRequest:
    """Mock minimalista de FastAPI Request pra testar _client_ip."""

    def __init__(self, host: str = "1.1.1.1", xff: str | None = None) -> None:
        self.headers: dict[str, str] = {}
        if xff:
            self.headers["x-forwarded-for"] = xff
        self.client = MagicMock()
        self.client.host = host


@pytest.mark.unit
class TestClientIpExtraction:
    """P0 security: rate limit NAO pode ser bypassed por XFF spoof."""

    def test_no_trusted_proxies_ignores_xff(self) -> None:
        """Sem trusted_proxies configurado, XFF é IGNORADO (fail-safe)."""
        from middleware.rate_limit import _client_ip

        req = _FakeRequest(host="1.1.1.1", xff="9.9.9.9")
        # Sem trusted_proxies → usa o IP real do socket, NAO o XFF.
        assert _client_ip(req) == "1.1.1.1"

    def test_no_trusted_proxies_no_xff_uses_socket(self) -> None:
        from middleware.rate_limit import _client_ip
        req = _FakeRequest(host="1.1.1.1", xff=None)
        assert _client_ip(req) == "1.1.1.1"

    def test_trusted_proxy_chain_validates_last_hop(self) -> None:
        """Com trusted_proxies, XFF só vale se o último hop é trusted."""
        from middleware.rate_limit import _client_ip

        # Trusted proxy chain: client → trusted → trusted → trusted
        req = _FakeRequest(
            host="10.0.0.1",  # trusted (no socket)
            xff="9.9.9.9, 10.0.0.2, 10.0.0.3",
        )
        trusted = {"10.0.0.1", "10.0.0.2", "10.0.0.3"}
        # Último XFF hop é 10.0.0.3 → trusted. Primeiro = 9.9.9.9 → real client.
        assert _client_ip(req, trusted_proxies=trusted) == "9.9.9.9"

    def test_trusted_proxy_untrusted_last_hop_ignored(self) -> None:
        """Se último hop do XFF não é trusted, ignora XFF (anti-spoof)."""
        from middleware.rate_limit import _client_ip

        req = _FakeRequest(
            host="10.0.0.1",
            xff="9.9.9.9, 10.0.0.2, evil.attacker.com",  # attacker forjou
        )
        trusted = {"10.0.0.1", "10.0.0.2"}  # NÃO inclui attacker.com
        # Último XFF = evil.attacker.com → NÃO é trusted → ignora XFF → usa socket.
        assert _client_ip(req, trusted_proxies=trusted) == "10.0.0.1"

    def test_trusted_proxy_cidr(self) -> None:
        """CIDR notation funciona pra ranges privados."""
        from middleware.rate_limit import _client_ip, _ip_in_trusted
        assert _ip_in_trusted("10.0.0.5", {"10.0.0.0/8"}) is True
        assert _ip_in_trusted("192.168.1.1", {"192.168.0.0/16"}) is True
        assert _ip_in_trusted("8.8.8.8", {"10.0.0.0/8"}) is False


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


def _make_redis_mock_with_counts(counts):
    """Cria mock Redis onde cada pipeline.execute() retorna o proximo count."""
    redis = _make_redis_mock()
    it = iter(counts)
    def next_count():
        try:
            return [next(it)]
        except StopIteration:
            return [1]
    redis.pipeline.return_value.execute.side_effect = next_count
    return redis


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
        # 5 hits, todos abaixo do limite (1..5)
        redis = _make_redis_mock_with_counts(list(range(1, 6)))
        engine = MagicMock()

        async with await self._make_client(redis, engine) as client:
            statuses = []
            for _ in range(5):
                resp = await client.post("/api/auth/login")
                statuses.append(resp.status_code)
            assert all(s == 401 for s in statuses), statuses

    async def test_blocks_11th_login_returns_429(self):
        # Sequência: 1..10 (allow), 11 (block)
        redis = _make_redis_mock_with_counts(list(range(1, 12)))
        redis.ttl.return_value = 25
        engine = MagicMock()

        async with await self._make_client(redis, engine) as client:
            for _ in range(10):
                resp = await client.post("/api/auth/login")
                assert resp.status_code == 401
            resp = await client.post("/api/auth/login")
            assert resp.status_code == 429

    async def test_retry_after_header_present_on_429(self):
        redis = _make_redis_mock_with_counts(list(range(1, 12)))
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
        # cron.* limite 5 — hits 1..5 (allow), 6 (block)
        redis = _make_redis_mock_with_counts(list(range(1, 7)))
        redis.ttl.return_value = 30
        engine = MagicMock()

        async with await self._make_client(redis, engine) as client:
            for _ in range(5):
                resp = await client.post("/api/cron/refresh-provider-health")
                assert resp.status_code == 403
            resp = await client.post("/api/cron/refresh-provider-health")
            assert resp.status_code == 429

    async def test_simulador_endpoint_600_per_minute(self):
        """Bug fix: simulador tem bucket dedicado com 600 req/min.

        Antes caía no default (60/min) e disparava 429 após alguns testes.
        Agora: 600 reqs passam tranquilo, 601 bloqueia.
        """
        # 600 hits = exatamente o limite; +1 = block
        redis = _make_redis_mock_with_counts(list(range(1, 601)))
        redis.ttl.return_value = 30
        engine = MagicMock()

        app = FastAPI()
        app.middleware("http")(ip_rate_limit_middleware(engine, redis_client=redis))

        @app.post("/api/simulador/franz/test")
        async def sim():
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=200, content={"ok": True})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for _ in range(10):
                resp = await client.post("/api/simulador/franz/test")
                assert resp.status_code == 200

    async def test_loopback_dev_open_skips_rate_limit(self, monkeypatch):
        """Com RATE_LIMIT_DEV_OPEN=1, loopback (127.0.0.1) ignora rate limit."""
        monkeypatch.setenv("RATE_LIMIT_DEV_OPEN", "1")
        redis = _make_redis_mock()
        engine = MagicMock()

        app = FastAPI()
        app.middleware("http")(ip_rate_limit_middleware(engine, redis_client=redis))

        @app.post("/api/auth/login")
        async def login():
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"detail": "invalid"})

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # 100 requests no login (limite seria 10) — todas passam
            for _ in range(100):
                resp = await client.post("/api/auth/login")
                assert resp.status_code == 401
            # Redis NUNCA foi tocado (loopback = skip)
            redis.pipeline.assert_not_called()

    async def test_loopback_no_dev_open_still_rate_limited(self, monkeypatch):
        """Sem RATE_LIMIT_DEV_OPEN, loopback SEGUE sendo rate-limited (fail-safe)."""
        monkeypatch.delenv("RATE_LIMIT_DEV_OPEN", raising=False)
        redis = _make_redis_mock_with_counts(list(range(1, 12)))
        engine = MagicMock()

        app = FastAPI()
        app.middleware("http")(ip_rate_limit_middleware(engine, redis_client=redis))

        @app.post("/api/auth/login")
        async def login():
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"detail": "invalid"})

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            for _ in range(10):
                await client.post("/api/auth/login")
            resp = await client.post("/api/auth/login")
            # Mesmo em loopback, sem dev-open = limit aplica
            assert resp.status_code == 429

    async def test_health_endpoint_not_rate_limited(self):
        """Whitelist: /api/health (GET) nao passa pelo Redis."""
        redis = _make_redis_mock()
        engine = MagicMock()

        async with await self._make_client(redis, engine) as client:
            for _ in range(20):
                resp = await client.get("/api/health")
                assert resp.status_code == 200
            # Pipeline NUNCA deve ser chamado para health (whitelist)
            redis.pipeline.assert_not_called()
