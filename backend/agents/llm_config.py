# llm_config.py — LLM configuration, constants, and environment setup
"""
Configuration module for FraLib LLM client.
Contains constants, environment variables, and basic configuration.
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────
# PATH SETUP
# ─────────────────────────────────────────────────────────────────
_SERVICES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "services")
)
if _SERVICES_DIR not in sys.path:
    sys.path.insert(0, _SERVICES_DIR)
_AGENTS_DIR = os.path.abspath(os.path.dirname(__file__))
if _AGENTS_DIR not in sys.path:
    sys.path.insert(0, _AGENTS_DIR)

import pathlib as _pathlib
from backend.config import FRALIB_ROOT as _CFG_ROOT

# ─────────────────────────────────────────────────────────────────
# ENV LOADING
# ─────────────────────────────────────────────────────────────────
_env_paths = [
    str(_CFG_ROOT / ".env"),
    str(_pathlib.Path(__file__).parent.parent.parent / ".env"),
    str(_pathlib.Path(__file__).parent.parent / ".env"),
]
for _env_path in _env_paths:
    if _pathlib.Path(_env_path).exists():
        load_dotenv(_env_path, override=False)
        break
else:
    load_dotenv(override=False)

# ─────────────────────────────────────────────────────────────────
# API KEYS & ENDPOINTS
# ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.aibee.cloud")

LITELLM_API_KEY: str | None = os.getenv("LITELLM_API_KEY")
LITELLM_BASE_URL: str = os.getenv("LITELLM_BASE_URL", "https://llm.seunegociofralib.site/v1")

# ─────────────────────────────────────────────────────────────────
# MODEL MAPPINGS
# ─────────────────────────────────────────────────────────────────
try:
    from backend.core.proxy_models import (
        PROXY_BUILDER_MODEL,
        PROXY_DEFAULT_MODEL,
        PROXY_LIGHT_MODEL,
        PROXY_PROVIDER,
        is_proxy_model,
    )
except Exception:
    from backend.core.proxy_models import (  # type: ignore
        PROXY_BUILDER_MODEL,
        PROXY_DEFAULT_MODEL,
        PROXY_LIGHT_MODEL,
        PROXY_PROVIDER,
        is_proxy_model,
    )

# Agent to model size mapping (hardcoded fallback)
# v1.1-baseline-2026-06-23: sincronizado com overrides reais (auditoria gaps Sprint 0)
# - agente_nicho e agente_variacao foram trocados Haiku→Sonnet em 2026-06-22
# - arquiteto_mestre: bloco_copy.py usa cascade sonnet→haiku, nao sonnet→opus
# - builder_renderer: OpenUI cascade sonnet→opus; opus eh o FALLBACK
AGENT_MODEL_MAP: dict[str, str] = {
    "franz": "sonnet",  # Era haiku — Sonnet mantém contexto SDR muito melhor
    "bryan": "sonnet",  # Era haiku — alias legacy, ainda usado em imports
    "validador": "haiku",
    "agente_nicho": "sonnet",      # v1.1: era haiku
    "agente_variacao": "sonnet",   # v1.1: era haiku
    "curadoria": "opus",
    "arquiteto_mestre": "sonnet",  # v1.1: era opus (cascade real sonnet→haiku em bloco_copy)
    "designer_prd": "opus",
    "builder_renderer": "opus",    # OpenUI cascade sonnet→opus; opus eh fallback
}

# Provider-specific model mappings
AIBEE_MODEL_MAP: dict[str, str] = {
    "opus": PROXY_BUILDER_MODEL,
    "sonnet": PROXY_DEFAULT_MODEL,
    "haiku": PROXY_LIGHT_MODEL,
}

LITELLM_MODEL_MAP: dict[str, str] = {
    "opus": PROXY_BUILDER_MODEL,
    "sonnet": PROXY_DEFAULT_MODEL,
    "haiku": PROXY_LIGHT_MODEL,
}

# Active model map based on configuration
MODEL_MAP: dict[str, str] = LITELLM_MODEL_MAP if LITELLM_API_KEY else AIBEE_MODEL_MAP

# ─────────────────────────────────────────────────────────────────
# AGENT CONFIG CACHE
# ─────────────────────────────────────────────────────────────────
_AGENT_CONFIG_CACHE: dict = {}
_AGENT_CONFIG_CACHE_TS: float = 0.0
AGENT_CONFIG_CACHE_TTL: float = 60.0
BUILDER_RENDERER_AGENT: str = "builder_renderer"
BUILDER_AIBEE_PROVIDER: str = PROXY_PROVIDER
BUILDER_AIBEE_MODEL_ID: str = os.getenv("FRALIB_BUILDER_AIBEE_MODEL_ID", PROXY_BUILDER_MODEL)
BUILDER_NON_AIBEE_OVERRIDE_ENV: str = "FRALIB_BUILDER_ALLOW_NON_AIBEE"
BUILDER_NON_AIBEE_OVERRIDE_TOKEN: str = "ALLOW_NON_AIBEE_BUILDER_PROVIDER"
FAIL_CLOSED_FALLBACKS_ENV: str = "FRALIB_FAIL_CLOSED_FALLBACKS"

# ─────────────────────────────────────────────────────────────────
# RATE LIMITING CONFIG
# ─────────────────────────────────────────────────────────────────
TENANT_MAX_CALLS_PER_MIN: int = int(os.environ.get("TENANT_MAX_CALLS_PER_MIN", "40"))
TENANT_THROTTLE_WAIT: int = 10
CALL_SPACING_SECONDS: float = float(os.environ.get("LLM_CALL_SPACING", "1.2"))

# ─────────────────────────────────────────────────────────────────
# EXCEPTIONS
# ─────────────────────────────────────────────────────────────────
class RateLimitError(Exception):
    """Exceção quando API atinge rate limit após todas as tentativas."""

    def __init__(self, reset_seconds: int = 0):
        self.reset_seconds = reset_seconds
        if reset_seconds > 60:
            tempo = f"{reset_seconds // 60}min {reset_seconds % 60}s"
        else:
            tempo = f"{reset_seconds}s"
        super().__init__(f"Limite de uso atingido. Sera resetado em: {tempo}")


# ─────────────────────────────────────────────────────────────────
# CONFIG HELPERS
# ─────────────────────────────────────────────────────────────────
def _invalidar_agent_config_cache() -> None:
    """Chamado quando superadmin altera config de agente."""
    global _AGENT_CONFIG_CACHE, _AGENT_CONFIG_CACHE_TS
    _AGENT_CONFIG_CACHE = {}
    _AGENT_CONFIG_CACHE_TS = 0.0
    print("[LLM] Agent config cache invalidado")


def invalidate_agent_config_cache() -> None:
    """Public alias for _invalidar_agent_config_cache."""
    _invalidar_agent_config_cache()


def _builder_non_aibee_override_enabled() -> bool:
    """Check if non-Aibee builder override is enabled."""
    # Contrato atual: builder_renderer sempre passa pelo provider anthropic
    # compatível com LiteLLM FraLib. Overrides antigos para OpenRouter ficam
    # desativados para impedir fuga de custo/modelo na pipeline.
    return False


def builder_non_aibee_override_enabled() -> bool:
    """Public alias for _builder_non_aibee_override_enabled."""
    return _builder_non_aibee_override_enabled()


def _fallbacks_disabled() -> bool:
    """Check if fallbacks are disabled (fail-closed mode)."""
    env = (os.getenv(FAIL_CLOSED_FALLBACKS_ENV) or "").strip().lower()
    if env in {"1", "true", "yes", "on"}:
        return True
    return (os.getenv("FRALIB_ENV") or "").strip().lower() == "prod"


def fallbacks_disabled() -> bool:
    """Public alias for _fallbacks_disabled."""
    return _fallbacks_disabled()


def _enforce_builder_aibee_lock(agent_name: str | None, config: dict | None) -> dict:
    """Lock builder_renderer to Aibee provider/model."""
    if not config or (agent_name or "").lower() != BUILDER_RENDERER_AGENT:
        return config
    if _builder_non_aibee_override_enabled():
        return config
    provider = (config.get("provider") or BUILDER_AIBEE_PROVIDER).lower()
    model_id = config.get("model_id") or ""
    openrouter_style_model = "/" in model_id
    if provider == BUILDER_AIBEE_PROVIDER and not openrouter_style_model and is_proxy_model(model_id):
        return config

    locked = dict(config)
    locked["provider"] = BUILDER_AIBEE_PROVIDER
    locked["model_id"] = BUILDER_AIBEE_MODEL_ID
    locked["fallback_provider"] = None
    locked["fallback_model_id"] = None
    print(
        "[LLM] builder_renderer provider lock: "
        f"ignorando DB {provider}/{config.get('model_id')}; "
        f"usando {BUILDER_AIBEE_PROVIDER}/{BUILDER_AIBEE_MODEL_ID}"
    )
    return locked


def _load_agent_configs() -> dict:
    """Carrega configs do DB. Retorna dict {agent_name: {provider, model_id, temperature, max_tokens, ...}}."""
    global _AGENT_CONFIG_CACHE, _AGENT_CONFIG_CACHE_TS
    import time as _time

    now = _time.time()
    if _AGENT_CONFIG_CACHE and (now - _AGENT_CONFIG_CACHE_TS) < AGENT_CONFIG_CACHE_TTL:
        return _AGENT_CONFIG_CACHE
    try:
        from backend.core.database import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                SELECT agent_name, provider, model_id, fallback_provider, fallback_model_id,
                       temperature, top_p, max_tokens, enabled
                FROM agent_model_configs WHERE enabled = TRUE
            """)
            ).fetchall()
        configs = {}
        for r in rows:
            agent_name = r[0]
            configs[agent_name] = _enforce_builder_aibee_lock(agent_name, {
                "provider": r[1],
                "model_id": r[2],
                "fallback_provider": r[3],
                "fallback_model_id": r[4],
                "temperature": r[5],
                "top_p": r[6],
                "max_tokens": r[7],
            })
        _AGENT_CONFIG_CACHE = configs
        _AGENT_CONFIG_CACHE_TS = now
        return configs
    except Exception as e:
        print(f"[LLM] agent_model_configs load falhou (usando hardcoded): {e}")
        return {}