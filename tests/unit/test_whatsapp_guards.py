from datetime import date
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from whatsapp.guards import AntiAbuseGuards, SavedContactsRegistry


class _Clock:
    def __init__(self):
        self.now = 1000.0
        self.today = date(2026, 6, 17)

    def time(self):
        return self.now

    def date(self):
        return self.today


def _guards(clock: _Clock):
    return AntiAbuseGuards(
        flood_threshold=2,
        flood_window=10.0,
        flood_silence=30.0,
        daily_limit_for_key=lambda key: 2,
        cooldown_seconds_for_key=lambda key: 5.0,
        human_pause_seconds_for_key=lambda key: 20.0,
        now_func=clock.time,
        today_func=clock.date,
    )


def test_flood_silences_after_threshold_and_expires():
    clock = _Clock()
    guards = _guards(clock)

    assert not guards.check_flood("2:lead")
    assert not guards.check_flood("2:lead")
    assert guards.check_flood("2:lead")

    clock.now += 31.0
    assert not guards.check_flood("2:lead")


def test_daily_limit_resets_when_day_changes():
    clock = _Clock()
    guards = _guards(clock)

    guards.increment_daily("2:lead")
    guards.increment_daily("2:lead")
    assert guards.check_daily_limit("2:lead")

    clock.today = date(2026, 6, 18)
    assert not guards.check_daily_limit("2:lead")


def test_cooldown_reports_remaining_time():
    clock = _Clock()
    guards = _guards(clock)

    guards.set_cooldown("2:lead")
    clock.now += 2.0

    assert guards.check_cooldown("2:lead")
    assert guards.cooldown_remaining("2:lead") == 3.0

    clock.now += 4.0
    assert not guards.check_cooldown("2:lead")


def test_human_pause_expires():
    clock = _Clock()
    guards = _guards(clock)

    assert guards.activate_human_pause("2:lead") == 20.0
    assert guards.is_human_paused("2:lead")

    clock.now += 21.0
    assert not guards.is_human_paused("2:lead")


def test_saved_contacts_registry_keeps_only_whatsapp_contacts():
    registry = SavedContactsRegistry()

    total = registry.handle_upsert(
        "fralib_user_2",
        [
            {"jid": "554199999999@s.whatsapp.net"},
            {"jid": "123@g.us"},
            {"jid": ""},
        ],
    )

    assert total == 1
    assert registry.is_saved_contact("fralib_user_2", "554199999999@s.whatsapp.net")
    assert not registry.is_saved_contact("fralib_user_2", "123@g.us")
