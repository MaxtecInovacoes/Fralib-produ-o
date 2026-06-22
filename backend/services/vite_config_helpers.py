"""
Vite Config Helpers - Funções de configuração do Vite React Renderer.

Responsabilidades:
- Getters de configuração de ambiente
- Seleção de modelos LLM
- Configuração de proxy
- Configuração de batch/attempt

Este módulo contém apenas funções puras de leitura - sem side effects.
"""
from __future__ import annotations

import os
import re
from typing import Any

# =============================================================================
# CONFIG GETTERS
# =============================================================================

PROXY_BUILDER_MODEL = os.getenv("FRALIB_PROXY_BUILDER_MODEL", "sonnet")


def _env_int(name: str, default: int) -> int:
    """Get integer config from environment."""
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _single_model_mode_enabled() -> bool:
    env = os.getenv("FRALIB_SINGLE_MODEL_ONLY", "1").strip().lower()
    return env not in {"0", "false", "no", "off"}


def _preview_fast_enabled() -> bool:
    env = os.getenv("FRALIB_VITE_PREVIEW_FAST", "").strip().lower()
    return env in {"1", "true", "yes", "on"}


def _batch_first_enabled() -> bool:
    env = os.getenv("FRALIB_VITE_BATCH_FIRST", "1").strip().lower()
    return env not in {"0", "false", "no", "off"}


def _is_namehost_base() -> bool:
    base = _proxy_base_url()
    return "proxy" in base.lower()


def _namehost_batch_mode() -> bool:
    return _batch_first_enabled() and _is_namehost_base()


def _probe_enabled() -> bool:
    env = os.getenv("FRALIB_VITE_PROBE", "1").strip().lower()
    return env not in {"0", "false", "no", "off"}


def _model_repair_attempts() -> int:
    try:
        return max(1, min(int(os.getenv("FRALIB_VITE_MODEL_REPAIR_ATTEMPTS", "3")), 3))
    except ValueError:
        return 3


def _batch_first_project_attempts() -> int:
    return max(1, min(_env_int("FRALIB_VITE_BATCH_FIRST_ATTEMPTS", 2), 2))


def _batch_generation_attempts() -> int:
    return max(1, min(_env_int("FRALIB_VITE_BATCH_ATTEMPTS", 1), 2))


def _batch_spacing_seconds() -> float:
    return max(0.5, min(_env_int("FRALIB_VITE_BATCH_SPACING_SECONDS", 3), 30))


def _transient_proxy_retry_delay_seconds(attempt: int) -> float:
    base = _env_int("FRALIB_VITE_RETRY_DELAY_SECONDS", 2)
    return min(base * (2 ** attempt), 30)


def _studio_min_source_chars() -> int:
    return max(100, _env_int("FRALIB_VITE_MIN_SOURCE_CHARS", 500))


def _studio_min_classnames() -> int:
    return max(10, _env_int("FRALIB_VITE_MIN_CLASSNAMES", 20))


def _studio_min_images() -> int:
    return max(1, _env_int("FRALIB_VITE_MIN_IMAGES", 2))


def _studio_min_components() -> int:
    return max(3, _env_int("FRALIB_VITE_MIN_COMPONENTS", 5))


# =============================================================================
# PROXY CONFIG
# =============================================================================


def _proxy_base_url() -> str:
    return (
        os.getenv("LITELLM_BASE_URL")
        or os.getenv("ANTHROPIC_BASE_URL")
        or "https://llm.seunegociofralib.site"
    ).rstrip("/")


