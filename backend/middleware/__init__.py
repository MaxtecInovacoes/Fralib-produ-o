"""Middleware HTTP do Fralib.

Sprint 3.1 — Rate limit por IP (Redis + fallback Postgres).

Fornece `ip_rate_limit_middleware(app)` para registro em FastAPI via
`app.middleware('http')`. Veja `middleware.rate_limit` para detalhes.
"""

from __future__ import annotations

from middleware.rate_limit import (
    IPRateLimiter,
    endpoint_bucket_for_request,
    ip_rate_limit_middleware,
)

__all__ = ["IPRateLimiter", "endpoint_bucket_for_request", "ip_rate_limit_middleware"]
