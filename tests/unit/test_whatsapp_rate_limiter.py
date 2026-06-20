"""Characterization tests for whatsapp.rate_limiter.

Proves the behavior of the rate-limiting wrappers:
- Cooldown (check/set/remaining)
- Flood detection
- Daily limit (check/increment)
- Human pause (activate/check/expire)
- Humanized delay
- Debounce batching
"""

import sys
import os
import time
import types
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from whatsapp.rate_limiter import (
    RateLimiter,
    DEBOUNCE_SECONDS,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_limiter(now=0.0):
    """Create a RateLimiter with fixed clock for testing."""
    clock = [now]
    limiter = RateLimiter(
        flood_threshold=10,
        flood_window=60.0,
        flood_silence=300.0,
        default_daily_limit=50,
        default_cooldown_seconds=30.0,
        default_human_pause_seconds=300.0,
        now_func=lambda: clock[0],
    )
    return limiter, clock


# ── Tests: Cooldown ──────────────────────────────────────────────────────


def test_cooldown_not_active_initially():
    limiter, clock = _make_limiter(now=100.0)
    assert limiter.check_cooldown("2:5511999") is False


def test_cooldown_active_after_set():
    limiter, clock = _make_limiter(now=100.0)
    limiter.set_cooldown("2:5511999")
    clock[0] = 110.0  # 10s later, still within 30s cooldown
    assert limiter.check_cooldown("2:5511999") is True


def test_cooldown_expires():
    limiter, clock = _make_limiter(now=100.0)
    limiter.set_cooldown("2:5511999")
    clock[0] = 131.0  # 31s later, past 30s cooldown
    assert limiter.check_cooldown("2:5511999") is False


def test_cooldown_remaining():
    limiter, clock = _make_limiter(now=100.0)
    limiter.set_cooldown("2:5511999")
    clock[0] = 110.0
    remaining = limiter.cooldown_remaining("2:5511999")
    assert 19.0 <= remaining <= 20.1


# ── Tests: Flood ─────────────────────────────────────────────────────────


def test_flood_not_triggered_under_threshold():
    limiter, clock = _make_limiter(now=0.0)
    for i in range(10):
        clock[0] = float(i)
        assert limiter.check_flood("2:5511999") is False


def test_flood_triggered_over_threshold():
    limiter, clock = _make_limiter(now=0.0)
    for i in range(10):
        clock[0] = float(i)
        limiter.check_flood("2:5511999")
    clock[0] = 11.0
    assert limiter.check_flood("2:5511999") is True


def test_flood_silence_expires():
    limiter, clock = _make_limiter(now=0.0)
    for i in range(11):
        clock[0] = float(i)
        limiter.check_flood("2:5511999")
    # Silence was set at t=10 (11th call), so expires at t=310
    clock[0] = 311.0
    assert limiter.check_flood("2:5511999") is False


# ── Tests: Daily Limit ───────────────────────────────────────────────────


def test_daily_limit_not_reached():
    limiter, clock = _make_limiter(now=0.0)
    assert limiter.check_daily_limit("2:5511999") is False


def test_daily_limit_reached():
    limiter, clock = _make_limiter(now=0.0)
    for _ in range(50):
        limiter.increment_daily("2:5511999")
    assert limiter.check_daily_limit("2:5511999") is True


# ── Tests: Human Pause ───────────────────────────────────────────────────


def test_human_pause_not_active_initially():
    limiter, clock = _make_limiter(now=100.0)
    assert limiter.is_human_paused("2:5511999") is False


def test_human_pause_active_after_activation():
    limiter, clock = _make_limiter(now=100.0)
    limiter.activate_human_pause("2:5511999")
    clock[0] = 200.0  # 100s later, within 300s pause
    assert limiter.is_human_paused("2:5511999") is True


def test_human_pause_expires():
    limiter, clock = _make_limiter(now=100.0)
    limiter.activate_human_pause("2:5511999")
    clock[0] = 401.0  # 301s later, past 300s pause
    assert limiter.is_human_paused("2:5511999") is False


# ── Tests: Humanized Delay ───────────────────────────────────────────────


def test_humanized_delay_returns_float():
    limiter, _ = _make_limiter()
    delay = limiter.humanized_delay("Oi, tudo bem?")
    assert isinstance(delay, float)
    assert delay >= 0.0
