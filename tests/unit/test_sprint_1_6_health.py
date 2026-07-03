"""Testes Sprint 1.6 — health check + migration idempotente."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))

from services.health_check import (  # noqa: E402
    check_postgres,
    check_redis,
    check_table_exists,
    check_column_exists,
    run_health_check,
)


# ── check_postgres ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCheckPostgres:
    def test_ok(self):
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = conn
        conn.execute.return_value.scalar.return_value = 1
        ok, msg = check_postgres(engine)
        assert ok is True
        assert msg == "ok"

    def test_engine_none(self):
        ok, msg = check_postgres(None)
        assert ok is False
        assert "None" in msg

    def test_connection_fails(self):
        engine = MagicMock()
        engine.connect.return_value.__enter__.side_effect = ConnectionError("db offline")
        ok, msg = check_postgres(engine)
        assert ok is False
        assert "ConnectionError" in msg


# ── check_redis ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCheckRedis:
    def test_ok(self):
        redis = MagicMock()
        redis.ping.return_value = True
        ok, msg = check_redis(redis)
        assert ok is True

    def test_none(self):
        ok, msg = check_redis(None)
        assert ok is False
        assert "None" in msg

    def test_ping_fails(self):
        redis = MagicMock()
        redis.ping.side_effect = ConnectionError("redis offline")
        ok, msg = check_redis(redis)
        assert ok is False
        assert "ConnectionError" in msg

    def test_unexpected_response(self):
        redis = MagicMock()
        redis.ping.return_value = "PONG"  # string, nao True
        ok, msg = check_redis(redis)
        # "PONG".lower() == "pong" != "true" → unexpected
        assert ok is False
        assert "unexpected" in msg.lower()


# ── check_table_exists ────────────────────────────────────────────────────


@pytest.mark.unit
class TestCheckTableExists:
    def test_exists(self):
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = conn
        conn.execute.return_value.scalar.return_value = True
        ok, msg = check_table_exists(engine, "users")
        assert ok is True

    def test_not_found(self):
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = conn
        conn.execute.return_value.scalar.return_value = False
        ok, msg = check_table_exists(engine, "nao_existe")
        assert ok is False
        assert "not found" in msg


# ── check_column_exists ──────────────────────────────────────────────────


@pytest.mark.unit
class TestCheckColumnExists:
    def test_exists(self):
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = conn
        conn.execute.return_value.scalar.return_value = True
        ok, msg = check_column_exists(engine, "users", "id")
        assert ok is True

    def test_not_found(self):
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = conn
        conn.execute.return_value.scalar.return_value = False
        ok, msg = check_column_exists(engine, "users", "coluna_inexistente")
        assert ok is False


# ── run_health_check ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestRunHealthCheck:
    def test_all_healthy(self):
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = conn
        # SELECT 1 → 1
        # table_exists → True
        # column_exists → True
        conn.execute.return_value.scalar.return_value = 1
        redis = MagicMock()
        redis.ping.return_value = True

        result = run_health_check(engine=engine, redis_client=redis)
        assert result["all_ok"] is True
        assert result["status"] == "healthy"
        assert result["failed"] == []

    def test_postgres_down(self):
        engine = MagicMock()
        engine.connect.return_value.__enter__.side_effect = Exception("db down")
        redis = MagicMock()
        redis.ping.return_value = True

        result = run_health_check(engine=engine, redis_client=redis)
        assert result["all_ok"] is False
        assert result["status"] == "degraded"
        assert "postgres" in result["failed"]

    def test_redis_down(self):
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = conn
        conn.execute.return_value.scalar.return_value = 1
        redis = MagicMock()
        redis.ping.side_effect = ConnectionError("redis down")

        result = run_health_check(engine=engine, redis_client=redis)
        assert result["all_ok"] is False
        assert "redis" in result["failed"]

    def test_missing_table(self):
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = conn
        # SELECT 1 retorna 1, mas sdr_turns nao existe
        conn.execute.return_value.scalar.side_effect = [1, False]
        redis = MagicMock()
        redis.ping.return_value = True

        result = run_health_check(engine=engine, redis_client=redis)
        assert result["all_ok"] is False
        # Alguma tabela deve estar missing
        assert any("table" in f for f in result["failed"])


# ── Migration idempotente ────────────────────────────────────────────────


@pytest.mark.unit
class TestMigrationIdempotent:
    def test_sdr_turns_migration_uses_if_not_exists(self):
        """Migration sdr_turns DEVE usar IF NOT EXISTS pra ser idempotente."""
        content = Path("backend/migrations/2026_07_sdr_turns.sql").read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS" in content
        assert "CREATE INDEX IF NOT EXISTS" in content
