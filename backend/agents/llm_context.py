# llm_context.py — LLM context, user tracking, and rate limiting
"""
Context management module for FraLib LLM client.
Handles thread-local context, user tracking, tenant rate limiting, and BYOK key resolution.
"""
from __future__ import annotations

import os
import threading as _threading
import time as _time
from collections import defaultdict as _defaultdict

from backend.agents import llm_config


# ─────────────────────────────────────────────────────────────────
# THREAD-LOCAL CONTEXT
# ─────────────────────────────────────────────────────────────────
_current_user_id = None
_LLM_CONTEXT = _threading.local()


def set_current_user_id(uid: str | None) -> None:
    """Set the current user ID for LLM tracking.

    Args:
        uid: User ID to set
    """
    global _current_user_id
    _current_user_id = uid
    _LLM_CONTEXT.tenant_id = uid


def set_llm_context(
    user_id: str | None = None,
    run_id: str | None = None,
    job_id: str | None = None,
    phase: str | None = None,
) -> None:
    """Define contexto auditavel da chamada LLM no thread atual.

    Args:
        user_id: Tenant/lead ID
        run_id: Pipeline run ID
        job_id: Pipeline job ID
        phase: Current pipeline phase
    """
    global _current_user_id
    _current_user_id = user_id
    _LLM_CONTEXT.tenant_id = user_id
    _LLM_CONTEXT.run_id = run_id
    _LLM_CONTEXT.job_id = job_id
    _LLM_CONTEXT.phase = phase


def clear_llm_context() -> None:
    """Clear all LLM context values."""
    set_llm_context(None, None, None, None)


def _llm_context_value(name: str, default=None):
    """Get a value from the thread-local LLM context.

    Args:
        name: Attribute name to retrieve
        default: Default value if not found

    Returns:
        The context value or default
    """
    return getattr(_LLM_CONTEXT, name, default)


def get_current_user_id() -> str | None:
    """Get the current user ID."""
    return _llm_context_value("tenant_id") or _current_user_id


# ─────────────────────────────────────────────────────────────────
# TENANT RATE LIMITING — sliding window per tenant
# ─────────────────────────────────────────────────────────────────
_TENANT_CALLS_LOCK = _threading.Lock()
_TENANT_CALLS: dict = _defaultdict(list)


def _tenant_rate_check(user_id: str) -> tuple[bool, int, int]:
    """Check if tenant is within rate limits.

    Args:
        user_id: Tenant/user ID

    Returns:
        Tuple of (allowed, wait_seconds, call_count)
    """
    if not user_id:
        return (True, 0, 0)
    now = _time.time()
    window = 60.0
    with _TENANT_CALLS_LOCK:
        _TENANT_CALLS[user_id] = [t for t in _TENANT_CALLS[user_id] if now - t < window]
        count = len(_TENANT_CALLS[user_id])
        if count >= llm_config.TENANT_MAX_CALLS_PER_MIN:
            oldest = _TENANT_CALLS[user_id][0]
            wait = int(window - (now - oldest)) + 1
            return (False, wait, count)
        _TENANT_CALLS[user_id].append(now)
        return (True, 0, count + 1)


def _tenant_rate_alert(user_id: str, wait_seconds: int, calls_count: int) -> None:
    """Send alert when tenant is rate limited.

    Args:
        user_id: Tenant/user ID
        wait_seconds: Seconds to wait
        calls_count: Number of calls made
    """
    print(
        f"[RATE-LIMIT] Tenant {user_id} throttled: {calls_count} calls/min (max={llm_config.TENANT_MAX_CALLS_PER_MIN}). Aguardando {wait_seconds}s"
    )
    try:
        import ia_manager as _ia

        _ia.raise_alert(
            "rate_limit",
            None,
            f"Tenant throttled: {calls_count} chamadas/min excede limite de {llm_config.TENANT_MAX_CALLS_PER_MIN}. Pipeline aguardou {wait_seconds}s.",
            lead_id=None,
            user_id=user_id,
        )
    except Exception:
        pass


