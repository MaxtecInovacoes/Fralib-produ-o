"""Manager agent — Pipeline states, constants, and helpers.

This module contains the FSM state constants, PipelineState dataclass,
and utility functions used across all pipeline step modules.
"""
import traceback
from dataclasses import dataclass, field
from typing import Optional

# Feature flag: uses Quality Gate v2 (Playwright + Vision) instead of v1 (regex)
USE_QA_V2 = True  # default; overridden by env in barrel agent.py

# FSM states
STATE_INIT = "init"
STATE_HUNTING = "hunting"
STATE_QUALIFYING = "qualifying"
STATE_DESIGNING = "designing"
STATE_BUILDING = "building"
STATE_VALIDATING = "validating"
STATE_PUBLISHING = "publishing"
STATE_OUTREACH = "outreach"
STATE_DONE = "done"
STATE_FAILED = "failed"


@dataclass
class PipelineState:
    """Central state object passed between pipeline steps."""
    tenant_id: int = 0
    run_id: str = ""
    lead_id: str = ""
    job_id: int = 0
    segmento: str = ""
    cidade: str = ""
    lead_data: dict = field(default_factory=dict)
    caio_output: Optional[dict] = None
    design_output: Optional[dict] = None
    build_output: Optional[dict] = None
    quality_score: int = 0
    deploy_url: str = ""
    deploy_path: str = ""
    current_state: str = STATE_HUNTING
    history: list[str] = field(default_factory=list)
    error: str = ""
    error_step: str = ""
    attempts: dict = field(default_factory=dict)
    estado_manual: str = ""
    paused_by: Optional[str] = None


def _transition(state: PipelineState, new_state: str) -> PipelineState:
    """Transition to a new FSM state, recording the change in history."""
    state.history.append(f"{state.current_state} → {new_state}")
    state.current_state = new_state
    return state


def _validate_required_fields(data: dict, required: list[str]) -> tuple[bool, str]:
    """Validate that required fields exist in data dict."""
    missing = [f for f in required if not data.get(f)]
    if missing:
        return False, f"campos faltando: {', '.join(missing)}"
    return True, ""


def _is_transient_llm_error(exc: Exception) -> bool:
    """Check if an exception is a transient LLM error (rate limit, overload, timeout)."""
    error_str = str(exc).lower()
    transient_markers = [
        "429", "529", "overloaded", "sobrecarregado",
        "rate limit", "too many requests", "503",
        "502", "504", "timeout", "timed out",
        "provider_error", "sem janela", "temporariamente",
    ]
    return any(marker in error_str for marker in transient_markers)


logger = __import__("logging").getLogger("manager.pipeline")


def _log_step_error(state: PipelineState, step_name: str, exc: Exception) -> None:
    """Log estruturado de erro com step, exception type, traceback e lead_id.

    Persiste no DB (pipeline_error_log) + stdout.
    Falha de persistencia nunca quebra a pipeline.
    """
    state.error_step = step_name
    logger.error(
        "PIPELINE_ERROR step=%s lead_id=%s tenant_id=%s exception=%s msg=%s",
        step_name,
        state.lead_id,
        state.tenant_id,
        type(exc).__name__,
        str(exc),
    )
    logger.debug(
        "PIPELINE_TRACEBACK step=%s lead_id=%s\n%s",
        step_name,
        state.lead_id,
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    )
    # Persist to DB (best-effort)
    try:
        from backend.core.pipeline_error_log import log_step_error as _db_log

        _db_log(
            lead_id=state.lead_id,
            tenant_id=state.tenant_id,
            step_name=step_name,
            exc=exc,
        )
    except Exception as db_err:
        logger.warning("Pipeline error DB persist failed: %s", db_err)
