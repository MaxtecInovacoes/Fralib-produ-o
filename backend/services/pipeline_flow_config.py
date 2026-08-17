"""Runtime flags for the pipeline orchestration flow."""


import os


def env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def is_prompt_agent_flow(config: dict | None = None) -> bool:
    config = config or {}
    if config.get("_disable_prompt_agent_flow"):
        return False
    if "_prompt_agent_flow" in config:
        return bool(config.get("_prompt_agent_flow"))
    return os.getenv("FRALIB_PROMPT_AGENT_FLOW", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def skip_html_quality_gate(config: dict | None = None) -> bool:
    """Quality Gate agora roda por PADRÃO. Só pula se flag explícita."""
    config = config or {}
    return (
        env_flag("FRALIB_SKIP_HTML_QUALITY_GATE")
        or bool(config.get("_skip_html_quality_gate"))
    )


def skip_deterministic_gate(config: dict | None = None) -> bool:
    """Gate determinístico NUNCA pode ser pulado por FRALIB_SKIP_HTML_QUALITY_GATE.

    O skip flag só se aplica ao validador LLM opcional (validador.py), não às
    validações determinísticas em html_quality_gate.py (audit_generated_html,
    validate_generated_html, sanitize_builder_html_for_publication).
    """
    # Sempre retorna False - gate determinístico é mandatório
    return False


def is_builder_fast_path(config: dict | None = None) -> bool:
    config = config or {}
    if config.get("_disable_builder_fast_path"):
        return False
    return os.getenv("FRALIB_BUILDER_FAST_PATH", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
