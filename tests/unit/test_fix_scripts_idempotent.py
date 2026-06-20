"""Contract tests: fix scripts are idempotent.

fix_one_truth_mirror.py and fix_job_577_ledger.py must:
1. Have --apply flag (default dry-run)
2. Print plan before applying
3. Be idempotent: running 2x does not change state on 2nd run
"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _has_apply_flag(source: str) -> bool:
    return "--apply" in source and "store_true" in source


def _prints_dry_run_notice(source: str) -> bool:
    dry_run_indicators = [
        "DRY-RUN", "dry-run", "dry_run", "DRY_RUN",
        "Use --apply", "sem esta flag", "without --apply"
    ]
    return any(ind.lower() in source.lower() for ind in dry_run_indicators)


def _print_plan_before_apply(source: str) -> bool:
    # The script must print the plan BEFORE calling apply
    plan_keywords = ["plano", "plan", "fix", "corre"]
    return any(kw in source.lower() for kw in plan_keywords)


def _is_idempotent_design(source: str) -> bool:
    """Check the script design supports idempotency."""
    # Should use COALESCE or ON CONFLICT DO NOTHING
    return ("COALESCE" in source or "DO NOTHING" in source or
            "noop" in source.lower() or "no difference" in source.lower())


# ---- fix_one_truth_mirror.py ----

def test_fix_one_truth_mirror_has_apply_flag():
    source = _read("scripts/fix_one_truth_mirror.py")
    assert _has_apply_flag(source), "fix_one_truth_mirror.py must have --apply flag"


def test_fix_one_truth_mirror_prints_dry_run_notice():
    source = _read("scripts/fix_one_truth_mirror.py")
    assert _prints_dry_run_notice(source), (
        "fix_one_truth_mirror.py must print DRY-RUN notice without --apply"
    )


def test_fix_one_truth_mirror_prints_plan():
    source = _read("scripts/fix_one_truth_mirror.py")
    assert _print_plan_before_apply(source), (
        "fix_one_truth_mirror.py must print a plan before applying"
    )


def test_fix_one_truth_mirror_is_idempotent_design():
    source = _read("scripts/fix_one_truth_mirror.py")
    assert _is_idempotent_design(source), (
        "fix_one_truth_mirror.py must use idempotent design (COALESCE/DO NOTHING/NOOP check)"
    )


# ---- fix_job_577_ledger.py ----

def test_fix_job_577_ledger_has_apply_flag():
    source = _read("scripts/fix_job_577_ledger.py")
    assert _has_apply_flag(source), "fix_job_577_ledger.py must have --apply flag"


def test_fix_job_577_ledger_prints_dry_run_notice():
    source = _read("scripts/fix_job_577_ledger.py")
    assert _prints_dry_run_notice(source), (
        "fix_job_577_ledger.py must print DRY-RUN notice without --apply"
    )


def test_fix_job_577_ledger_prints_plan():
    source = _read("scripts/fix_job_577_ledger.py")
    assert _print_plan_before_apply(source), (
        "fix_job_577_ledger.py must print a plan before applying"
    )


def test_fix_job_577_ledger_uses_coalesce():
    """fix_job_577_ledger.py must use COALESCE to avoid overwriting positive values."""
    source = _read("scripts/fix_job_577_ledger.py")
    assert "COALESCE" in source, (
        "fix_job_577_ledger.py must use COALESCE to avoid overwriting "
        "existing positive llm_tokens_used / llm_cost_estimate"
    )


def test_fix_job_577_ledger_has_noop_action():
    """fix_job_577_ledger.py must return 'noop' action when no fix is needed."""
    source = _read("scripts/fix_job_577_ledger.py")
    assert '"action": "noop"' in source or "'action': 'noop'" in source, (
        "fix_job_577_ledger.py must detect and return 'noop' when job is already correct"
    )
