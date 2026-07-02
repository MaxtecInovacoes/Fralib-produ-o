"""Testes para provider-health (Sprint 0.1).

Cobre o painel de provedores externos:
  - services.provider_health_service.record_health (insert/upsert)
  - services.provider_health_service.compute_all_providers (agregação)
  - services.provider_health_service.view_provider_health_now (ordenação por status)
  - endpoints.superadmin_providers_endpoints.list_providers (GET /api/superadmin/dashboard/providers)
  - endpoints.cron_endpoints.refresh_provider_health (POST /api/cron/refresh-provider-health)

Markers:
  - @pytest.mark.unit: puro, com mocks
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))


# ── Mocks de baixo nível ────────────────────────────────────────────────


@dataclass
class _FakeRow:
    """Row retornada por _FakeResult — atributo nomeado por chave."""

    values: tuple = ()
    # Atributos nomeados (espelham as colunas da view v_provider_health_now)
    id: Any = None
    provider: str = ""
    endpoint: str = ""
    status: str = "unknown"
    latency_p95_ms: int | None = None
    success_rate_24h: float = 100.0
    calls_24h: int = 0
    errors_24h: int = 0
    custo_dia_brl: float = 0.0
    last_error: str | None = None
    last_checked_at: Any = None
    is_stale: bool = False
    metadata_json: dict[str, Any] = field(default_factory=dict)
    atualizado_em: Any = None
    severity_rank: int = 0

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def _asdict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "provider": self.provider,
            "endpoint": self.endpoint,
            "status": self.status,
            "latency_p95_ms": self.latency_p95_ms,
            "success_rate_24h": self.success_rate_24h,
            "calls_24h": self.calls_24h,
            "errors_24h": self.errors_24h,
            "custo_dia_brl": self.custo_dia_brl,
            "last_error": self.last_error,
            "last_checked_at": self.last_checked_at,
            "is_stale": self.is_stale,
            "metadata_json": self.metadata_json,
            "atualizado_em": self.atualizado_em,
            "severity_rank": self.severity_rank,
        }


class _FakeResult:
    def __init__(self, rows: list[_FakeRow] | None = None) -> None:
        self.rows = rows or []
        self.lastrowid: int | None = None

    def fetchone(self) -> _FakeRow | None:
        return self.rows[0] if self.rows else None

    def fetchall(self) -> list[_FakeRow]:
        return list(self.rows)


def _make_engine_with_providers(providers_state: list[dict]) -> _FakeEngine:
    """Cria engine onde SELECT na view v_provider_health_now retorna os providers."""
    rows = []
    for p in providers_state:
        rows.append(
            _FakeRow(
                values=(
                    0,
                    p["provider"],
                    p.get("endpoint", ""),
                    p["status"],
                    p.get("latency_p95_ms", 0),
                    float(p.get("success_rate_24h", 100.0)),
                    int(p.get("calls_24h", 0)),
                    int(p.get("errors_24h", 0)),
                    float(p.get("custo_dia_brl", 0.0)),
                    p.get("last_error"),
                    p.get("last_checked_at"),
                    p.get("is_stale", False),
                    p.get("metadata_json", {}),
                    p.get("atualizado_em"),
                    0,
                ),
                provider=p["provider"],
                endpoint=p.get("endpoint", ""),
                status=p["status"],
                latency_p95_ms=p.get("latency_p95_ms", 0),
                success_rate_24h=float(p.get("success_rate_24h", 100.0)),
                calls_24h=int(p.get("calls_24h", 0)),
                errors_24h=int(p.get("errors_24h", 0)),
                custo_dia_brl=float(p.get("custo_dia_brl", 0.0)),
                last_error=p.get("last_error"),
                last_checked_at=p.get("last_checked_at"),
                is_stale=p.get("is_stale", False),
                metadata_json=p.get("metadata_json", {}),
            )
        )
    return _FakeEngine(rows_by_sql={"from v_provider_health_now": rows})


class _FakeConn:
    """Conexão fake que registra todas as chamadas execute()."""

    def __init__(self, rows_by_sql: dict[str, list[_FakeRow]] | None = None) -> None:
        self.rows_by_sql = rows_by_sql or {}
        self.executed: list[tuple[str, dict]] = []
        self.commits = 0

    def execute(self, stmt, params: dict | None = None) -> _FakeResult:
        sql = str(stmt)
        normalized = sql.lower()
        self.executed.append((sql, params or {}))
        # Tenta match exato em rows_by_sql (normalizado).
        result = _FakeResult()
        for key, rows in self.rows_by_sql.items():
            if key in normalized:
                result.rows = rows
                break
        return result

    def commit(self) -> None:
        self.commits += 1

    def __enter__(self) -> "_FakeConn":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeEngine:
    """Engine mock que retorna _FakeConn configurável."""

    def __init__(self, rows_by_sql: dict[str, list[_FakeRow]] | None = None) -> None:
        self.rows_by_sql = rows_by_sql or {}
        self.connections: list[_FakeConn] = []

    def _new_conn(self) -> _FakeConn:
        conn = _FakeConn(self.rows_by_sql)
        self.connections.append(conn)
        return conn

    def connect(self) -> _FakeConn:
        return self._new_conn()

    def begin(self) -> _FakeConn:
        return self._new_conn()


def _make_engine_with_providers(providers_state: list[dict]) -> _FakeEngine:
    """Cria engine onde SELECT na view v_provider_health_now retorna os providers."""
    rows = []
    for p in providers_state:
        rows.append(
            _FakeRow(
                values=(
                    0,
                    p["provider"],
                    p.get("endpoint", ""),
                    p["status"],
                    p.get("latency_p95_ms", 0),
                    float(p.get("success_rate_24h", 100.0)),
                    int(p.get("calls_24h", 0)),
                    int(p.get("errors_24h", 0)),
                    float(p.get("custo_dia_brl", 0.0)),
                    p.get("last_error"),
                    p.get("last_checked_at"),
                    p.get("is_stale", False),
                    p.get("metadata_json", {}),
                    p.get("atualizado_em"),
                    0,
                ),
                provider=p["provider"],
                endpoint=p.get("endpoint", ""),
                status=p["status"],
                latency_p95_ms=p.get("latency_p95_ms", 0),
                success_rate_24h=float(p.get("success_rate_24h", 100.0)),
                calls_24h=int(p.get("calls_24h", 0)),
                errors_24h=int(p.get("errors_24h", 0)),
                custo_dia_brl=float(p.get("custo_dia_brl", 0.0)),
                last_error=p.get("last_error"),
                last_checked_at=p.get("last_checked_at"),
                is_stale=p.get("is_stale", False),
                metadata_json=p.get("metadata_json", {}),
            )
        )
    return _FakeEngine(rows_by_sql={"from v_provider_health_now": rows})


# ── record_health ───────────────────────────────────────────────────────


@pytest.mark.unit
class TestRecordHealth:
    """record_health insere e atualiza em provider_health."""

    def test_record_health_insere_linha(self) -> None:
        """Primeiro record_health de um provider deve executar INSERT na tabela provider_health."""
        from backend.services.provider_health_service import record_health

        engine = _FakeEngine()
        record_health(
            engine,
            provider="anthropic",
            status="healthy",
            latency_ms=420,
        )

        # Deve ter feito 1 connect + 1 begin (UPSERT em transação)
        assert len(engine.connections) >= 1
        # Captura todos os SQLs executados
        all_sqls = [s for conn in engine.connections for s, _ in conn.executed]
        joined = " | ".join(all_sqls).lower()
        assert "insert into provider_health" in joined
        assert "on conflict" in joined  # UPSERT
        # Params: provider + status + latency
        params_list = [p for conn in engine.connections for _, p in conn.executed]
        all_params: dict[str, Any] = {}
        for p in params_list:
            all_params.update(p)
        assert all_params.get("provider") == "anthropic"
        assert all_params.get("status") == "healthy"

    def test_record_health_upsert(self) -> None:
        """Chamar record_health 2x para o mesmo provider deve atualizar (UPSERT), não duplicar."""
        from backend.services.provider_health_service import record_health

        engine = _FakeEngine()
        record_health(engine, provider="openai", status="degraded", latency_ms=900)
        record_health(engine, provider="openai", status="healthy", latency_ms=200)

        # Os 2 calls devem ter sido em begin() (transação), totalizando 2 begin
        begin_count = sum(
            1 for c in engine.connections if c.executed and "insert into provider_health" in c.executed[0][0].lower()
        )
        assert begin_count == 2
        # Cada UPSERT mantém um único provider por linha (índice uq_provider_health_provider)
        # Verifica que ambos os parâmetros são do mesmo provider
        providers_used = [
            p.get("provider")
            for c in engine.connections
            for _, p in c.executed
            if p.get("provider") == "openai"
        ]
        assert providers_used.count("openai") == 2

    def test_record_health_persists_error(self) -> None:
        """record_health com error deve popular last_error e status=down/degraded."""
        from backend.services.provider_health_service import record_health

        engine = _FakeEngine()
        record_health(
            engine,
            provider="facebook_ads",
            status="down",
            latency_ms=0,
            error="401 Unauthorized: token revoked",
        )

        params_list = [
            p for c in engine.connections for _, p in c.executed
        ]
        all_params: dict[str, Any] = {}
        for p in params_list:
            all_params.update(p)
        assert all_params.get("last_error") == "401 Unauthorized: token revoked"
        assert all_params.get("status") == "down"


# ── compute_all_providers ───────────────────────────────────────────────


@pytest.mark.unit
class TestComputeAllProviders:
    """compute_all_providers deve agregar status por provider."""

    def test_compute_all_providers_agupa(self) -> None:
        """Múltiplos providers com status diferentes → retorna agregação por status."""
        from backend.services.provider_health_service import compute_all_providers

        providers = [
            {"provider": "anthropic", "status": "healthy"},
            {"provider": "openai", "status": "healthy"},
            {"provider": "facebook_ads", "status": "degraded"},
            {"provider": "hunter", "status": "down"},
            {"provider": "meowhats", "status": "healthy"},
        ]
        engine = _make_engine_with_providers(providers)
        summary = compute_all_providers(engine)

        # 5 providers processados
        assert summary["providers_total"] == 5
        # healthy = 3, degraded = 1, down = 1
        assert summary["by_status"]["healthy"] == 3
        assert summary["by_status"]["degraded"] == 1
        assert summary["by_status"]["down"] == 1
        # Algum provider em risco → flag global
        assert summary["has_risk"] is True
        # Lista detalhada inclui providers
        provider_names = [p["provider"] for p in summary["providers"]]
        assert "anthropic" in provider_names
        assert "facebook_ads" in provider_names

    def test_compute_all_providers_all_healthy_no_risk(self) -> None:
        """Todos providers healthy → has_risk=False."""
        from backend.services.provider_health_service import compute_all_providers

        providers = [
            {"provider": "anthropic", "status": "healthy"},
            {"provider": "openai", "status": "healthy"},
        ]
        engine = _make_engine_with_providers(providers)
        summary = compute_all_providers(engine)

        assert summary["providers_total"] == 2
        assert summary["by_status"]["healthy"] == 2
        assert summary["has_risk"] is False


# ── view v_provider_health_now ordenada por status ─────────────────────


@pytest.mark.unit
class TestViewProviderHealthNow:
    """view_provider_health_now deve retornar rows ordenadas por severidade."""

    def test_view_v_provider_health_now_ordenada_por_status(self) -> None:
        """A view/SELECT expõe provider, endpoint, status; ordering por status em severidade."""
        from backend.services.provider_health_service import view_provider_health_now

        providers = [
            {"provider": "anthropic", "status": "healthy"},
            {"provider": "facebook_ads", "status": "down"},
            {"provider": "openai", "status": "degraded"},
        ]
        engine = _make_engine_with_providers(providers)
        rows = view_provider_health_now(engine)

        assert len(rows) == 3
        # Cada row é um dict com chaves esperadas
        first = rows[0]
        assert "provider" in first
        assert "status" in first
        # Ordem: down primeiro (mais severo), depois degraded, depois healthy
        assert rows[0]["status"] == "down"
        assert rows[-1]["status"] == "healthy"

    def test_view_empty_returns_empty_list(self) -> None:
        """View sem providers → []."""
        from backend.services.provider_health_service import view_provider_health_now

        engine = _FakeEngine()
        rows = view_provider_health_now(engine)
        assert rows == []


# ── Endpoint /api/superadmin/dashboard/providers ────────────────────────


@pytest.mark.unit
class TestSuperadminProvidersEndpoint:
    """GET /api/superadmin/dashboard/providers retorna lista do service."""

    def test_endpoint_superadmin_providers_retorna_lista(self) -> None:
        """Endpoint autenticado como superadmin retorna payload com lista de providers."""
        from backend.endpoints import superadmin_providers_endpoints as mod
        from backend.core.auth import get_current_user

        providers = [
            {"provider": "anthropic", "status": "healthy"},
            {"provider": "facebook_ads", "status": "down"},
        ]
        engine = _make_engine_with_providers(providers)

        mod.engine = engine
        app = FastAPI()
        app.include_router(mod.router)

        superadmin_user = {"id": 1, "email": "admin@fralib.com", "role": "superadmin"}
        app.dependency_overrides[get_current_user] = lambda: superadmin_user

        client = TestClient(app)
        response = client.get("/api/superadmin/dashboard/providers")

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert "providers" in body
        assert "by_status" in body
        assert "providers_total" in body
        assert body["providers_total"] == 2
        assert body["by_status"]["healthy"] == 1
        assert body["by_status"]["down"] == 1

        provider_names = [p["provider"] for p in body["providers"]]
        assert "anthropic" in provider_names
        assert "facebook_ads" in provider_names

    def test_endpoint_requires_authentication(self) -> None:
        """Sem auth → 401."""
        from backend.endpoints import superadmin_providers_endpoints as mod
        from backend.core.auth import get_current_user

        providers = [{"provider": "anthropic", "status": "healthy"}]
        mod.engine = _make_engine_with_providers(providers)

        app = FastAPI()
        app.include_router(mod.router)

        def _reject():
            from fastapi import HTTPException
            raise HTTPException(401, "auth required")

        app.dependency_overrides[get_current_user] = _reject
        client = TestClient(app)
        response = client.get("/api/superadmin/dashboard/providers")

        assert response.status_code == 401


# ── Cron refresh-provider-health ────────────────────────────────────────


@pytest.mark.unit
class TestCronRefreshProviderHealth:
    """POST /api/cron/refresh-provider-health requer X-Cron-Secret."""

    def test_cron_refresh_requires_secret(self) -> None:
        """Sem X-Cron-Secret → 403."""
        from backend.endpoints import cron_endpoints as cron_mod
        from backend.services import provider_health_service as ph_mod

        cron_mod.CRON_SECRET = "test-secret-123"
        # Stub do record_health (não chega a ser chamado)
        ph_mod.engine = _FakeEngine()
        cron_mod.engine = ph_mod.engine

        app = FastAPI()
        app.include_router(cron_mod.router)
        client = TestClient(app)
        response = client.post("/api/cron/refresh-provider-health")
        assert response.status_code == 403

    def test_cron_refresh_calls_record_for_each_provider(self) -> None:
        """Com secret válido → deve iterar provedores e chamar record_health."""
        from backend.endpoints import cron_endpoints as cron_mod
        from backend.services import provider_health_service as ph_mod

        # Garante que o módulo aponte para o stubbed engine
        record_calls: list[dict] = []

        def fake_record(engine, provider, status, latency_ms, error=None):
            record_calls.append(
                {"provider": provider, "status": status, "latency_ms": latency_ms}
            )

        # Monkey-patch record_health dentro do módulo do cron
        original_record = ph_mod.record_health
        ph_mod.record_health = fake_record  # type: ignore[assignment]
        try:
            cron_mod.CRON_SECRET = "test-secret-123"
            app = FastAPI()
            app.include_router(cron_mod.router)
            client = TestClient(app)

            response = client.post(
                "/api/cron/refresh-provider-health",
                headers={"X-Cron-Secret": "test-secret-123"},
            )

            assert response.status_code == 200, response.text
            body = response.json()
            assert body["status"] == "ok"
            # Deve ter chamado record_health para cada provider conhecido
            assert len(record_calls) >= 5
            providers_called = {c["provider"] for c in record_calls}
            # Pelo menos os principais
            assert "anthropic" in providers_called or "openai" in providers_called
        finally:
            ph_mod.record_health = original_record  # type: ignore[assignment]