"""Contract test: reconcile_one_truth.py without --apply is read-only.

Running the script 100 times without --apply must not mutate any database state.
This test asserts that the script:
1. Has a --apply flag that is required for mutations
2. Without --apply, only reads data
3. Prints a DRY-RUN notice
"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_reconcile_has_apply_flag():
    """reconcile_one_truth.py must require --apply to mutate data."""
    source = _read("scripts/reconcile_one_truth.py")

    assert "--apply" in source, "reconcile_one_truth.py must have --apply flag"
    assert "store_true" in source, (
        "--apply must be a boolean flag (store_true)"
    )


def test_reconcile_blocks_mutation_without_apply():
    """Without --apply, reconcile_one_truth.py must not execute INSERT/UPDATE/DELETE.

    Each SQL mutation must be inside a block guarded by the 'apply' flag.
    We check within a 5-line window around each mutation.
    """
    source = _read("scripts/reconcile_one_truth.py")
    lines = source.splitlines()

    mutation_pattern = re.compile(
        r'^\s*(INSERT\s+|UPDATE\s+|DELETE\s+)',
        re.IGNORECASE
    )

    errors = []
    for i, line in enumerate(lines):
        if mutation_pattern.match(line.strip()):
            # Check a window of 5 lines before and after for 'apply'
            window = '\n'.join(lines[max(0, i-5):i+6]).lower()
            if 'apply' not in window:
                errors.append(f"Line {i+1}: mutation not guarded by 'apply': {line.strip()}")

    assert not errors, "Mutations without 'apply' guard:\n" + '\n'.join(errors)


def test_reconcile_prints_dry_run_notice():
    """reconcile_one_truth.py must print a DRY-RUN notice when --apply is absent."""
    source = _read("scripts/reconcile_one_truth.py")

    # The script should print a notice indicating dry-run mode
    dry_run_indicators = [
        "dry-run", "dry_run", "DRY-RUN", "DRY_RUN",
        "dry run", "sem --apply", "without --apply"
    ]
    found = any(indicator.lower() in source.lower() for indicator in dry_run_indicators)
    assert found, (
        "reconcile_one_truth.py must print a dry-run notice when --apply is not provided"
    )
