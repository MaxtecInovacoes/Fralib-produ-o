"""Guards operacionais do atendimento WhatsApp/SDR."""

from datetime import date
import time
from typing import Callable


class AntiAbuseGuards:
    """Estado em memoria para flood, cooldown, limite diario e pausa humana."""

    def __init__(
        self,
        *,
        flood_threshold: int,
        flood_window: float,
        flood_silence: float,
        daily_limit_for_key: Callable[[str], int],
        cooldown_seconds_for_key: Callable[[str], float],
        human_pause_seconds_for_key: Callable[[str], float],
        now_func: Callable[[], float] = time.time,
        today_func: Callable[[], date] = date.today,
    ):
        self.flood_threshold = flood_threshold
        self.flood_window = flood_window
        self.flood_silence = flood_silence
        self.daily_limit_for_key = daily_limit_for_key
        self.cooldown_seconds_for_key = cooldown_seconds_for_key
        self.human_pause_seconds_for_key = human_pause_seconds_for_key
        self.now_func = now_func
        self.today_func = today_func
        self.flood_tracker: dict[str, list[float]] = {}
        self.flood_silenced: dict[str, float] = {}
        self.daily_count: dict[str, int] = {}
        self.daily_date = ""
        self.lead_last_reply: dict[str, float] = {}
        self.human_pause: dict[str, float] = {}

    def reset_daily_if_needed(self) -> None:
        today = self.today_func().isoformat()
        if self.daily_date != today:
            self.daily_count = {}
            self.daily_date = today

    def check_flood(self, lead_key: str) -> bool:
        now = self.now_func()
        if lead_key in self.flood_silenced:
            if now - self.flood_silenced[lead_key] < self.flood_silence:
                return True
            del self.flood_silenced[lead_key]

        self.flood_tracker.setdefault(lead_key, []).append(now)
        self.flood_tracker[lead_key] = [
            item for item in self.flood_tracker[lead_key]
            if now - item < self.flood_window
        ]

        if len(self.flood_tracker[lead_key]) > self.flood_threshold:
            self.flood_silenced[lead_key] = now
            return True
        return False

    def check_daily_limit(self, lead_key: str) -> bool:
        self.reset_daily_if_needed()
        return self.daily_count.get(lead_key, 0) >= self.daily_limit_for_key(lead_key)

    def increment_daily(self, lead_key: str) -> None:
        self.reset_daily_if_needed()
        self.daily_count[lead_key] = self.daily_count.get(lead_key, 0) + 1

    def check_cooldown(self, lead_key: str) -> bool:
        last = self.lead_last_reply.get(lead_key, 0)
        return (self.now_func() - last) < self.cooldown_seconds_for_key(lead_key)

    def cooldown_remaining(self, lead_key: str) -> float:
        last = self.lead_last_reply.get(lead_key, 0)
        remaining = self.cooldown_seconds_for_key(lead_key) - (self.now_func() - last)
        return max(0.0, remaining)

    def set_cooldown(self, lead_key: str) -> None:
        self.lead_last_reply[lead_key] = self.now_func()

    def activate_human_pause(self, lead_key: str) -> float:
        self.human_pause[lead_key] = self.now_func()
        return self.human_pause_seconds_for_key(lead_key)

    def is_human_paused(self, lead_key: str) -> bool:
        if lead_key not in self.human_pause:
            return False
        elapsed = self.now_func() - self.human_pause[lead_key]
        if elapsed >= self.human_pause_seconds_for_key(lead_key):
            del self.human_pause[lead_key]
            return False
        return True


class SavedContactsRegistry:
    """Cache em memoria dos contatos salvos por tenant."""

    def __init__(self):
        self.contacts_by_tenant: dict[str, set[str]] = {}

    def handle_upsert(self, tenant_id: str, contacts: list[dict]) -> int:
        bucket = self.contacts_by_tenant.setdefault(tenant_id, set())
        for contact in contacts:
            jid = contact.get("jid", "")
            if jid and "@s.whatsapp.net" in jid:
                bucket.add(jid)
        return len(bucket)

    def is_saved_contact(self, tenant_id: str, jid: str) -> bool:
        return jid in self.contacts_by_tenant.get(tenant_id, set())
