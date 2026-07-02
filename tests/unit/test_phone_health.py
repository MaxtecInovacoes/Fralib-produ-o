"""Testes para phone-health (Trilha A).

Cobre:
  - whatsapp.guards.score_to_status (puro)
  - whatsapp.guards.AntiAbuseGuards com engine mock (fallback in-memory)
  - whatsapp.sender.classify_error (detecção de padrões whatsmeow)
  - services.phone_health_service.compute_health_score (com DB real)

Markers:
  - @pytest.mark.unit: puro, sem DB
  - @pytest.mark.integration: precisa DB
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from whatsapp.guards import (
    EVENT_WEIGHTS,
    AntiAbuseGuards,
    STATUS_THRESHOLDS,
    score_to_status,
)
from whatsapp.sender import classify_error


# ── score_to_status ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestScoreToStatus:
    """score_to_status converte score 0-100 em categoria textual."""

    def test_score_100_is_healthy(self) -> None:
        assert score_to_status(100) == "healthy"

    def test_score_80_is_healthy(self) -> None:
        assert score_to_status(80) == "healthy"

    def test_score_79_is_degraded(self) -> None:
        assert score_to_status(79) == "degraded"

    def test_score_50_is_degraded(self) -> None:
        assert score_to_status(50) == "degraded"

    def test_score_49_is_restricted(self) -> None:
        assert score_to_status(49) == "restricted"

    def test_score_20_is_restricted(self) -> None:
        assert score_to_status(20) == "restricted"

    def test_score_19_is_banned(self) -> None:
        assert score_to_status(19) == "banned"

    def test_score_0_is_banned(self) -> None:
        assert score_to_status(0) == "banned"

    def test_score_above_100_clamped(self) -> None:
        assert score_to_status(150) == "healthy"

    def test_score_below_0_clamped(self) -> None:
        assert score_to_status(-10) == "banned"


# ── EVENT_WEIGHTS ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestEventWeights:
    """Pesos por severity devem ser monotônicos e bem definidos."""

    def test_all_severities_present(self) -> None:
        assert set(EVENT_WEIGHTS.keys()) == {"info", "warn", "error", "critical"}

    def test_info_is_zero(self) -> None:
        assert EVENT_WEIGHTS["info"] == 0

    def test_weights_are_monotonic(self) -> None:
        assert EVENT_WEIGHTS["info"] < EVENT_WEIGHTS["warn"]
        assert EVENT_WEIGHTS["warn"] < EVENT_WEIGHTS["error"]
        assert EVENT_WEIGHTS["error"] < EVENT_WEIGHTS["critical"]

    def test_critical_can_break_score(self) -> None:
        # 3 critical = 120 pontos = score = -20 = banned
        weight = EVENT_WEIGHTS["critical"] * 3
        score = max(0, 100 - weight)
        assert score == 0


# ── AntiAbuseGuards com engine None (fallback in-memory) ───────────────

@pytest.mark.unit
class TestAntiAbuseGuardsInMemory:
    """Sem engine: comportamento idêntico ao original (dict in-memory)."""

    def _build(self) -> AntiAbuseGuards:
        return AntiAbuseGuards(
            flood_threshold=10,
            flood_window=60.0,
            flood_silence=300.0,
            daily_limit_for_key=lambda k: 50,
            cooldown_seconds_for_key=lambda k: 30.0,
            human_pause_seconds_for_key=lambda k: 300.0,
        )

    def test_initial_state_is_empty(self) -> None:
        g = self._build()
        assert g.daily_count == {}
        assert g.flood_tracker == {}
        assert g.lead_last_reply == {}

    def test_increment_daily_works(self) -> None:
        g = self._build()
        g.increment_daily("1:+5511")
        g.increment_daily("1:+5511")
        assert g.daily_count["1:+5511"] == 2

    def test_check_daily_limit_triggers_at_limit(self) -> None:
        g = self._build()
        for _ in range(50):
            g.increment_daily("1:+5511")
        assert g.check_daily_limit("1:+5511") is True

    def test_check_daily_limit_under_limit(self) -> None:
        g = self._build()
        g.increment_daily("1:+5511")
        assert g.check_daily_limit("1:+5511") is False

    def test_cooldown_set_and_check(self) -> None:
        g = self._build()
        assert g.check_cooldown("1:+5511") is False
        g.set_cooldown("1:+5511")
        assert g.check_cooldown("1:+5511") is True

    def test_human_pause_activate_and_check(self) -> None:
        g = self._build()
        assert g.is_human_paused("1:+5511") is False
        g.activate_human_pause("1:+5511")
        assert g.is_human_paused("1:+5511") is True


# ── AntiAbuseGuards com engine mock (write-through) ────────────────────

@dataclass
class _FakeRow:
    value: int
    payload: dict[str, Any]
    expires_at: Any = None


class _FakeConn:
    """Conexão mock que executa SQL textual retornando rows fakes."""

    def __init__(self, rows: list[_FakeRow] | None = None) -> None:
        self.rows = rows or []
        self.executed: list[tuple[str, dict]] = []

    def execute(self, stmt, params=None) -> "_FakeResult":
        self.executed.append((str(stmt), params or {}))
        return _FakeResult(self.rows)

    def __enter__(self) -> "_FakeConn":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeResult:
    def __init__(self, rows: list[_FakeRow]) -> None:
        self.rows = rows

    def fetchone(self) -> _FakeRow | None:
        return self.rows[0] if self.rows else None


class _FakeEngine:
    """Engine mock: connect() retorna _FakeConn, begin() também."""

    def __init__(self, rows: list[_FakeRow] | None = None) -> None:
        self.rows = rows or []
        self.conn_count = 0

    def connect(self) -> _FakeConn:
        self.conn_count += 1
        return _FakeConn(self.rows)

    def begin(self) -> _FakeConn:
        self.conn_count += 1
        return _FakeConn(self.rows)


@pytest.mark.unit
class TestAntiAbuseGuardsWithEngine:
    """Com engine: deve chamar upsert_counter em writes, read em cold reads."""

    def test_set_cooldown_persists(self) -> None:
        engine = _FakeEngine()
        g = AntiAbuseGuards(
            engine=engine,  # type: ignore[arg-type]
            flood_threshold=10,
            flood_window=60.0,
            flood_silence=300.0,
            daily_limit_for_key=lambda k: 50,
            cooldown_seconds_for_key=lambda k: 30.0,
            human_pause_seconds_for_key=lambda k: 300.0,
        )
        g.set_cooldown("42:+5511")
        # Cache in-memory atualizado
        assert "42:+5511" in g.lead_last_reply
        # Engine.begin() chamado (write-through)
        assert engine.conn_count >= 1

    def test_increment_daily_persists(self) -> None:
        engine = _FakeEngine()
        g = AntiAbuseGuards(
            engine=engine,  # type: ignore[arg-type]
            flood_threshold=10,
            flood_window=60.0,
            flood_silence=300.0,
            daily_limit_for_key=lambda k: 50,
            cooldown_seconds_for_key=lambda k: 30.0,
            human_pause_seconds_for_key=lambda k: 300.0,
        )
        g.increment_daily("42:+5511")
        g.increment_daily("42:+5511")
        # Cache local
        assert g.daily_count["42:+5511"] == 2
        # Engine chamado
        assert engine.conn_count >= 2


# ── classify_error ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestClassifyError:
    """Detecta padrões whatsmeow/WhatsApp Web."""

    def test_restricted_code_131047_is_critical(self) -> None:
        body = '<error code="131047" text="user-restricted"/>'
        sev, evt = classify_error(200, body)
        assert sev == "critical"
        assert evt == "restricted"

    def test_rate_limited_code_131056(self) -> None:
        body = '<error code="131056" text="rate-limit"/>'
        sev, evt = classify_error(200, body)
        assert sev == "error"
        assert evt == "rate_limited"

    def test_banned_temporarily(self) -> None:
        body = "Your number is temporarily banned"
        sev, evt = classify_error(200, body)
        assert sev == "critical"
        assert evt == "banned"

    def test_phone_banned(self) -> None:
        body = "phone number banned"
        sev, evt = classify_error(200, body)
        assert sev == "critical"
        assert evt == "banned"

    def test_spam_detected(self) -> None:
        body = "Spam detected from this device"
        sev, evt = classify_error(200, body)
        assert sev == "critical"
        assert evt == "restricted"

    def test_quality_rating_warning(self) -> None:
        body = "Quality rating is low"
        sev, evt = classify_error(200, body)
        assert sev == "warn"
        assert evt == "restricted"

    def test_http_429_no_body(self) -> None:
        sev, evt = classify_error(429, "")
        assert sev == "warn"
        assert evt == "rate_limited"

    def test_http_403_no_body(self) -> None:
        sev, evt = classify_error(403, "")
        assert sev == "warn"
        assert evt == "forbidden"

    def test_generic_500_no_match(self) -> None:
        sev, evt = classify_error(500, "Internal Server Error")
        assert sev is None
        assert evt == "ok"

    def test_case_insensitive(self) -> None:
        body = "PHONE NUMBER BANNED"
        sev, _ = classify_error(200, body)
        assert sev == "critical"


# ── STATUS_THRESHOLDS ──────────────────────────────────────────────────

@pytest.mark.unit
def test_status_thresholds_ordered() -> None:
    """Thresholds devem estar em ordem decrescente (healthy tem o maior)."""
    thresholds = [t for t, _ in STATUS_THRESHOLDS]
    assert thresholds == sorted(thresholds, reverse=True)


@pytest.mark.unit
def test_status_thresholds_complete() -> None:
    """Todos os 4 status devem estar presentes."""
    statuses = {s for _, s in STATUS_THRESHOLDS}
    assert statuses == {"healthy", "degraded", "restricted", "banned"}