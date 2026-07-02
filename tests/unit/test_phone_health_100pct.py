"""Testes finais 100% Trilha A.

Cobre:
  - effective_daily_limit + auto-throttle factor
  - auto-pause quando score=banned
  - widget em /admin/sdr_settings (HTML presence)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))

ADMIN_HTML = _ROOT / "frontend" / "admin.html"


# ── effective_daily_limit / auto-throttle ──────────────────────────────

@pytest.mark.unit
class TestEffectiveDailyLimit:
    """sdr_settings.effective_daily_limit aplica auto-throttle baseado em score."""

    def _settings(self, daily_limit: int = 50, auto_throttle: bool = True) -> dict:
        return {
            "limits": {"daily_limit_per_lead": daily_limit},
            "auto_throttle_enabled": auto_throttle,
        }

    def test_score_100_full_limit(self) -> None:
        from backend.services.sdr_settings import effective_daily_limit
        assert effective_daily_limit(self._settings(), 100) == 50

    def test_score_80_full_limit(self) -> None:
        from backend.services.sdr_settings import effective_daily_limit
        assert effective_daily_limit(self._settings(), 80) == 50

    def test_score_79_70_percent(self) -> None:
        from backend.services.sdr_settings import effective_daily_limit
        assert effective_daily_limit(self._settings(), 79) == 35  # 50*0.7

    def test_score_50_70_percent(self) -> None:
        from backend.services.sdr_settings import effective_daily_limit
        assert effective_daily_limit(self._settings(), 50) == 35

    def test_score_49_50_percent(self) -> None:
        from backend.services.sdr_settings import effective_daily_limit
        assert effective_daily_limit(self._settings(), 49) == 25  # 50*0.5

    def test_score_20_50_percent(self) -> None:
        from backend.services.sdr_settings import effective_daily_limit
        assert effective_daily_limit(self._settings(), 20) == 25

    def test_score_19_10_percent(self) -> None:
        from backend.services.sdr_settings import effective_daily_limit
        assert effective_daily_limit(self._settings(), 19) == 5  # 50*0.1

    def test_score_0_10_percent(self) -> None:
        from backend.services.sdr_settings import effective_daily_limit
        assert effective_daily_limit(self._settings(), 0) == 5

    def test_score_none_no_throttle(self) -> None:
        from backend.services.sdr_settings import effective_daily_limit
        assert effective_daily_limit(self._settings(), None) == 50

    def test_auto_throttle_disabled_keeps_full(self) -> None:
        from backend.services.sdr_settings import effective_daily_limit
        # Mesmo com score baixo, se auto_throttle desativado, mantém full
        assert effective_daily_limit(self._settings(50, auto_throttle=False), 0) == 50

    def test_minimum_is_one(self) -> None:
        from backend.services.sdr_settings import effective_daily_limit
        # Base=1 com score=0 → 1*0.1=0.1 → max(1, 0) = 1
        assert effective_daily_limit(self._settings(daily_limit=1), 0) == 1

    def test_respects_custom_base(self) -> None:
        from backend.services.sdr_settings import effective_daily_limit
        # base=200 com score=50 → 200*0.7 = 140
        assert effective_daily_limit(self._settings(daily_limit=200), 50) == 140


# ── auto-pause quando score=banned ─────────────────────────────────────

@pytest.mark.unit
class TestAutoPauseOnBanned:
    """phone_health_service.persist_health_score auto-pausa quando status=banned."""

    def _fake_engine(self) -> MagicMock:
        engine = MagicMock()
        conn = MagicMock()
        engine.begin.return_value.__enter__.return_value = conn
        engine.begin.return_value.__exit__.return_value = None
        return engine, conn

    def _snap_banned(self) -> Any:
        from backend.services.phone_health_service import TenantHealthSnapshot
        return TenantHealthSnapshot(
            user_id=99,
            score=0,
            status="banned",
            events_weight=120,
            dlq_weight=0,
            optout_weight=0,
            total_weight=120,
            events_24h=3,
            dlq_24h=0,
            optouts_24h=0,
        )

    def _snap_healthy(self) -> Any:
        from backend.services.phone_health_service import TenantHealthSnapshot
        return TenantHealthSnapshot(
            user_id=99,
            score=100,
            status="healthy",
            events_weight=0,
            dlq_weight=0,
            optout_weight=0,
            total_weight=0,
            events_24h=0,
            dlq_24h=0,
            optouts_24h=0,
        )

    def test_banned_upsert_includes_pause_until(self) -> None:
        from backend.services.phone_health_service import persist_health_score
        engine, conn = self._fake_engine()
        persist_health_score(engine, self._snap_banned())

        # 2 statements: UPSERT + INSERT event (auto_paused)
        assert conn.execute.call_count == 2
        # 1ª chamada: UPSERT com pause_franz_until
        first_sql = str(conn.execute.call_args_list[0][0][0])
        assert "pause_franz_until" in first_sql
        assert "24 hours" in first_sql or "24" in first_sql

    def test_banned_inserts_auto_paused_event(self) -> None:
        from backend.services.phone_health_service import persist_health_score
        engine, conn = self._fake_engine()
        persist_health_score(engine, self._snap_banned())

        # 2ª chamada: INSERT event
        second_call = conn.execute.call_args_list[1]
        second_sql = str(second_call[0][0])
        second_params = second_call[0][1]
        assert "INSERT INTO phone_health_events" in second_sql
        # severity e event_type são literais no SQL (não params)
        assert "'critical'" in second_sql
        assert "'auto_paused'" in second_sql
        assert second_params["user_id"] == 99
        assert '"reason": "score=0"' in second_params["detail"]
        assert '"auto_pause_hours": 24' in second_params["detail"]

    def test_healthy_no_pause(self) -> None:
        from backend.services.phone_health_service import persist_health_score
        engine, conn = self._fake_engine()
        persist_health_score(engine, self._snap_healthy())

        # 1 statement: UPSERT sem pause_franz_until
        assert conn.execute.call_count == 1
        first_sql = str(conn.execute.call_args_list[0][0][0])
        assert "pause_franz_until" not in first_sql

    def test_degraded_no_pause(self) -> None:
        from backend.services.phone_health_service import TenantHealthSnapshot, persist_health_score
        engine, conn = self._fake_engine()
        snap = TenantHealthSnapshot(
            user_id=1, score=60, status="degraded",
            events_weight=40, dlq_weight=0, optout_weight=0,
            total_weight=40, events_24h=2, dlq_24h=0, optouts_24h=0,
        )
        persist_health_score(engine, snap)
        # degraded NÃO é banned → 1 statement, sem pause
        assert conn.execute.call_count == 1


# ── widget sdr_phone_health no admin.html ──────────────────────────────

@pytest.mark.unit
class TestSdrPhoneHealthWidget:

    REQUIRED_IDS = [
        "sdrPhoneHealthWidget",
        "sdrPhoneHealthSync",
        "sdrPhoneHealthScore",
        "sdrPhoneHealthStatus",
        "sdrPhoneHealthEffectiveLimit",
        "sdrAutoThrottleEnabled",
    ]

    @pytest.fixture(scope="class")
    def admin_html(self) -> str:
        return ADMIN_HTML.read_text(encoding="utf-8")

    @pytest.mark.parametrize("element_id", REQUIRED_IDS)
    def test_widget_id_present(self, admin_html: str, element_id: str) -> None:
        assert f'id="{element_id}"' in admin_html, f"id {element_id} ausente"

    def test_widget_title(self, admin_html: str) -> None:
        assert "Saúde do número" in admin_html

    def test_loadSdrPhoneHealthWidget_function(self, admin_html: str) -> None:
        assert "async function loadSdrPhoneHealthWidget" in admin_html

    def test_auto_throttle_label(self, admin_html: str) -> None:
        assert "Auto-throttle" in admin_html

    def test_carregarSdrConfig_calls_widget(self, admin_html: str) -> None:
        assert "loadSdrPhoneHealthWidget" in admin_html

    def test_salvarSdrConfig_persists_auto_throttle(self, admin_html: str) -> None:
        # Procura o payload inclui auto_throttle_enabled
        assert "auto_throttle_enabled" in admin_html

    def test_sdr_carregar_reads_auto_throttle(self, admin_html: str) -> None:
        # carregarSdrConfig chama _sdrSetChecked no toggle
        assert "_sdrSetChecked('sdrAutoThrottleEnabled'" in admin_html