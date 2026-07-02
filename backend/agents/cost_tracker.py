"""Cost Tracker — registro unificado de custo multi-provider (Sprint 0.3).

Operações:
  - record_cost_event(...) — UPSERT em cost_events. Fail-safe: loga erro, nunca levanta.
  - compute_costs_breakdown() — agrega por provider e por tenant (últimos N dias).
  - compute_top_tenants_by_cost() — top tenants ordenados por custo (BRL).
  - check_budget_alerts() — alerta se algum provider > 80% do budget mensal.

Design:
  - Sem dependência dura: se o DB falhar, loga e segue.
  - Singleton por thread: engine é importado lazy do database module.
  - Reutiliza domain/llm_pricing.resolve_model_price para custos LLM.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger("fralib.cost_tracker")


# Providers canônicos (mesmos do provider_health, sem overlap de nome exato).
KNOWN_PROVIDERS: tuple[str, ...] = (
    "anthropic",
    "openai",
    "google",
    "groq",
    "facebook_ads",
    "hunter",
    "jina",
    "whatsapp_waba",
    "google_maps",
)

# Budget mensal default em BRL por provider (override via env COST_BUDGET_<PROVIDER>_BRL).
DEFAULT_MONTHLY_BUDGET_BRL: dict[str, float] = {
    "anthropic": 5000.0,
    "openai": 2000.0,
    "google": 1500.0,
    "groq": 800.0,
    "facebook_ads": 15000.0,
    "hunter": 500.0,
    "jina": 300.0,
    "whatsapp_waba": 1000.0,
    "google_maps": 400.0,
}

# Cotação USD/BRL default (cron pode atualizar).
DEFAULT_USD_BRL_RATE: float = 5.65


@dataclass(frozen=True)
class CostEvent:
    """Snapshot imutável de 1 evento de custo."""

    tenant_id: int | None
    user_id: int | None
    job_id: int | None
    provider: str
    model: str | None
    service: str | None
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    units: int
    latency_ms: int | None
    custo_usd: float
    custo_brl: float | None
    cotacao_usd_brl: float
    status: str
    error_message: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


def _get_engine() -> Engine | None:
    """Import lazy do engine padrão; retorna None se indisponível."""
    try:
        from backend.core.database import engine

        return engine
    except Exception as exc:  # pragma: no cover - import defensive
        logger.warning("[cost_tracker] engine indisponível: %s", exc)
        return None


def estimate_llm_cost_usd(model: str, usage: Mapping[str, int | float]) -> float:
    """Delega para domain/llm_pricing; cobre testes sem import circular."""
    try:
        from backend.domain.llm_pricing import estimate_llm_cost_usd as _fn

        return _fn(model, usage)
    except Exception as exc:  # pragma: no cover - fallback
        logger.warning("[cost_tracker] estimate_llm_cost_usd falhou: %s", exc)
        return 0.0


def _to_pg_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def record_cost_event(
    *,
    provider: str,
    model: str | None = None,
    service: str | None = None,
    tenant_id: int | None = None,
    user_id: int | None = None,
    job_id: int | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    units: int = 1,
    latency_ms: int | None = None,
    custo_usd: float | None = None,
    custo_brl: float | None = None,
    cotacao_usd_brl: float | None = None,
    status: str = "success",
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Registra 1 evento de custo. Fail-safe (nunca levanta).

    Args:
        provider: nome canônico (ex.: 'anthropic', 'facebook_ads').
        model: id do modelo (LLM); None para eventos sem modelo.
        service: sub-recurso/endpoint (ex.: 'get_overall_insights').
        tenant_id: tenant proprietário do custo (None = global).
        user_id: user id opcional.
        job_id: job pipeline opcional.
        input_tokens: tokens de entrada (LLM).
        output_tokens: tokens de saída (LLM).
        cache_read_tokens: tokens lidos do cache (LLM).
        units: quantidade discreta (chamadas, requests, etc).
        latency_ms: latência da chamada.
        custo_usd: custo em USD (None = calcula via pricing se provider LLM).
        custo_brl: custo em BRL (None = converte da cotação).
        cotacao_usd_brl: taxa de conversão (None = default 5.65).
        status: 'success' | 'error' | 'partial'.
        error_message: mensagem de erro opcional.
        metadata: dict livre (auditoria estruturada).

    Returns:
        True se o INSERT foi executado; False se algo falhou (mas nunca levanta).
    """
    engine: Engine | None = _get_engine()
    if engine is None:
        logger.warning("[cost_tracker] sem engine: evento descartado provider=%s", provider)
        return False

    if provider not in KNOWN_PROVIDERS:
        logger.debug(
            "[cost_tracker] provider '%s' fora da lista canônica (aceito, segue)",
            provider,
        )

    # Calcular custo em USD se necessário
    if custo_usd is None and model:
        custo_usd = estimate_llm_cost_usd(
            model,
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read": cache_read_tokens,
                "cache_creation": 0,
            },
        )
    if custo_usd is None:
        custo_usd = 0.0

    # Cotação USD/BRL
    if cotacao_usd_brl is None:
        cotacao_usd_brl = DEFAULT_USD_BRL_RATE

    # Custo em BRL
    if custo_brl is None:
        try:
            custo_brl = float(
                (Decimal(str(custo_usd)) * Decimal(str(cotacao_usd_brl))).quantize(
                    Decimal("0.0001")
                )
            )
        except Exception:
            custo_brl = 0.0

    payload: dict[str, Any] = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "job_id": job_id,
        "provider": provider,
        "model": model,
        "service": service,
        "input_tokens": _to_pg_int(input_tokens),
        "output_tokens": _to_pg_int(output_tokens),
        "cache_read_tokens": _to_pg_int(cache_read_tokens),
        "units": _to_pg_int(units),
        "latency_ms": latency_ms,
        "custo_usd": custo_usd,
        "custo_brl": custo_brl,
        "cotacao_usd_brl": cotacao_usd_brl,
        "status": status,
        "error_message": error_message,
        "metadata_json": json.dumps(metadata or {}),
    }

    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO cost_events
                      (tenant_id, user_id, job_id, provider, model, service,
                       input_tokens, output_tokens, cache_read_tokens, units,
                       latency_ms, custo_usd, custo_brl, cotacao_usd_brl,
                       status, error_message, metadata, criado_em)
                    VALUES
                      (:tenant_id, :user_id, :job_id, :provider, :model, :service,
                       :input_tokens, :output_tokens, :cache_read_tokens, :units,
                       :latency_ms, :custo_usd, :custo_brl, :cotacao_usd_brl,
                       :status, :error_message, CAST(:metadata_json AS JSONB), NOW())
                    """
                ),
                payload,
            )
        logger.debug(
            "[cost_tracker] ok provider=%s modelo=%s custo_usd=%.6f custo_brl=%.4f",
            provider, model, custo_usd, custo_brl or 0.0,
        )
        return True
    except Exception as exc:
        # Fail-safe: loga e retorna False (nunca levanta).
        logger.warning(
            "[cost_tracker] record falhou provider=%s modelo=%s: %s",
            provider, model, exc,
        )
        return False


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Converte _FakeRow / SQLAlchemy Row em dict."""
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    if hasattr(row, "_asdict") and callable(getattr(row, "_asdict")):
        return dict(row._asdict())
    if hasattr(row, "values") and not callable(getattr(row, "values", None)):
        vals = row.values
    else:
        try:
            return dict(row._mapping)
        except AttributeError:
            vals = tuple(row)

    keys = (
        "provider",
        "total_eventos",
        "total_usd",
        "total_brl",
        "total_input_tokens",
        "total_output_tokens",
        "dia",
        "tenant_id",
    )
    return {k: v for k, v in zip(keys, vals)}


