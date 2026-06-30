"""Rate limiting, debounce, and anti-abuse wrappers for the WhatsApp listener.

Consolidates all timing/throttling state that was previously inline in
whatsapp_listener.py. Uses AntiAbuseGuards from whatsapp.guards internally.
"""

import threading
import time as _time_mod
from datetime import date
from typing import Callable, Dict

from whatsapp.guards import AntiAbuseGuards, SavedContactsRegistry

# ── Constants ────────────────────────────────────────────────────────────

DEBOUNCE_SECONDS = 4.0
DEFAULT_COOLDOWN_SECONDS = 30.0
DEFAULT_FLOOD_THRESHOLD = 10
DEFAULT_FLOOD_WINDOW = 60.0
DEFAULT_FLOOD_SILENCE = 300.0
DEFAULT_DAILY_LIMIT = 50
DEFAULT_HUMAN_PAUSE_SECONDS = 300.0


class RateLimiter:
    """Encapsulates all anti-abuse state and exposes simple check/set methods.

    Designed to be instantiated once per process (singleton in the listener).
    All methods are thin wrappers that delegate to AntiAbuseGuards.
    """

    def __init__(
        self,
        *,
        flood_threshold: int = DEFAULT_FLOOD_THRESHOLD,
        flood_window: float = DEFAULT_FLOOD_WINDOW,
        flood_silence: float = DEFAULT_FLOOD_SILENCE,
        default_daily_limit: int = DEFAULT_DAILY_LIMIT,
        default_cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        default_human_pause_seconds: float = DEFAULT_HUMAN_PAUSE_SECONDS,
        daily_limit_for_key: Callable[[str], int] | None = None,
        cooldown_seconds_for_key: Callable[[str], float] | None = None,
        human_pause_seconds_for_key: Callable[[str], float] | None = None,
        now_func: Callable[[], float] = _time_mod.time,
        today_func: Callable[[], date] = date.today,
    ):
        self.flood_threshold = flood_threshold
        self.flood_window = flood_window
        self.flood_silence = flood_silence
        self.default_daily_limit = default_daily_limit
        self.default_cooldown_seconds = default_cooldown_seconds
        self.default_human_pause_seconds = default_human_pause_seconds

        self._guards = AntiAbuseGuards(
            flood_threshold=flood_threshold,
            flood_window=flood_window,
            flood_silence=flood_silence,
            daily_limit_for_key=daily_limit_for_key or (lambda k: default_daily_limit),
            cooldown_seconds_for_key=cooldown_seconds_for_key or (lambda k: default_cooldown_seconds),
            human_pause_seconds_for_key=human_pause_seconds_for_key or (lambda k: default_human_pause_seconds),
            now_func=now_func,
            today_func=today_func,
        )

        # Saved contacts registry
        self.saved_contacts = SavedContactsRegistry()

        # Debounce state
        self._debounce_buffer: Dict[str, dict] = {}
        self._debounce_lock = threading.Lock()

    # ── Cooldown ─────────────────────────────────────────────────────────

    def check_cooldown(self, lead_key: str) -> bool:
        return self._guards.check_cooldown(lead_key)

    def set_cooldown(self, lead_key: str) -> None:
        self._guards.set_cooldown(lead_key)

    def cooldown_remaining(self, lead_key: str) -> float:
        return self._guards.cooldown_remaining(lead_key)

    # ── Flood ────────────────────────────────────────────────────────────

    def check_flood(self, lead_key: str) -> bool:
        return self._guards.check_flood(lead_key)

    # ── Daily Limit ──────────────────────────────────────────────────────

    def check_daily_limit(self, lead_key: str) -> bool:
        return self._guards.check_daily_limit(lead_key)

    def increment_daily(self, lead_key: str) -> None:
        self._guards.increment_daily(lead_key)

    def reset_daily_if_needed(self) -> None:
        self._guards.reset_daily_if_needed()

    # ── Human Pause ──────────────────────────────────────────────────────

    def activate_human_pause(self, lead_key: str) -> float:
        return self._guards.activate_human_pause(lead_key)

    def is_human_paused(self, lead_key: str) -> bool:
        return self._guards.is_human_paused(lead_key)

    @property
    def human_pause(self) -> dict:
        return self._guards.human_pause

    # ── Humanized Delay ──────────────────────────────────────────────────

    def humanized_delay(self, reply_text: str) -> float:
        """Compute a humanized typing delay based on reply length.

        Currently returns a fixed 2.0s (debug mode). Production formula TBD.
        """
        return 2.0

    # ── Saved Contacts ───────────────────────────────────────────────────

    def handle_contacts_upsert(self, tenant_id: str, contacts: list) -> int:
        return self.saved_contacts.handle_upsert(tenant_id, contacts)

    def is_saved_contact(self, tenant_id: str, jid: str) -> bool:
        return self.saved_contacts.is_saved_contact(tenant_id, jid)

    # ── Flood tracker access (for logging) ───────────────────────────────

    @property
    def flood_tracker(self) -> dict:
        return self._guards.flood_tracker

    # ── Compatibility (can_send) ──────────────────────────────────────────

    def can_send(self, lead_key: str) -> bool:
        """Verifica se pode enviar mensagem para o lead.

        Combina: cooldown, flood, daily_limit, human_pause.
        Retorna True se PODE enviar.
        """
        if not self.check_cooldown(lead_key):
            return False
        if not self.check_flood(lead_key):
            return False
        if not self.check_daily_limit(lead_key):
            return False
        if self.is_human_paused(lead_key):
            return False
        return True

    def get_remaining_cooldown(self, lead_key: str) -> float:
        """Retorna segundos restantes de cooldown (0 se pode enviar)."""
        return self.cooldown_remaining(lead_key)
