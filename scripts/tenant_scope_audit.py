"""Static audit for tenant scoping on SQL touching tenant-owned tables.

Focus:
- Catch obvious raw SQL that touches tenant-owned tables without owner filters.
- Keep false-positives low; this is a guardrail, not a full SQL parser.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_DIRS = [ROOT / "backend" / "endpoints", ROOT / "backend" / "core", ROOT / "backend" / "services"]

# Intentional exclusions:
# - superadmin endpoints may read cross-tenant aggregates by design.
# - metrics/alerting/health may read cross-tenant aggregates only for superadmin or internal health checks.
# - database bootstrap/migrations can define tables without tenant predicates.
# - job_queue is an internal queue manager that uses job_id after claim.
SKIP_FILES = {
    "backend/endpoints/superadmin_endpoints.py",
    "backend/endpoints/metrics_endpoints.py",
    "backend/endpoints/health_endpoints.py",
    "backend/services/alerting.py",
    "backend/core/database.py",
    "backend/core/job_queue.py",
    "backend/endpoints/tracking_endpoints.py",
}

SQL_PATTERN = re.compile(
    r"""text\(\s*(?P<quote>["']{1,3})(?P<sql>.*?)(?P=quote)\s*\)""",
    re.DOTALL | re.IGNORECASE,
)

TENANT_OWNED_TABLES = {
    "leads": ("user_id", "tenant_id"),
    "jobs": ("tenant_id",),
    "pipeline_failures": ("tenant_id", "user_id"),
    "pipeline_state": ("tenant_id",),
    "pipeline_queue": ("user_id", "tenant_id"),
    "pipeline_executions": ("tenant_id", "user_id"),
    "pipeline_run_spans": ("tenant_id",),
    "pipeline_token_usage": ("tenant_id",),
    "llm_budget_ledger": ("tenant_id",),
    "tenant_device": ("tenant_id",),
    "user_configs": ("user_id",),
}

TOUCH_TEMPLATE = r"\b(from|join|update|insert\s+into|delete\s+from)\s+(?:public\.)?{table}\b"


def iter_python_files():
    for base in TARGET_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if rel in SKIP_FILES:
                continue
            yield path


def audit_file(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    findings = []
    for match in SQL_PATTERN.finditer(text):
        sql = match.group("sql")
        touched_table = None
        owner_columns = ()
        for table, columns in TENANT_OWNED_TABLES.items():
            if re.search(TOUCH_TEMPLATE.format(table=re.escape(table)), sql, re.IGNORECASE):
                touched_table = table
                owner_columns = columns
                break

        if not touched_table:
            continue

        guard_pattern = re.compile(
            r"\b(" + "|".join(re.escape(column) for column in owner_columns) + r")\b",
            re.IGNORECASE,
        )
        if guard_pattern.search(sql):
            continue

        lineno = text.count("\n", 0, match.start()) + 1
        snippet = " ".join(sql.strip().split())
        findings.append((lineno, touched_table, snippet[:180]))
    return findings


def main() -> int:
    issues = []
    for path in iter_python_files():
        findings = audit_file(path)
        if findings:
            rel = path.relative_to(ROOT).as_posix()
            for lineno, table, snippet in findings:
                issues.append((rel, lineno, table, snippet))

    if not issues:
        print("PASS tenant-scope-audit: no unscoped SQL on tenant-owned tables found.")
        return 0

    print("FAIL tenant-scope-audit: potential unscoped SQL found.")
    for rel, lineno, table, snippet in issues:
        print(f"- {rel}:{lineno} [{table}] -> {snippet}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
