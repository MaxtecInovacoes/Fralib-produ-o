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
STATE_NICHE_BRIEFING = "niche_briefing"
STATE_DIRECTING = "directing"
STATE_VARIATING = "variating"
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
    niche_brief: Optional[dict] = None
    creative_direction: Optional[dict] = None
    variation_blueprint: Optional[dict] = None
    designer_prd: Optional[dict] = None
    visual_dna: Optional[dict] = None
    media_plan: list[dict] = field(default_factory=list)
    openui_payload: Optional[dict] = None
    visual_custody: list[dict] = field(default_factory=list)
    visual_fingerprint: Optional[dict] = None
    design_output: Optional[dict] = None
    build_output: Optional[dict] = None
    seo_intel: Optional[dict] = None  # Jina/Playwright intel — ISOLATED from lead_data
    jina_insights: str = ""  # Formatted Jina text — ISOLATED slot (read-only downstream)
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
    forcar_renovacao: bool = False


def _transition(state: PipelineState, new_state: str) -> PipelineState:
    """Transition to a new FSM state, recording the change in history."""
    state.history.append(f"{state.current_state} → {new_state}")
    state.current_state = new_state
    return state


def _record_visual_custody(
    state: PipelineState,
    stage: str,
    *,
    received_decisions: Optional[dict] = None,
    preserved_decisions: Optional[dict] = None,
    changed_decisions: Optional[dict] = None,
    lost_decisions: Optional[dict] = None,
    notes: Optional[list[str]] = None,
) -> None:
    """Append a visual custody record for auditability across the pipeline."""
    state.visual_custody.append(
        {
            "stage": stage,
            "received_decisions": received_decisions or {},
            "preserved_decisions": preserved_decisions or {},
            "changed_decisions": changed_decisions or {},
            "lost_decisions": lost_decisions or {},
            "notes": notes or [],
        }
    )


def _record_agent_handoff(
    state: PipelineState,
    stage: str,
    *,
    received: Optional[dict] = None,
    produced: Optional[dict] = None,
    preserved: Optional[dict] = None,
    changed: Optional[dict] = None,
    lost: Optional[dict] = None,
    notes: Optional[list[str]] = None,
) -> None:
    """Persist a readable handoff file showing what one agent passed forward."""
    try:
        from backend.agents.artifact_store import write_handoff_artifact

        write_handoff_artifact(
            run_id=state.run_id,
            lead_id=state.lead_id,
            lead_name=(state.lead_data or {}).get("nome", ""),
            stage=stage,
            sequence=_HANDOFF_SEQUENCE.get(stage, len(state.visual_custody) + 1),
            received=received or {},
            produced=produced or {},
            preserved=preserved or {},
            changed=changed or {},
            lost=lost or {},
            notes=notes or [],
            metadata={"tenant_id": state.tenant_id, "job_id": state.job_id},
        )
    except Exception as exc:
        logger.warning("Agent handoff artifact failed stage=%s lead_id=%s: %s", stage, state.lead_id, exc)


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


_HANDOFF_SEQUENCE = {
    "hunter": 1,
    "caio": 2,
    "niche_brief": 3,
    "creative_direction": 4,
    "variation_blueprint": 5,
    "designer_prd": 6,
    "builder_openui": 7,
    "quality_gate": 8,
    "deploy": 9,
    "franz": 10,
}


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
