"""Contract tests: no dual-write to legacy token tables.

These tests assert that:
1. token_tracker.py does NOT write to pipeline_token_usage (canonical: llm_budget_ledger)
2. orchestrator_service.py finally block does NOT update jobs.llm_tokens_used
   from the local accumulator (canonical: job_queue.mark_success via COALESCE from ledger)
"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_token_tracker_does_not_write_to_pipeline_token_usage():
    """salvar_tracking must NOT issue INSERT INTO pipeline_token_usage.

    Canonical LLM cost/tokens go to llm_budget_ledger (populated by llm_direct.py).
    A historical docstring reference is OK; the INSERT is what must be absent.
    """
    source = _read("backend/agents/token_tracker.py")

    # The function should exist (API compat) but be a no-op
    assert "def salvar_tracking" in source

    # Must NOT contain INSERT INTO pipeline_token_usage
    insert_pattern = re.compile(r'\bINSERT\s+INTO\s+pipeline_token_usage\b', re.IGNORECASE)
    assert not insert_pattern.search(source), (
        "salvar_tracking must not write to pipeline_token_usage; "
        "use llm_budget_ledger as canonical source"
    )


def test_orchestrator_finally_does_not_write_jobs_from_local_accumulator():
    """The orchestrator finally block must NOT update jobs.llm_tokens_used
    from the local TokenTracker accumulator.

    Canonical flow:
    - LLM calls: llm_budget_ledger (populated by llm_direct.py)
    - job completion: job_queue.mark_success() uses COALESCE from ledger
    - The local _resumo accumulator is for logging only.
    """
    sources = [
        _read("backend/endpoints/pipeline_orchestrator_service.py"),
        _read("backend/endpoints/pipeline_phase_helpers.py"),
    ]
    tracker_source = _read("backend/agents/token_tracker.py")

    assert "llm_budget_ledger" in tracker_source
    assert "job_queue.mark_success()" in tracker_source

    # Must NOT contain the UPDATE jobs pattern in the context of the token tracker
    for source in sources:
        assert "UPDATE jobs" not in source
        tracking_block_match = re.search(
            r'log_tracking\((?:_resumo|resumo)\)\s+'
            r'salvar_tracking\((?:_resumo|resumo)\).*?'
            r'(?=\n\s{0,16}except|\n\s{0,16}finally:|\n\s{0,16}def\s)',
            source,
            re.DOTALL,
        )
        if tracking_block_match:
            assert "UPDATE jobs" not in tracking_block_match.group(0)


def test_hermes_watchdog_is_in_audit_allowlist():
    """hermes_watchdog.py references pipeline_queue but is an allowed_legacy file.

    It must be listed in the allowed_files set of audit_one_truth.py.
    """
    source = _read("scripts/audit_one_truth.py")

    assert "backend/services/hermes_watchdog.py" in source, (
        "hermes_watchdog.py must be in the allowed_files set of audit_one_truth.py "
        "as it legitimately references pipeline_queue"
    )


def test_vps_validate_uses_health_not_api_version():
    """vps_validate_prod_launch.py must use /health, not /api/version."""
    source = _read("scripts/vps_validate_prod_launch.py")

    assert "/api/version" not in source, (
        "/api/version must be replaced with /health as the canonical health endpoint"
    )
    assert "/health" in source, (
        "/health must be present as the canonical health check endpoint"
    )
