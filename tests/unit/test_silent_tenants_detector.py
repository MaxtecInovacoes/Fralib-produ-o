"""Tests Sprint 3.3 — Detector de Tenant Silencioso + Endpoints superadmin.

Cobre:
- 5 critérios individuais (admin_inactive_7d, no_new_leads_15d, no_cost_events_3d,
  subscription_expiring_7d, trial_active_no_use_14d)
- Detector (dedupe de alertas OPEN, mock de engine)
- Notificações por email (skip se env nao setado)
- Endpoints (list, acknowledge, resolve, run-detector)

Padrao do projeto: MagicMock para engine + TestClient isolado.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))

os.environ.setdefault("SUPERADMIN_EMAIL", "su@x.com")


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_mock_engine(
    *,
    admin_inactive_rows: list[dict] | None = None,
    no_new_leads_rows: list[dict] | None = None,
    no_cost_events_rows: list[dict] | None = None,
    subscription_expiring_rows: list[dict] | None = None,
    trial_no_use_rows: list[dict] | None = None,
    existing_open_alerts: list[tuple[int, str]] | None = None,
) -> MagicMock:
    """Monta mock engine que responde conforme o SQL executado.

    Cada chave acima injeta rows no critério correspondente. ``existing_open_alerts``
    é a lista de ``(tenant_id, alert_type)`` já abertos — usado para validar dedupe.
    """
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    engine.connect.return_value.__exit__.return_value = None
    engine.begin.return_value.__enter__.return_value = conn
    engine.begin.return_value.__exit__.return_value = None

    def execute_side(stmt, params=None):
        sql = str(stmt).lower()
        result = MagicMock()

        # SELECT 1 FROM tenant_alerts WHERE status='open'  — dedupe check
        if "from tenant_alerts" in sql and "status = 'open'" in sql:
            rows = existing_open_alerts or []
            tenant_id = (params or {}).get("tenant_id")
            alert_type = (params or {}).get("alert_type")
            found = any(
                r[0] == tenant_id and r[1] == alert_type
                for r in rows
            )
            # _open_alert_exists calls .fetchone() — return (1,) when found
            if found:
                result.fetchone.return_value = (1,)
            else:
                result.fetchone.return_value = None
            result.scalar.return_value = 1 if found else None
            return result

        # Criteria 5: trial_active_no_use_14d — match first (most specific: 14 days)
        # SQL novo: SELECT id, criado_em, ultimo_acesso FROM users WHERE ... '14 days'
        # AND status_plano = 'trial'. Match unico por combinacao: 14 days + status_plano
        if "14 days" in sql and "status_plano" in sql:
            rows = trial_no_use_rows or []
            result.fetchall.return_value = [
                (r["tenant_id"], r.get("criado_em"), r.get("ultimo_acesso"))
                for r in rows
            ]
            return result

        # Criteria 1: admin_inactive_7d
        if "ultimo_acesso is null" in sql and "7 days" in sql:
            rows = admin_inactive_rows or []
            result.fetchall.return_value = [
                (r["tenant_id"], r.get("ultimo_acesso")) for r in rows
            ]
            return result

        # Criteria 2: no_new_leads_15d
        if "from leads l" in sql:
            rows = no_new_leads_rows or []
            result.fetchall.return_value = [
                (r["tenant_id"], r.get("last_lead_at")) for r in rows
            ]
            return result

        # Criteria 3: no_cost_events_3d
        if "from cost_events" in sql:
            rows = no_cost_events_rows or []
            result.fetchall.return_value = [
                (r["tenant_id"],) for r in rows
            ]
            return result

        # Criteria 4: subscription_expiring_7d
        if "plan_expires_at between" in sql:
            rows = subscription_expiring_rows or []
            result.fetchall.return_value = [
                (r["tenant_id"], r.get("plan_expires_at")) for r in rows
            ]
            return result

        # INSERT/UPDATE tenant_alerts
        result.rowcount = 1
        result.fetchone.return_value = None
        result.fetchall.return_value = []
        return result

    conn.execute.side_effect = execute_side
    return engine


def _build_endpoint_app(engine_mock: MagicMock, usuario: dict | None) -> TestClient:
    """Monta TestClient isolado para os endpoints superadmin/silent-tenants."""
    from backend.core.auth import get_current_user
    from backend.endpoints import superadmin_silent_tenants_endpoints as mod

    mod.engine = engine_mock

    app = FastAPI()
    app.include_router(mod.router)
    if usuario is not None:
        app.dependency_overrides[get_current_user] = lambda: usuario
    return TestClient(app)


# ── Tests: critérios individuais ─────────────────────────────────────────

@pytest.mark.unit
class TestDetectorCriteria:

    def test_admin_inactive_7d_detected(self) -> None:
        """Critério 1: retorna dict {tenant_id, alert_type, severity}."""
        from backend.jobs.detect_silent_tenants import detect_admin_inactive_7d

        engine = _make_mock_engine(
            admin_inactive_rows=[
                {"tenant_id": 10, "ultimo_acesso": None},
                {"tenant_id": 20, "ultimo_acesso": "2026-06-01"},
            ],
        )
        results = detect_admin_inactive_7d(engine)
        assert len(results) == 2
        assert all(r["alert_type"] == "admin_inactive_7d" for r in results)
        assert all(r["severity"] == "warning" for r in results)
        tenant_ids = {r["tenant_id"] for r in results}
        assert tenant_ids == {10, 20}

    def test_no_new_leads_15d_detected(self) -> None:
        """Critério 2: detecta tenants sem leads > 15d."""
        from backend.jobs.detect_silent_tenants import detect_no_new_leads_15d

        engine = _make_mock_engine(
            no_new_leads_rows=[
                {"tenant_id": 30, "last_lead_at": None},
                {"tenant_id": 31, "last_lead_at": "2026-06-15"},
            ],
        )
        results = detect_no_new_leads_15d(engine)
        assert len(results) == 2
        assert all(r["alert_type"] == "no_new_leads_15d" for r in results)
        assert all(r["severity"] == "info" for r in results)

    def test_no_cost_events_3d_detected(self) -> None:
        """Critério 3: detecta tenants ativos sem custo > 3d."""
        from backend.jobs.detect_silent_tenants import detect_no_cost_events_3d

        engine = _make_mock_engine(
            no_cost_events_rows=[
                {"tenant_id": 40},
                {"tenant_id": 41},
            ],
        )
        results = detect_no_cost_events_3d(engine)
        assert len(results) == 2
        assert all(r["alert_type"] == "no_cost_events_3d" for r in results)
        # tenant ativo sem uso = warning
        assert all(r["severity"] == "warning" for r in results)

    def test_subscription_expiring_7d_detected(self) -> None:
        """Critério 4: detecta planos vencendo em <= 7d."""
        from backend.jobs.detect_silent_tenants import detect_subscription_expiring_7d

        engine = _make_mock_engine(
            subscription_expiring_rows=[
                {"tenant_id": 50, "plan_expires_at": "2026-07-05"},
            ],
        )
        results = detect_subscription_expiring_7d(engine)
        assert len(results) == 1
        assert results[0]["tenant_id"] == 50
        assert results[0]["alert_type"] == "subscription_expiring_7d"
        # Plano vencendo = critical (risco de churn iminente)
        assert results[0]["severity"] == "critical"

    def test_trial_active_no_use_14d_detected(self) -> None:
        """Critério 5: detecta trials > 14d sem login."""
        from backend.jobs.detect_silent_tenants import detect_trial_active_no_use_14d

        engine = _make_mock_engine(
            trial_no_use_rows=[
                {"tenant_id": 60, "criado_em": "2026-06-01"},
            ],
        )
        results = detect_trial_active_no_use_14d(engine)
        assert len(results) == 1
        assert results[0]["tenant_id"] == 60
        assert results[0]["alert_type"] == "trial_active_no_use_14d"
        # Trial sem uso por > 14d = warning (churn eminente)
        assert results[0]["severity"] == "warning"


# ── Tests: detector agregado ──────────────────────────────────────────────

@pytest.mark.unit
class TestDetectorAggregate:

    def test_detect_all_returns_list_with_engine_mock(self) -> None:
        """detect_all executa todos os 5 critérios e retorna lista agregada."""
        from backend.jobs.detect_silent_tenants import detect_all

        engine = _make_mock_engine(
            admin_inactive_rows=[{"tenant_id": 1, "ultimo_acesso": None}],
            no_new_leads_rows=[{"tenant_id": 2, "last_lead_at": None}],
            no_cost_events_rows=[{"tenant_id": 3}],
            subscription_expiring_rows=[{"tenant_id": 4, "plan_expires_at": "2026-07-05"}],
            trial_no_use_rows=[{"tenant_id": 5, "criado_em": "2026-06-01"}],
        )
        results = detect_all(engine)
        # 1 de cada = 5 total
        assert len(results) == 5
        types = {r["alert_type"] for r in results}
        assert types == {
            "admin_inactive_7d",
            "no_new_leads_15d",
            "no_cost_events_3d",
            "subscription_expiring_7d",
            "trial_active_no_use_14d",
        }

    def test_detect_all_dedups_open_alerts(self) -> None:
        """Não duplica quando já existe alerta OPEN para (tenant, type)."""
        from backend.jobs.detect_silent_tenants import detect_all

        # Tenant 1 já tem admin_inactive_7d OPEN.
        engine = _make_mock_engine(
            admin_inactive_rows=[{"tenant_id": 1, "ultimo_acesso": None}],
            existing_open_alerts=[(1, "admin_inactive_7d")],
        )
        results = detect_all(engine)
        # Tenant 1 NÃO deve aparecer (já tem open).
        tenant_ids = {r["tenant_id"] for r in results}
        assert 1 not in tenant_ids

    def test_send_email_notifications_skip_when_env_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sem SILENT_TENANT_ALERT_EMAIL -> NO-OP, sem raise."""
        from backend.jobs import detect_silent_tenants

        monkeypatch.delenv("SILENT_TENANT_ALERT_EMAIL", raising=False)
        # Nao pode levantar mesmo com alerts mockados
        detect_silent_tenants.send_email_notifications([
            {"tenant_id": 1, "alert_type": "admin_inactive_7d", "severity": "warning"},
        ])
        # Se chegou aqui sem raise, passou.


