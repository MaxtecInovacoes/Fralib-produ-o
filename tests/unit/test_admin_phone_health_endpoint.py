"""Smoke tests para /api/admin/phone-health (admin tenant).

Usa TestClient com mocks — não depende de server.py nem de DB real.
Valida contrato HTTP, auth e escopo por tenant.
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
    score_row: dict | None = None,
    events_rows: list[dict] | None = None,
) -> MagicMock:
    """Monta um engine mock que retorna as rows esperadas."""
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    engine.connect.return_value.__exit__.return_value = None
    engine.begin.return_value.__enter__.return_value = conn
    engine.begin.return_value.__exit__.return_value = None

    def execute_side(stmt, params=None):
        sql = str(stmt).lower()
        result = MagicMock()
        if "from phone_health_score" in sql:
            if score_row is None:
                result.fetchone.return_value = None
            else:
                result.fetchone.return_value = (
                    score_row.get("score", 100),
                    score_row.get("status", "healthy"),
                    score_row.get("signals", {}),
                    score_row.get("ultima_restricao_em"),
                    score_row.get("pause_franz_until"),
                    score_row.get("atualizado_em"),
                )
        elif "from phone_health_events" in sql:
            events = events_rows or []
            result.fetchall.return_value = [
                (e["id"], e["severity"], e["event_type"], e["criado_em"]) for e in events
            ]
        else:
            result.fetchone.return_value = None
            result.fetchall.return_value = []
        return result

    conn.execute.side_effect = execute_side
    return engine


def _build_app(engine_mock: MagicMock, user_id: int) -> TestClient:
    """Constrói TestClient com engine e user mockados via dependency_overrides."""
    from backend.endpoints import admin_phone_health_endpoints as mod
    from backend.core.auth import get_current_user

    # Patch engine no módulo ANTES de incluir o router
    mod.engine = engine_mock

    app = FastAPI()
    app.include_router(mod.router)
    app.dependency_overrides[get_current_user] = lambda: {"user_id": user_id, "role": "user"}
    return TestClient(app)


# ── Tests ───────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestAdminPhoneHealthEndpoint:
    """Valida contrato HTTP e lógica do endpoint admin (escopado por tenant)."""

    def test_get_without_auth_returns_401(self) -> None:
        """Sem get_current_user resolvida → 401."""
        from backend.endpoints.admin_phone_health_endpoints import router
        from backend.endpoints import admin_phone_health_endpoints as mod
        mod.engine = _make_mock_engine()
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.get("/api/admin/phone-health")
        assert response.status_code in (401, 403), (
            f"esperado 401/403 sem auth, obtido {response.status_code}"
        )

    def test_get_returns_default_when_no_score(self) -> None:
        """Sem linha em phone_health_score → retorna defaults com recommendation."""
        client = _build_app(_make_mock_engine(), user_id=42)
        response = client.get("/api/admin/phone-health")
        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == 42
        assert body["score"] == 100
        assert body["status"] == "healthy"
        assert body["events"] == []
        assert "recommendation" in body
        assert "Sem dados" in body["recommendation"]

    def test_get_returns_existing_score(self) -> None:
        """Com score populado → retorna valores corretos + escopo respeitado."""
        from datetime import datetime
        now = datetime(2026, 7, 1, 12, 0, 0)
        engine = _make_mock_engine(
            score_row={
                "score": 65,
                "status": "degraded",
                "signals": {"events_24h": 8, "dlq_24h": 2, "optouts_24h": 1},
                "ultima_restricao_em": None,
                "pause_franz_until": None,
                "atualizado_em": now,
            },
            events_rows=[
                {"id": 1, "severity": "warn", "event_type": "rate_limited", "criado_em": now},
            ],
        )
        client = _build_app(engine, user_id=99)
        response = client.get("/api/admin/phone-health")

        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == 99  # escopo respeitado (do token)
        assert body["score"] == 65
        assert body["status"] == "degraded"
        assert body["signals"]["events_24h"] == 8
        assert body["signals"]["dlq_24h"] == 2
        assert body["signals"]["optouts_24h"] == 1
        assert len(body["events"]) == 1
        assert body["events"][0]["severity"] == "warn"
        # Recommendation: degraded + dlq_24h > 5? No, é 2. events_24h > 10? No, é 8.
        # Cai no genérico "Score abaixo do ideal"
        assert "degradado" in body["recommendation"].lower() or "65" in body["recommendation"]

    def test_post_pause_updates_pause_until(self) -> None:
        """POST /pause → 200 e body com paused_hours."""
        client = _build_app(_make_mock_engine(), user_id=42)
        response = client.post("/api/admin/phone-health/pause?hours=12")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["user_id"] == 42
        assert body["paused_hours"] == 12

    def test_post_pause_validates_hours(self) -> None:
        """hours fora de [1, 168] → 422."""
        client = _build_app(_make_mock_engine(), user_id=42)
        response = client.post("/api/admin/phone-health/pause?hours=0")
        assert response.status_code == 422
        response = client.post("/api/admin/phone-health/pause?hours=200")
        assert response.status_code == 422

    def test_recommendation_banned(self) -> None:
        """Score=0/status=banned → recommendation menciona ban e instrui parar."""
        engine = _make_mock_engine(
            score_row={
                "score": 0,
                "status": "banned",
                "signals": {"events_24h": 5, "dlq_24h": 0, "optouts_24h": 0},
                "ultima_restricao_em": None,
                "pause_franz_until": None,
                "atualizado_em": None,
            },
        )
        client = _build_app(engine, user_id=7)
        response = client.get("/api/admin/phone-health")
        assert response.status_code == 200
        body = response.json()
        rec = body["recommendation"].lower()
        assert "ban" in rec
        assert "parar" in rec or "suporte" in rec