def costs_breakdown(
    engine: Engine,
    days: int = 30,
    tenant_id: int | None = None,
) -> list[dict[str, Any]]:
    """Retorna breakdown por provider nos últimos N dias (opcionalmente por tenant).

    Returns:
        Lista de dicts com chaves: provider, total_eventos, total_usd, total_brl,
        total_input_tokens, total_output_tokens.
    """
    days = max(1, int(days))
    params: dict[str, Any] = {"days": days}
    tenant_clause = ""
    if tenant_id is not None:
        tenant_clause = "AND tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id

    sql = f"""
        SELECT
            provider,
            COUNT(*)                    AS total_eventos,
            COALESCE(SUM(custo_usd), 0)  AS total_usd,
            COALESCE(SUM(custo_brl), 0)  AS total_brl,
            COALESCE(SUM(input_tokens), 0)  AS total_input_tokens,
            COALESCE(SUM(output_tokens), 0) AS total_output_tokens
        FROM cost_events
        WHERE criado_em >= NOW() - make_interval(days => :days)
          {tenant_clause}
        GROUP BY provider
        ORDER BY total_brl DESC
    """

    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
    except Exception as exc:
        logger.warning("[cost_tracker] costs_breakdown falhou: %s", exc)
        return []

    out: list[dict[str, Any]] = []
    for r in rows:
        d = _row_to_dict(r)
        # Casting float
        for k in ("total_usd", "total_brl", "total_input_tokens",
                  "total_output_tokens", "total_eventos"):
            if k in d:
                try:
                    d[k] = float(d[k])
                except (TypeError, ValueError):
                    d[k] = 0.0
        out.append(d)
    return out


