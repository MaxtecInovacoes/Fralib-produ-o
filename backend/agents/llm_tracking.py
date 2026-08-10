# llm_tracking.py — LLM usage tracking and budget registration
"""
Usage tracking module for FraLib LLM client.
Handles token counting, cost calculation, and budget ledger recording.
"""
from __future__ import annotations



# ─────────────────────────────────────────────────────────────────
# USAGE TRACKING — saves to llm_usage table
# ─────────────────────────────────────────────────────────────────
def _salvar_uso_llm(
    modelo: str,
    input_tokens: int,
    output_tokens: int,
    agente: str | None = None,
) -> None:
    """Salva uso de LLM na tabela llm_usage.

    Args:
        modelo: Model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        agente: Agent name (optional)
    """
    try:
        from backend.core.database import engine
        from sqlalchemy import text
        try:
            from agents.token_tracker import get_tracker
        except Exception:
            from token_tracker import get_tracker

        tracker = get_tracker()

        # Get tenant context
        tenant_id = _get_tenant_context(tracker)

        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO llm_usage (modelo, input_tokens, output_tokens, agente, user_id) VALUES (:m, :i, :o, :a, :u)"
                ),
                {
                    "m": modelo,
                    "i": input_tokens,
                    "o": output_tokens,
                    "a": agente,
                    "u": tenant_id,
                },
            )
            conn.commit()
    except Exception as e:
        print(f"[LLM Usage] Erro ao salvar: {e}")


def _registrar_llm_budget(
    modelo: str,
    input_tokens: int,
    output_tokens: int,
    cache_read: int = 0,
    cache_created: int = 0,
    agente: str | None = None,
    provider: str = "anthropic",
    latency_ms: int | None = None,
) -> None:
    """Registra custo por chamada LLM em ledger auditavel por tenant/run.

    Args:
        modelo: Model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cache_read: Cached read tokens
        cache_created: Cached created tokens
        agente: Agent name
        provider: Provider name
        latency_ms: Request latency in milliseconds
    """
    try:
        from backend.core.database import engine
        from sqlalchemy import text
        try:
            from agents.token_tracker import _calcular_custo, get_tracker
        except Exception:
            from token_tracker import _calcular_custo, get_tracker

        usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read": cache_read,
            "cache_creation": cache_created,
        }
        custo = _calcular_custo(modelo, usage)
        tracker = get_tracker()

        # Get context from thread-local or tracker
        tenant_id = _get_tenant_context(tracker)
        run_id = _get_run_context(tracker)
        job_id = _get_job_context(tracker)

        # job_id column is INTEGER — coerce or NULL
        if job_id is not None:
            try:
                job_id = int(job_id)
            except (ValueError, TypeError):
                job_id = None

        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO llm_budget_ledger
                        (tenant_id, job_id, run_id, phase, agent, provider, model,
                         input_tokens, output_tokens, cache_read_tokens,
                         cache_created_tokens, cost_usd, latency_ms, status)
                    VALUES
                        (:tenant_id, :job_id, :run_id, :phase, :agent, :provider, :model,
                         :input_tokens, :output_tokens, :cache_read_tokens,
                         :cache_created_tokens, :cost_usd, :latency_ms, 'success')
                """),
                {
                    "tenant_id": tenant_id,
                    "job_id": job_id,
                    "run_id": run_id,
                    "phase": _llm_context_value("phase"),
                    "agent": agente or "unknown",
                    "provider": provider or "anthropic",
                    "model": modelo,
                    "input_tokens": input_tokens or 0,
                    "output_tokens": output_tokens or 0,
                    "cache_read_tokens": cache_read or 0,
                    "cache_created_tokens": cache_created or 0,
                    "cost_usd": round(custo, 6),
                    "latency_ms": latency_ms,
                },
            )
            conn.commit()
    except Exception as e:
        print(f"[LLM Budget] Erro ao registrar ledger: {e}")


# ─────────────────────────────────────────────────────────────────
# CONTEXT ACCESSORS — used by tracking functions
# ─────────────────────────────────────────────────────────────────
_LLM_CONTEXT = None
_CURRENT_USER_ID = None


def _init_llm_context():
    """Initialize the LLM context module. Called from llm_context.py."""
    global _LLM_CONTEXT
    try:
        from backend.agents import llm_context
        _LLM_CONTEXT = llm_context
    except Exception:
        import threading
        _LLM_CONTEXT = threading.local()


def _get_tenant_context(tracker=None):
    """Get current tenant ID from context or tracker."""
    tenant_id = None
    if _LLM_CONTEXT:
        tenant_id = getattr(_LLM_CONTEXT, '_llm_context_value', lambda n, d=None: d)("tenant_id")
    if not tenant_id and tracker:
        tenant_id = getattr(tracker, "tenant_id", None)
    if not tenant_id:
        tenant_id = _get_current_user_id()
    return tenant_id


def _get_run_context(tracker=None):
    """Get current run ID from context or tracker."""
    run_id = None
    if _LLM_CONTEXT:
        run_id = getattr(_LLM_CONTEXT, '_llm_context_value', lambda n, d=None: d)("run_id")
    if not run_id and tracker:
        run_id = getattr(tracker, "run_id", None)
    return run_id


def _get_job_context(tracker=None):
    """Get current job ID from context or tracker."""
    job_id = None
    if _LLM_CONTEXT:
        job_id = getattr(_LLM_CONTEXT, '_llm_context_value', lambda n, d=None: d)("job_id")
    if not job_id and tracker:
        job_id = getattr(tracker, "job_id", None)
    return job_id


def _llm_context_value(name: str, default=None):
    """Get a value from LLM context."""
    if _LLM_CONTEXT:
        return getattr(_LLM_CONTEXT, '_llm_context_value', lambda n, d=None: d)(name, default)
    return default


def _get_current_user_id():
    """Get the current user ID."""
    if _LLM_CONTEXT:
        return getattr(_LLM_CONTEXT, '_current_user_id', None)
    return _CURRENT_USER_ID


def set_tracking_context(user_id=None, run_id=None, job_id=None, phase=None):
    """Set tracking context values. Bridge function."""
    if _LLM_CONTEXT and hasattr(_LLM_CONTEXT, 'set_llm_context'):
        _LLM_CONTEXT.set_llm_context(user_id, run_id, job_id, phase)


# ─────────────────────────────────────────────────────────────────
# TOKEN TRACKER INTEGRATION
# ─────────────────────────────────────────────────────────────────
def register_with_tracker(
    tracker,
    agente: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read: int = 0,
    cache_created: int = 0,
) -> None:
    """Register usage with the token tracker if available.

    Args:
        tracker: Token tracker instance
        agente: Agent name
        model: Model identifier
        input_tokens: Input token count
        output_tokens: Output token count
        cache_read: Cached read tokens
        cache_created: Cached created tokens
    """
    try:
        if tracker:
            usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
            if cache_read or cache_created:
                usage["cache_read_input_tokens"] = cache_read
                usage["cache_creation_input_tokens"] = cache_created
            tracker.registrar(
                agente=agente or "unknown",
                model=model,
                usage=usage,
            )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────
# LEGACY FUNCTION NAMES — for backward compatibility
# ─────────────────────────────────────────────────────────────────
salvar_uso_llm = _salvar_uso_llm  # Alias for public API
_registrar_llm_budget = _registrar_llm_budget  # Alias for internal use
