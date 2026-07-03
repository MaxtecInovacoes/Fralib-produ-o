"""Sprint 1.6: health check completo do Plano SDR.

Verifica:
  - Postgres conectavel
  - Redis conectavel
  - Tabela sdr_turns existe
  - Tabela leads tem colunas obrigatorias
  - Migration rodou

Uso:
    from services.health_check import run_health_check
    result = run_health_check(engine, redis_client)
    # result = {"postgres": "ok", "redis": "ok", "sdr_turns": "ok", ...}

    # Para usar em endpoint /api/health:
    @app.get("/api/health/sdr")
    async def health_sdr():
        return run_health_check(engine, redis_client)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("fralib.services.health_check")


def check_postgres(engine) -> tuple[bool, str]:
    """Tenta SELECT 1. Returns (ok, msg)."""
    try:
        if engine is None:
            return False, "engine is None"
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1")).scalar()
        return True, "ok"
    except Exception as e:
        return False, f"connection failed: {type(e).__name__}: {e}"


def check_redis(redis_client) -> tuple[bool, str]:
    """Tenta PING no Redis. Returns (ok, msg)."""
    try:
        if redis_client is None:
            return False, "redis_client is None"
        pong = redis_client.ping()
        if pong is True or str(pong).lower() == "true":
            return True, "ok"
        return False, f"unexpected ping response: {pong}"
    except Exception as e:
        return False, f"ping failed: {type(e).__name__}: {e}"


def check_table_exists(engine, table_name: str) -> tuple[bool, str]:
    """Verifica se tabela existe no schema public."""
    try:
        if engine is None:
            return False, "engine is None"
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = :table_name
                )
            """), {"table_name": table_name}).scalar()
        if result:
            return True, "ok"
        return False, f"table '{table_name}' not found"
    except Exception as e:
        return False, f"check failed: {type(e).__name__}: {e}"


def check_column_exists(engine, table_name: str, column_name: str) -> tuple[bool, str]:
    """Verifica se coluna existe na tabela."""
    try:
        if engine is None:
            return False, "engine is None"
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = :table_name
                    AND column_name = :column_name
                )
            """), {"table_name": table_name, "column_name": column_name}).scalar()
        if result:
            return True, "ok"
        return False, f"column '{table_name}.{column_name}' not found"
    except Exception as e:
        return False, f"check failed: {type(e).__name__}: {e}"


def run_health_check(engine=None, redis_client=None) -> dict[str, Any]:
    """Health check completo do Plano SDR.

    Returns:
        dict com status de cada check + summary
    """
    checks = {
        "postgres": check_postgres(engine),
        "redis": check_redis(redis_client),
        "sdr_turns_table": check_table_exists(engine, "sdr_turns"),
        "sdr_simulations_table": check_table_exists(engine, "sdr_simulations"),
        "leads_table": check_table_exists(engine, "leads"),
        "leads_phone_health": check_column_exists(engine, "leads", "phone_health_score"),
        "outbound_queue_table": check_table_exists(engine, "outbound_queue"),
        "tenant_alerts_table": check_table_exists(engine, "tenant_alerts"),
        "audit_events_table": check_table_exists(engine, "audit_events"),
    }

    all_ok = all(ok for ok, _ in checks.values())
    failed = [name for name, (ok, _) in checks.items() if not ok]

    return {
        "status": "healthy" if all_ok else "degraded",
        "all_ok": all_ok,
        "failed": failed,
        "checks": {
            name: {"ok": ok, "message": msg}
            for name, (ok, msg) in checks.items()
        },
    }