def top_tenants_by_cost(
    engine: Engine,
    days: int = 30,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Top tenants por custo (BRL) nos últimos N dias.

    Returns:
        Lista ordenada desc por custo BRL com chaves:
        tenant_id, total_eventos, total_brl, total_usd.
    """
    days = max(1, int(days))
    limit = max(1, int(limit))
    sql = """
        SELECT
            COALESCE(tenant_id, 0)         AS tenant_id,
            COUNT(*)                        AS total_eventos,
            COALESCE(SUM(custo_brl), 0)     AS total_brl,
            COALESCE(SUM(custo_usd), 0)     AS total_usd
        FROM cost_events
        WHERE criado_em >= NOW() - make_interval(days => :days)
          AND tenant_id IS NOT NULL
        GROUP BY tenant_id
        ORDER BY total_brl DESC
        LIMIT :limit
    """
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(sql), {"days": days, "limit": limit}
            ).fetchall()
    except Exception as exc:
        logger.warning("[cost_tracker] top_tenants_by_cost falhou: %s", exc)
        return []

    out: list[dict[str, Any]] = []
    for r in rows:
        d = _row_to_dict(r)
        for k in ("total_brl", "total_usd", "total_eventos"):
            if k in d:
                try:
                    d[k] = float(d[k])
                except (TypeError, ValueError):
                    d[k] = 0.0
        out.append(d)
    return out


def _budget_for_provider(provider: str) -> float:
    """Retorna budget mensal em BRL para provider (env override)."""
    env_key = f"COST_BUDGET_{provider.upper()}_BRL"
    try:
        v = float(os.getenv(env_key, "0"))
        if v > 0:
            return v
    except (TypeError, ValueError):
        pass
    return DEFAULT_MONTHLY_BUDGET_BRL.get(provider, 1000.0)


def check_budget_alerts(
    engine: Engine,
    *,
    days: int = 30,
    threshold_pct: float = 80.0,
) -> list[dict[str, Any]]:
    """Verifica custo dos últimos N dias por provider; alerta se >= threshold_pct.

    Returns:
        Lista de dicts {provider, custo_brl, budget_brl, pct, level}.
        level: 'critical' (>= 100%), 'warning' (>= threshold_pct), 'info' (< threshold).
    """
    breakdown = costs_breakdown(engine, days=days)
    alerts: list[dict[str, Any]] = []
    for row in breakdown:
        provider = row.get("provider", "")
        custo = float(row.get("total_brl", 0.0))
        budget = _budget_for_provider(provider)
        if budget <= 0:
            continue
        pct = (custo / budget) * 100.0
        if pct >= 100.0:
            level = "critical"
        elif pct >= threshold_pct:
            level = "warning"
        else:
            level = "info"
        if level != "info":
            alerts.append(
                {
                    "provider": provider,
                    "custo_brl": round(custo, 4),
                    "budget_brl": budget,
                    "pct": round(pct, 2),
                    "level": level,
                }
            )
    return alerts
