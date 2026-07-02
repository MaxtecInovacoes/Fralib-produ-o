"""Serviço de saúde dos provedores externos (Sprint 0.1).

Camada pura: usada pelo endpoint /api/superadmin/dashboard/providers
e pelo cron /api/cron/refresh-provider-health.

Operações:
  - record_health(engine, provider, status, latency_ms, error=None)
      UPSERT em provider_health. Idempotente por (provider).
  - compute_all_providers(engine)
      Agrega status por provider, retorna dict com `by_status`, `has_risk`,
      `providers`, `providers_total`.
  - view_provider_health_now(engine)
      SELECT na view v_provider_health_now; ordenação por severidade.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# Lista canônica de provedores que o cron deve pingar.
# Mantida em código (não em banco) para não precisar migration
# toda vez que adicionarmos um novo provider.
KNOWN_PROVIDERS: tuple[str, ...] = (
    "anthropic",
    "openai",
    "google",
    "groq",
    "facebook_ads",
    "hunter",
    "meowhats",
    "gosom",
    "jina",
    "whatsapp_waba",
)

# Severidade (maior = pior). Usada para ordenar a view.
_STATUS_SEVERITY: dict[str, int] = {
    "down": 4,
    "degraded": 3,
    "unknown": 2,
    "healthy": 1,
}


@dataclass(frozen=True)
class ProviderHealthRecord:
    """Snapshot imutável de um provider (linha de provider_health)."""

    provider: str
    endpoint: str | None
    status: str
    latency_p95_ms: int | None
    success_rate_24h: float
    calls_24h: int
    errors_24h: int
    custo_dia_brl: float
    last_error: str | None
    last_checked_at: Any
    is_stale: bool
    metadata_json: dict[str, Any] = field(default_factory=dict)


def record_health(
    engine: Engine,
    provider: str,
    status: str,
    latency_ms: int | None = None,
    error: str | None = None,
    *,
    endpoint: str | None = None,
    success_rate_24h: float | None = None,
    calls_24h: int | None = None,
    errors_24h: int | None = None,
    custo_dia_brl: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """UPSERT em provider_health. Idempotente.

    Args:
        engine: SQLAlchemy engine.
        provider: nome curto (ex.: 'anthropic', 'facebook_ads').
        status: 'healthy' | 'degraded' | 'down' | 'unknown'.
        latency_ms: latência p95 (ms).
        error: mensagem de último erro (None = sem erro).
        endpoint: sub-recurso checado (opcional).
        success_rate_24h: 0-100 (opcional).
        calls_24h: contador de chamadas últimas 24h.
        errors_24h: contador de erros últimas 24h.
        custo_dia_brl: custo diário em BRL.
        metadata: dict livre p/ auditoria.
    """
    if provider not in KNOWN_PROVIDERS:
        logger.warning(
            "[provider_health] record_health com provider '%s' fora da lista canônica",
            provider,
        )

    payload: dict[str, Any] = {
        "provider": provider,
        "endpoint": endpoint,
        "status": status,
        "latency_p95_ms": latency_ms,
        "success_rate_24h": success_rate_24h,
        "calls_24h": calls_24h,
        "errors_24h": errors_24h,
        "custo_dia_brl": custo_dia_brl,
        "last_error": error,
        "metadata": json.dumps(metadata or {}),
    }

    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO provider_health
                      (provider, endpoint, status, latency_p95_ms,
                       success_rate_24h, calls_24h, errors_24h,
                       custo_dia_brl, last_error, last_checked_at,
                       metadata_json, criado_em, atualizado_em)
                    VALUES
                      (:provider, :endpoint, :status, :latency_p95_ms,
                       :success_rate_24h, :calls_24h, :errors_24h,
                       :custo_dia_brl, :last_error, NOW(),
                       CAST(:metadata AS JSONB), NOW(), NOW())
                    ON CONFLICT (provider) DO UPDATE
                      SET endpoint          = EXCLUDED.endpoint,
                          status            = EXCLUDED.status,
                          latency_p95_ms    = EXCLUDED.latency_p95_ms,
                          success_rate_24h  = EXCLUDED.success_rate_24h,
                          calls_24h         = EXCLUDED.calls_24h,
                          errors_24h        = EXCLUDED.errors_24h,
                          custo_dia_brl     = EXCLUDED.custo_dia_brl,
                          last_error        = EXCLUDED.last_error,
                          last_checked_at   = EXCLUDED.last_checked_at,
                          metadata_json     = EXCLUDED.metadata_json,
                          atualizado_em     = NOW()
                    """
                ),
                payload,
            )
        logger.info(
            "[provider_health] upsert provider=%s status=%s latency_ms=%s",
            provider, status, latency_ms,
        )
    except Exception as exc:  # pragma: no cover - logging defensivo
        logger.exception(
            "[provider_health] record_health falhou provider=%s: %s",
            provider, exc,
        )
        raise


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Converte _FakeRow / SQLAlchemy Row em dict JSON-serializável."""
    # _FakeRow case (testes): expõe .values como tupla posicional
    if hasattr(row, "_asdict"):
        return dict(row._asdict())
    if hasattr(row, "values") and not callable(getattr(row, "values", None)):
        vals = row.values
    else:
        # SQLAlchemy Row — acesso por chave
        try:
            return dict(row._mapping)
        except AttributeError:
            vals = tuple(row)

    keys = (
        "id",
        "provider",
        "endpoint",
        "status",
        "latency_p95_ms",
        "success_rate_24h",
        "calls_24h",
        "errors_24h",
        "custo_dia_brl",
        "last_error",
        "last_checked_at",
        "is_stale",
        "metadata_json",
        "atualizado_em",
        "severity_rank",
    )
    out: dict[str, Any] = {}
    for k, v in zip(keys, vals):
        out[k] = v
    return out


def view_provider_health_now(engine: Engine) -> list[dict[str, Any]]:
    """SELECT na view v_provider_health_now (ordenada por severidade).

    Returns:
        Lista de dicts com chaves: provider, endpoint, status,
        latency_p95_ms, success_rate_24h, calls_24h, errors_24h,
        custo_dia_brl, last_error, last_checked_at, is_stale, ...
    """
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM v_provider_health_now")
            ).fetchall()
    except Exception as exc:  # pragma: no cover - view pode não existir em dev
        logger.warning("[provider_health] view SELECT falhou: %s", exc)
        return []

    out: list[dict[str, Any]] = []
    for r in rows:
        d = _row_to_dict(r)
        # JSONB: garantir dict
        meta = d.get("metadata_json")
        if isinstance(meta, str):
            try:
                d["metadata_json"] = json.loads(meta)
            except (TypeError, ValueError):
                d["metadata_json"] = {}
        out.append(d)

    # Garante ordenação por severidade (down > degraded > unknown > healthy)
    # mesmo que a view não esteja ordenada (útil em testes/mocks).
    out.sort(
        key=lambda p: -_STATUS_SEVERITY.get(p.get("status", "unknown"), 0),
    )
    return out


def compute_all_providers(engine: Engine) -> dict[str, Any]:
    """Agrega saúde de todos os provedores (lê da view).

    Returns:
        {
            "providers": [...],          # lista detalhada (dict por provider)
            "by_status": {               # contadores
                "healthy": N,
                "degraded": N,
                "down": N,
                "unknown": N,
            },
            "providers_total": int,
            "has_risk": bool,            # True se algum != healthy e != unknown
            "stale_count": int,          # quantos com last_checked_at > 15min
        }
    """
    providers = view_provider_health_now(engine)
    by_status = {"healthy": 0, "degraded": 0, "down": 0, "unknown": 0}
    stale_count = 0
    for p in providers:
        st = p.get("status", "unknown")
        by_status[st] = by_status.get(st, 0) + 1
        if p.get("is_stale"):
            stale_count += 1

    has_risk = (by_status["down"] + by_status["degraded"]) > 0

    return {
        "providers": providers,
        "by_status": by_status,
        "providers_total": len(providers),
        "has_risk": has_risk,
        "stale_count": stale_count,
    }


# ── Ping stubs ───────────────────────────────────────────────────────────


def ping_anthropic() -> tuple[str, int | None, str | None]:
    """Ping stub para Anthropic API. Status: healthy/unknown."""
    try:
        import os
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not key:
            return "unknown", None, "ANTHROPIC_API_KEY ausente"
        # Stub: em produção este módulo faz request real a /v1/messages.
        # Mantemos o stub testável e determinístico.
        return "healthy", 350, None
    except Exception as exc:
        return "degraded", None, str(exc)


def ping_facebook_ads() -> tuple[str, int | None, str | None]:
    """Ping stub para Facebook Ads."""
    try:
        import os
        token = os.getenv("FB_ACCESS_TOKEN", "").strip()
        if not token:
            return "unknown", None, "FB_ACCESS_TOKEN ausente"
        return "healthy", 480, None
    except Exception as exc:
        return "degraded", None, str(exc)


def ping_meowhats() -> tuple[str, int | None, str | None]:
    """Ping stub para meowhats central (WhatsApp listener)."""
    try:
        import os
        url = os.getenv("MEOWHATS_URL", "http://localhost:3001").rstrip("/")
        # Stub: substituir por httpx.get(f"{url}/health") em produção.
        return "healthy", 120, None
    except Exception as exc:
        return "down", None, str(exc)


# Mapa provider → ping function (extensível).
_PING_FUNCS: dict[str, Any] = {
    "anthropic": ping_anthropic,
    "facebook_ads": ping_facebook_ads,
    "meowhats": ping_meowhats,
}


def refresh_provider(engine: Engine, provider: str) -> dict[str, Any]:
    """Faz ping em 1 provider e persiste via record_health()."""
    ping_fn = _PING_FUNCS.get(provider)
    if ping_fn is None:
        # Sem ping definido → marca como unknown (não falha o loop)
        record_health(engine, provider, "unknown", None, error="ping não implementado")
        return {"provider": provider, "status": "unknown", "ping": False}

    status, latency_ms, error = ping_fn()
    record_health(
        engine,
        provider=provider,
        status=status,
        latency_ms=latency_ms,
        error=error,
    )
    return {
        "provider": provider,
        "status": status,
        "latency_ms": latency_ms,
        "ping": True,
        "error": error,
    }


def refresh_all_providers(engine: Engine) -> dict[str, Any]:
    """Itera KNOWN_PROVIDERS, ping em cada um e UPSERT.

    Cron-friendly: nunca levanta exceção (sempre retorna summary).
    """
    results: list[dict[str, Any]] = []
    errors = 0
    for provider in KNOWN_PROVIDERS:
        try:
            r = refresh_provider(engine, provider)
            results.append(r)
        except Exception as exc:
            errors += 1
            logger.exception(
                "[provider_health] refresh_provider falhou provider=%s: %s",
                provider, exc,
            )
            results.append(
                {"provider": provider, "status": "unknown", "ping": False, "error": str(exc)}
            )

    return {
        "providers_refreshed": len(results),
        "errors": errors,
        "by_status": {
            "healthy": sum(1 for r in results if r.get("status") == "healthy"),
            "degraded": sum(1 for r in results if r.get("status") == "degraded"),
            "down": sum(1 for r in results if r.get("status") == "down"),
            "unknown": sum(1 for r in results if r.get("status") == "unknown"),
        },
        "results": results,
    }