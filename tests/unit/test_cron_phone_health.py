"""Smoke tests para /api/cron/compute-phone-health-score.

Valida:
  - Auth por X-Cron-Secret
  - Iteração por todos os tenants ativos
  - UPSERT em phone_health_score
  - Cálculo correto do score (3 critical events → score=0, banned)
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))


# ── Helpers ─────────────────────────────────────────────────────────────

class _FakeResult:
    def __init__(self, rows: list = None, row=None) -> None:
        self.rows = rows or []
        self.row = row

    def fetchall(self) -> list:
        return self.rows

    def fetchone(self):
        return self.row


def _make_mock_engine(
    *,
    active_user_ids: list[int] | None = None,
    events_by_user: dict[int, list[tuple]] | None = None,
    dlq_by_user: dict[int, int] | None = None,
    optouts_by_user: dict[int, int] | None = None,
    upsert_calls: list[dict] | None = None,
) -> MagicMock:
    """Engine mock que simula compute_all_tenants().

    events_by_user: {user_id: [(severity, count), ...]}
    """
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    engine.connect.return_value.__exit__.return_value = None
    engine.begin.return_value.__enter__.return_value = conn
    engine.begin.return_value.__exit__.return_value = None

    events_by_user = events_by_user or {}
    dlq_by_user = dlq_by_user or {}
    optouts_by_user = optouts_by_user or {}

    def execute_side(stmt, params=None):
        sql = str(stmt).lower()
        result = _FakeResult()
        if "from users where status = 'active'" in sql:
            result.rows = [(uid,) for uid in (active_user_ids or [])]
        elif "from phone_health_events" in sql:
            uid = (params or {}).get("user_id")
            result.rows = events_by_user.get(uid, [])
        elif "from outbound_queue" in sql:
            uid = (params or {}).get("user_id")
            result.row = (dlq_by_user.get(uid, 0),)
        elif "from leads" in sql and "sdr_stage" in sql:
            uid = (params or {}).get("user_id")
            result.row = (optouts_by_user.get(uid, 0),)
        elif "insert into phone_health_score" in sql:
            if upsert_calls is not None:
                upsert_calls.append(dict(params or {}))
        return result

    conn.execute.side_effect = execute_side
    return engine


def _build_app(engine_mock: MagicMock) -> TestClient:
    """Constrói TestClient com CRON_SECRET configurado e engine mockado."""
    import os
    from backend.endpoints import cron_endpoints as mod

    # Seta CRON_SECRET para o módulo
    mod.CRON_SECRET = "test-secret-123"
    mod.engine = engine_mock

    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app)


# ── Tests ───────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestComputePhoneHealthScoreCron:

    def test_requires_cron_secret(self) -> None:
        """Sem X-Cron-Secret → 403."""
        client = _build_app(_make_mock_engine(active_user_ids=[]))
        response = client.post("/api/cron/compute-phone-health-score")
        assert response.status_code == 403

    def test_rejects_wrong_secret(self) -> None:
        """X-Cron-Secret errado → 403."""
        client = _build_app(_make_mock_engine(active_user_ids=[]))
        response = client.post(
            "/api/cron/compute-phone-health-score",
            headers={"X-Cron-Secret": "wrong-secret"},
        )
        assert response.status_code == 403

    def test_empty_tenant_list_returns_ok(self) -> None:
        """Sem tenants ativos → 200, processed=0."""
        client = _build_app(_make_mock_engine(active_user_ids=[]))
        response = client.post(
            "/api/cron/compute-phone-health-score",
            headers={"X-Cron-Secret": "test-secret-123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["tenants_processed"] == 0
        assert body["by_status"] == {}

    def test_healthy_tenant_keeps_score_100(self) -> None:
        """Tenant sem events/dlq/optouts → score=100, status=healthy."""
        client = _build_app(_make_mock_engine(
            active_user_ids=[1],
            events_by_user={1: []},
            dlq_by_user={1: 0},
            optouts_by_user={1: 0},
        ))
        response = client.post(
            "/api/cron/compute-phone-health-score",
            headers={"X-Cron-Secret": "test-secret-123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["tenants_processed"] == 1
        assert body["by_status"].get("healthy") == 1

    def test_three_critical_events_means_banned(self) -> None:
        """3 critical events (40 peso cada) → score=0, status=banned."""
        upsert_calls: list[dict] = []
        client = _build_app(_make_mock_engine(
            active_user_ids=[42],
            events_by_user={42: [("critical", 3)]},
            dlq_by_user={42: 0},
            optouts_by_user={42: 0},
            upsert_calls=upsert_calls,
        ))
        response = client.post(
            "/api/cron/compute-phone-health-score",
            headers={"X-Cron-Secret": "test-secret-123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["by_status"].get("banned") == 1
        # UPSERT chamado com score=0
        assert len(upsert_calls) == 1
        assert upsert_calls[0]["score"] == 0
        assert upsert_calls[0]["status"] == "banned"
        assert upsert_calls[0]["user_id"] == 42

    def test_score_calculation_with_mixed_signals(self) -> None:
        """2 warn (5*2=10) + 1 error (15) + 2 DLQ (10*2=20) + 1 opt-out (8) = 53 → degraded."""
        upsert_calls: list[dict] = []
        client = _build_app(_make_mock_engine(
            active_user_ids=[7],
            events_by_user={7: [("warn", 2), ("error", 1)]},
            dlq_by_user={7: 2},
            optouts_by_user={7: 1},
            upsert_calls=upsert_calls,
        ))
        response = client.post(
            "/api/cron/compute-phone-health-score",
            headers={"X-Cron-Secret": "test-secret-123"},
        )
        assert response.status_code == 200
        # 100 - 10 - 15 - 20 - 8 = 47 → restricted (>=20 e <50)
        assert upsert_calls[0]["score"] == 47
        assert upsert_calls[0]["status"] == "restricted"

    def test_multiple_tenants_grouped_by_status(self) -> None:
        """Vários tenants → resposta agrega por status."""
        client = _build_app(_make_mock_engine(
            active_user_ids=[1, 2, 3],
            events_by_user={
                1: [],  # healthy
                2: [("warn", 3)],  # 100-15=85 → healthy
                3: [("error", 5), ("warn", 2)],  # 100-75-10=15 → banned
            },
            dlq_by_user={1: 0, 2: 0, 3: 0},
            optouts_by_user={1: 0, 2: 0, 3: 0},
        ))
        response = client.post(
            "/api/cron/compute-phone-health-score",
            headers={"X-Cron-Secret": "test-secret-123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["tenants_processed"] == 3
        assert body["by_status"].get("healthy") == 2
        assert body["by_status"].get("banned") == 1


@pytest.mark.unit
class TestComputeService:
    """Testa o serviço puro (sem HTTP)."""

    def test_score_to_status_thresholds(self) -> None:
        from whatsapp.guards import score_to_status
        assert score_to_status(100) == "healthy"
        assert score_to_status(80) == "healthy"
        assert score_to_status(50) == "degraded"
        assert score_to_status(20) == "restricted"
        assert score_to_status(0) == "banned"
        assert score_to_status(19) == "banned"

    def test_compute_health_score_pure(self) -> None:
        """compute_health_score com engine mock — score puro, sem HTTP."""
        from backend.services.phone_health_service import compute_health_score

        engine = _make_mock_engine(
            active_user_ids=[1],
            events_by_user={1: [("critical", 1)]},  # 40 peso
            dlq_by_user={1: 1},  # 10 peso
            optouts_by_user={1: 0},
        )
        snap = compute_health_score(engine, user_id=1)
        assert snap.user_id == 1
        assert snap.score == 50  # 100 - 40 - 10
        assert snap.status == "degraded"
        assert snap.events_24h == 1
        assert snap.dlq_24h == 1
        assert snap.optouts_24h == 0
        assert snap.total_weight == 50