# ── Tests: endpoints ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestSuperadminSilentTenantsEndpoints:

    def test_list_requires_superadmin(self) -> None:
        """role=user -> 403."""
        client = _build_endpoint_app(
            _make_mock_engine(),
            usuario={"user_id": 1, "role": "user", "is_superadmin": False},
        )
        # Sem auth (dep override nao aplica para require_superadmin do core)
        response = client.get("/api/superadmin/silent-tenants/")
        # 401 ou 403 dependendo de como a dep é resolvida no TestClient
        assert response.status_code in (401, 403)

    def test_acknowledge_changes_status(self) -> None:
        """POST /{id}/acknowledge -> atualiza status para 'acknowledged'."""
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = conn
        engine.connect.return_value.__exit__.return_value = None

        result = MagicMock()
        result.rowcount = 1
        conn.execute.return_value = result

        # superadmin autenticado
        from backend.core.auth import get_current_user
        with patch(
            "backend.core.access_control.is_superadmin", return_value=True
        ):
            from backend.endpoints import superadmin_silent_tenants_endpoints as mod
            mod.engine = engine
            app = FastAPI()
            app.include_router(mod.router)
            app.dependency_overrides[get_current_user] = lambda: {
                "user_id": 99, "email": "su@x.com", "role": "user",
            }
            # Mock get_db para evitar conexao real
            from backend.core.database import get_db
            fake_db = MagicMock()
            fake_db.execute.return_value = result
            app.dependency_overrides[get_db] = lambda: fake_db
            client = TestClient(app)
            response = client.post("/api/superadmin/silent-tenants/42/acknowledge")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["alert_id"] == 42

    def test_resolve_changes_status(self) -> None:
        """POST /{id}/resolve -> atualiza status para 'resolved'."""
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__.return_value = conn
        engine.connect.return_value.__exit__.return_value = None

        result = MagicMock()
        result.rowcount = 1
        conn.execute.return_value = result

        with patch(
            "backend.core.access_control.is_superadmin", return_value=True
        ):
            from backend.endpoints import superadmin_silent_tenants_endpoints as mod
            mod.engine = engine
            app = FastAPI()
            app.include_router(mod.router)
            from backend.core.auth import get_current_user
            app.dependency_overrides[get_current_user] = lambda: {
                "user_id": 99, "email": "su@x.com", "role": "user",
            }
            from backend.core.database import get_db
            fake_db = MagicMock()
            fake_db.execute.return_value = result
            app.dependency_overrides[get_db] = lambda: fake_db
            client = TestClient(app)
            response = client.post("/api/superadmin/silent-tenants/42/resolve")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["alert_id"] == 42

    def test_run_detector_endpoint_executes_sync(self) -> None:
        """POST /run-detector -> executa detect_all sincrono e retorna contagem."""
        engine = _make_mock_engine(
            admin_inactive_rows=[{"tenant_id": 1, "ultimo_acesso": None}],
        )
        with patch(
            "backend.core.access_control.is_superadmin", return_value=True
        ):
            from backend.endpoints import superadmin_silent_tenants_endpoints as mod
            mod.engine = engine
            # patcha detect_all no modulo importado pelo endpoint
            from backend.jobs import detect_silent_tenants as _dst
            with patch.object(
                _dst, "detect_all",
                return_value=[
                    {"tenant_id": 1, "alert_type": "admin_inactive_7d", "severity": "warning"},
                ],
            ):
                app = FastAPI()
                app.include_router(mod.router)
                from backend.core.auth import get_current_user
                app.dependency_overrides[get_current_user] = lambda: {
                    "user_id": 99, "email": "su@x.com", "role": "user",
                }
                from backend.core.database import get_db
                fake_db = MagicMock()
                app.dependency_overrides[get_db] = lambda: fake_db
                client = TestClient(app)
                response = client.post("/api/superadmin/silent-tenants/run-detector")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["detected"] >= 1
        assert "results" in body
