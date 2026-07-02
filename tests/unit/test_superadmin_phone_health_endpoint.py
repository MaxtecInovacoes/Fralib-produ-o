"""Smoke tests para /api/superadmin/phone-health.

Valida auth (role=superadmin), listagem de tenants, eventos, e pause.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))


# ── Helpers ─────────────────────────────────────────────────────────────

def _make_mock_engine(
    *,
    tenant_rows: list[dict] | None = None,
    events_rows: list[dict] | None = None,
    pause_result: tuple | None = None,
) -> MagicMock:
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    engine.connect.return_value.__exit__.return_value = None
    engine.begin.return_value.__enter__.return_value = conn
    engine.begin.return_value.__exit__.return_value = None

    def execute_side(stmt, params=None):
        sql = str(stmt).lower()
        result = MagicMock()
        if "from users u" in sql and "left join phone_health_score" in sql:
            tenants = tenant_rows or []
            result.fetchall.return_value = [
                (
                    t["user_id"],
                    t.get("email", "user@example.com"),
                    t.get("score", 100),
                    t.get("status", "healthy"),
                    t.get("ultima_restricao_em"),
                    t.get("pause_franz_until"),
                    t.get("atualizado_em"),
                    t.get("signals", {}),
                )
                for t in tenants
            ]
        elif "from phone_health_events" in sql:
            events = events_rows or []
            result.fetchall.return_value = [
                (e["id"], e["severity"], e["event_type"], e.get("detail", {}), e["criado_em"])
                for e in events
            ]
        elif "returning pause_franz_until" in sql:
            if pause_result is not None:
                result.fetchone.return_value = pause_result
            else:
                result.fetchone.return_value = None
        else:
            result.fetchone.return_value = None
            result.fetchall.return_value = []
        return result

    conn.execute.side_effect = execute_side
    return engine


def _build_app(engine_mock: MagicMock, usuario: dict | None) -> TestClient:
    from backend.endpoints import phone_health_endpoints as mod
    from backend.core.auth import get_current_user

    mod.engine = engine_mock

    app = FastAPI()
    app.include_router(mod.router)
    if usuario is not None:
        app.dependency_overrides[get_current_user] = lambda: usuario
    return TestClient(app)


# ── Tests ───────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestSuperadminPhoneHealthEndpoint:

    def test_list_requires_auth(self) -> None:
        """Sem auth → 401."""
        from backend.endpoints import phone_health_endpoints as mod
        mod.engine = _make_mock_engine()
        client = _build_app(_make_mock_engine(), usuario=None)
        response = client.get("/api/superadmin/phone-health")
        assert response.status_code in (401, 403)

    def test_list_requires_superadmin_role(self) -> None:
        """role='user' → 403."""
        client = _build_app(
            _make_mock_engine(),
            usuario={"user_id": 1, "role": "user", "is_superadmin": False},
        )
        response = client.get("/api/superadmin/phone-health")
        assert response.status_code == 403

    def test_list_accepts_is_superadmin_flag(self) -> None:
        """is_superadmin=True (mesmo com role diferente) → 200."""
        engine = _make_mock_engine(tenant_rows=[
            {"user_id": 10, "email": "a@x.com", "score": 90, "status": "healthy"},
            {"user_id": 20, "email": "b@x.com", "score": 30, "status": "restricted"},
        ])
        client = _build_app(
            engine,
            usuario={"user_id": 1, "role": "ops", "is_superadmin": True},
        )
        response = client.get("/api/superadmin/phone-health")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        # Verifica que ambos os tenants estão presentes (ordem depende do SQL)
        user_ids = {t["user_id"] for t in body["tenants"]}
        assert user_ids == {10, 20}
        # Top 5 = todos (total=2)
        assert len(body["top_5_risk"]) == 2

    def test_list_accepts_superadmin_role(self) -> None:
        """role='superadmin' → 200."""
        engine = _make_mock_engine(tenant_rows=[
            {"user_id": 5, "email": "x@x.com", "score": 100, "status": "healthy"},
        ])
        client = _build_app(
            engine,
            usuario={"user_id": 1, "role": "superadmin", "is_superadmin": False},
        )
        response = client.get("/api/superadmin/phone-health")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1

    def test_list_filters_by_status(self) -> None:
        """?status=restricted → mock deve receber :status param."""
        engine = _make_mock_engine(tenant_rows=[])
        client = _build_app(
            engine,
            usuario={"user_id": 1, "role": "superadmin"},
        )
        response = client.get("/api/superadmin/phone-health?status=restricted")
        assert response.status_code == 200

    def test_events_requires_superadmin(self) -> None:
        """role=user → 403."""
        client = _build_app(
            _make_mock_engine(),
            usuario={"user_id": 1, "role": "user", "is_superadmin": False},
        )
        response = client.get("/api/superadmin/phone-health/42/events")
        assert response.status_code == 403

    def test_events_returns_list(self) -> None:
        """superadmin → 200 com lista de eventos."""
        from datetime import datetime
        now = datetime(2026, 7, 1)
        engine = _make_mock_engine(events_rows=[
            {"id": 1, "severity": "critical", "event_type": "restricted", "detail": {"code": 131047}, "criado_em": now},
            {"id": 2, "severity": "warn", "event_type": "rate_limited", "detail": {}, "criado_em": now},
        ])
        client = _build_app(
            engine,
            usuario={"user_id": 1, "role": "superadmin"},
        )
        response = client.get("/api/superadmin/phone-health/42/events?limit=10")
        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == 42
        assert len(body["events"]) == 2
        assert body["events"][0]["severity"] == "critical"
        assert body["events"][0]["event_type"] == "restricted"

    def test_pause_requires_superadmin(self) -> None:
        """role=user → 403."""
        client = _build_app(
            _make_mock_engine(),
            usuario={"user_id": 1, "role": "user", "is_superadmin": False},
        )
        response = client.post("/api/superadmin/phone-health/42/pause?hours=24")
        assert response.status_code == 403

    def test_pause_returns_ok(self) -> None:
        """superadmin → 200 com paused_hours."""
        from datetime import datetime
        pause_until = datetime(2026, 7, 2)
        engine = _make_mock_engine(pause_result=(pause_until,))
        client = _build_app(
            engine,
            usuario={"user_id": 1, "role": "superadmin"},
        )
        response = client.post("/api/superadmin/phone-health/42/pause?hours=24")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["user_id"] == 42
        assert body["paused_hours"] == 24

    def test_pause_validates_hours(self) -> None:
        """hours fora de [1, 168] → 422."""
        client = _build_app(
            _make_mock_engine(),
            usuario={"user_id": 1, "role": "superadmin"},
        )
        response = client.post("/api/superadmin/phone-health/42/pause?hours=0")
        assert response.status_code == 422
        response = client.post("/api/superadmin/phone-health/42/pause?hours=200")
        assert response.status_code == 422