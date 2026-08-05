# llm_agent_config.py — Agent model configuration and routing
"""
Agent configuration module for FraLib LLM client.
Handles agent model configs from DB, cache, and hardcoded fallbacks.
"""
from __future__ import annotations

import time as _time

from backend.agents import llm_config


# ─────────────────────────────────────────────────────────────────
# AGENT CONFIG CACHE & LOADING
# ─────────────────────────────────────────────────────────────────
def _enforce_builder_aibee_lock(agent_name: str, config: dict) -> dict:
    """Enforce Aibee lock for builder_renderer agent.

    Args:
        agent_name: Name of the agent
        config: Configuration dict

    Returns:
        Locked configuration if applicable
    """
    if not config or (agent_name or "").lower() != llm_config.BUILDER_RENDERER_AGENT:
        return config
    if llm_config.builder_non_aibee_override_enabled():
        return config
    provider = (config.get("provider") or llm_config.BUILDER_AIBEE_PROVIDER).lower()
    model_id = config.get("model_id") or ""
    openrouter_style_model = "/" in model_id
    if provider == llm_config.BUILDER_AIBEE_PROVIDER and not openrouter_style_model and llm_config.is_proxy_model(model_id):
        return config

    locked = dict(config)
    locked["provider"] = llm_config.BUILDER_AIBEE_PROVIDER
    locked["model_id"] = llm_config.BUILDER_AIBEE_MODEL_ID
    locked["fallback_provider"] = None
    locked["fallback_model_id"] = None
    print(
        "[LLM] builder_renderer provider lock: "
        f"ignorando DB {provider}/{config.get('model_id')}; "
        f"usando {llm_config.BUILDER_AIBEE_PROVIDER}/{llm_config.BUILDER_AIBEE_MODEL_ID}"
    )
    return locked


def _load_agent_configs() -> dict:
    """Carrega configs do DB. Retorna dict {agent_name: {provider, model_id, temperature, max_tokens, ...}}.

    Returns:
        Dictionary mapping agent names to their configurations
    """
    global llm_config
    # Re-import to get mutable state
    from backend.agents import llm_config as lc

    if lc.AGENT_CONFIG_CACHE and (_time.time() - lc.AGENT_CONFIG_CACHE_TS) < lc.AGENT_CONFIG_CACHE_TTL:
        return lc.AGENT_CONFIG_CACHE
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
        lc.AGENT_CONFIG_CACHE = configs
        lc.AGENT_CONFIG_CACHE_TS = _time.time()
        return configs
    except Exception as e:
        print(f"[LLM] agent_model_configs load falhou (usando hardcoded): {e}")
        return {}


def get_agent_config(agent_name: str) -> dict | None:
    """Get configuration for an agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Agent configuration dict or None
    """
    configs = _load_agent_configs()
    return configs.get(agent_name.lower())


def invalidate_agent_config_cache() -> None:
    """Invalidate the agent config cache."""
    llm_config.invalidate_agent_config_cache()