def _proxy_api_key() -> str:
    return os.getenv("LITELLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""


def _chat_completions_url(base_url: str) -> str:
    return f"{base_url}/v1/chat/completions"


def _is_litellm_openai_chat_base(base_url: str | None = None) -> bool:
    base = base_url or _proxy_base_url()
    return "litellm" in base.lower() or "openai" in base.lower()


# =============================================================================
# MODEL SELECTION
# =============================================================================


def _model_candidates(*values: str) -> list[str]:
    """Parse comma/semicolon separated model values."""
    candidates: list[str] = []
    for value in values:
        for item in re.split(r"[,;]+", str(value or "")):
            clean = item.strip()
            if clean:
                candidates.append(clean)
    return candidates


def _normalize_model_alias(model: str) -> str | None:
    """Normalize model name aliases.

    Returns the canonical alias (haiku/sonnet/opus) for known models,
    or None for unknown models so callers can fall back.
    """
    model = (model or "").strip().lower()
    aliases = {
        "4": "opus",
        "4o": "sonnet",
        "4-mini": "haiku",
        "4-mini-high": "haiku",
        "sonnet": "sonnet",
        "haiku": "haiku",
        "opus": "opus",
        "claude": "sonnet",
        "claude-3-5": "sonnet",
        "claude-3-5-sonnet": "sonnet",
        "claude-3-5-haiku": "haiku",
        "gpt-4o": "sonnet",
        "gpt-4-mini": "haiku",
    }
    return aliases.get(model)


def _select_vite_react_models(primary_model: str, fallback_model: str) -> list[str]:
    """Select deduplicated list of models to try."""
    selected: list[str] = []
    for candidate in _model_candidates(primary_model, fallback_model):
        normalized = _normalize_model_alias(candidate)
        if normalized and normalized not in selected:
            selected.append(normalized)
    if not selected:
        selected.append(PROXY_BUILDER_MODEL)
    return selected


def _select_vite_react_models_for_run(primary_model: str, fallback_model: str) -> list[str]:
    """Select models based on current configuration mode."""
    if _single_model_mode_enabled():
        return _select_vite_react_models(primary_model or PROXY_BUILDER_MODEL, "")
    if _namehost_batch_mode():
        configured = os.getenv("FRALIB_VITE_NAMEHOST_MODELS", "").strip()
        if configured:
            return _select_vite_react_models(configured, "")
        preferred = (
            os.getenv("FRALIB_VITE_NAMEHOST_MODEL", "").strip()
            or os.getenv("FRALIB_PROXY_DEFAULT_MODEL", "").strip()
            or fallback_model
            or primary_model
        )
        light = os.getenv("FRALIB_PROXY_LIGHT_MODEL", "").strip()
        return _select_vite_react_models(preferred, light)
    return _select_vite_react_models(primary_model, fallback_model)


# =============================================================================
# ERROR HANDLING
# =============================================================================


def _batch_first_error_allows_repair(error: Exception) -> bool:
    """Check if a batch first error should trigger repair attempt."""
    lowered = str(error or "").lower()
    return not any(
        marker in lowered
        for marker in (
            "429",
            "too many requests",
            "usage_limit",
            "rate limit",
            "401 unauthorized",
            "403 forbidden",
            "invalid api key",
        )
    )


def _is_transient_proxy_error(exc: Exception) -> bool:
    """Check if an exception is a transient error that should be retried."""
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    lowered = str(exc).lower()
    transients = {
        "timeout",
        "connection",
        "network",
        "temporarily unavailable",
        "service unavailable",
    }
    return any(t in lowered for t in transients)


# =============================================================================
# UTILITIES
# =============================================================================


def _safe_probe_preview(raw: str, limit: int = 240) -> str:
    """Sanitize probe output for logging (hide secrets)."""
    preview = str(raw or "")[:limit]
    preview = re.sub(r"(?i)(bearer\s+)[a-z0-9._\-]+", r"\1***", preview)
    preview = re.sub(r"(?i)(api[_-]?key['\"]?\s*[:=]\s*['\"]?)[^'\"\s,}]+", r"\1***", preview)
    return preview


def _digits(value: str) -> str:
    """Extract only digits from a string."""
    return re.sub(r"\D", "", value or "")