def enforce_tenant_rate_limit(user_id: str | None) -> None:
    """Enforce tenant rate limit, sleeping if necessary.

    Args:
        user_id: Tenant/user ID to check
    """
    if user_id:
        allowed, wait, count = _tenant_rate_check(user_id)
        if not allowed:
            _tenant_rate_alert(user_id, wait, count)
            _time.sleep(min(wait, llm_config.TENANT_THROTTLE_WAIT))
            allowed2, wait2, _ = _tenant_rate_check(user_id)
            if not allowed2:
                _time.sleep(wait2)


# ─────────────────────────────────────────────────────────────────
# CALL SPACING — minimum 1.2s between calls per process
# ─────────────────────────────────────────────────────────────────
_LAST_CALL_TIME = 0.0
_CALL_SPACING_LOCK = _threading.Lock()


def _enforce_call_spacing() -> None:
    """Enforce minimum spacing between LLM calls in the same process."""
    global _LAST_CALL_TIME
    with _CALL_SPACING_LOCK:
        now = _time.time()
        elapsed = now - _LAST_CALL_TIME
        if elapsed < llm_config.CALL_SPACING_SECONDS:
            _time.sleep(llm_config.CALL_SPACING_SECONDS - elapsed)
        _LAST_CALL_TIME = _time.time()


# ─────────────────────────────────────────────────────────────────
# BYOK (BRING YOUR OWN KEY) — legacy key lookup
# ─────────────────────────────────────────────────────────────────
_byok_cache: dict = {}


def invalidar_byok_cache(uid: str | None = None) -> None:
    """Invalidate the BYOK cache.

    Args:
        uid: Specific user ID to invalidate, or None to clear all
    """
    global _byok_cache
    if uid is None:
        _byok_cache = {}
    else:
        _byok_cache.pop(uid, None)


def _get_byok_key() -> str | None:
    """Get BYOK key for current tenant if configured.

    Returns:
        Decrypted API key or None if not available
    """
    if os.getenv("FRALIB_ENABLE_BYOK", "0") != "1":
        return None
    uid = _llm_context_value("tenant_id") or _current_user_id
    if not uid:
        return None
    if uid in _byok_cache:
        return _byok_cache[uid]
    try:
        from backend.core.database import engine
        from sqlalchemy import text
        from utils.secrets_crypto import decriptar

        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT plano, anthropic_key_encrypted FROM users WHERE id=:id"),
                {"id": uid},
            ).fetchone()
        if row and (row[0] or "").lower() == "pro" and row[1]:
            key = decriptar(row[1])
            _byok_cache[uid] = key or None
            return _byok_cache[uid]
        _byok_cache[uid] = None
    except Exception as e:
        print(f"[llm_direct] lookup de chave legada falhou para user {uid}: {e}")
    return None


# ─────────────────────────────────────────────────────────────────
# API KEY RESOLUTION
# ─────────────────────────────────────────────────────────────────
def _resolve_anthropic(agent_name: str | None = None) -> tuple[str, str, int | None]:
    """Resolve Anthropic API key and base URL.

    Priority:
    1. LiteLLM if configured
    2. BYOK key for Pro users
    3. ia_manager key rotation
    4. Fallback to env ANTHROPIC_API_KEY

    Args:
        agent_name: Agent name for logging

    Returns:
        Tuple of (api_key, base_url, key_id_or_None)
    """
    if llm_config.LITELLM_API_KEY:
        return (llm_config.LITELLM_API_KEY, llm_config.LITELLM_BASE_URL, 'litellm-vps')

    byok = _get_byok_key()
    if byok:
        return (byok, llm_config.ANTHROPIC_BASE_URL, None)
    try:
        import ia_manager

        picked = ia_manager.pick_key("anthropic")
        if picked:
            return picked
    except Exception as e:
        print(f"[llm_direct] ia_manager falhou, usando .env: {e}")
    return (llm_config.ANTHROPIC_API_KEY, llm_config.ANTHROPIC_BASE_URL, None)


def _get_active_api_key() -> str:
    """Get the active API key (convenience function)."""
    return _resolve_anthropic()[0]
