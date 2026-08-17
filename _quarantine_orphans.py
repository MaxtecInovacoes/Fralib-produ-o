"""Fase 1 — Quarantine orphan .py files into _quarantine_legacy/.
Respects guardrail whitelist (services/, core/, schemas/, agents/, endpoints/).
Backup strategy: move (not delete), .bak/.tmp excluded, preserve __pycache__ untouched.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUARANTINE = ROOT / "_quarantine_legacy"
REPORT = ROOT / "critical_core_report.json"

# Guardrail: never quarantine these directories (dynamic loading / runtime).
WHITELIST_PREFIXES = (
    "backend/agents/",
    "backend/services/",
    "backend/core/",
    "backend/schemas/",
    "backend/endpoints/",
    "backend/utils/",
    "backend/scripts/",
)

# Never quarantine these root-level directories or files.
SKIP_ROOTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "_quarantine_legacy",
    "node_modules",
    "openui-service-wandb",  # separate service
    "alembic",               # migrations — never touch
    "tests",
    "scripts",
    "docs",
    "frontend",
    "audit_codebase.py",
    "auto_fix_mechanical.py",
    "map_critical_core.py",
    "critical_core_report.json",
    "critical_core_report.md",
}


def _should_skip(rel: str) -> bool:
    top = rel.split("/")[0] if "/" in rel else rel
    if top in SKIP_ROOTS:
        return True
    for prefix in WHITELIST_PREFIXES:
        if rel.startswith(prefix):
            return True
    return False


def main() -> None:
    with REPORT.open(encoding="utf-8") as fh:
        report = json.load(fh)

    orphans = report.get("orphaned_files", [])
    moved: list[str] = []
    skipped_guardrail: list[str] = []
    skipped_dot: list[str] = []
    skipped_bak: list[str] = []

    QUARANTINE.mkdir(exist_ok=True)

    for rel in orphans:
        # quarantine script itself from moving
        if rel == "map_critical_core.py":
            continue

        src = ROOT / rel
        if not src.exists():
            skipped_dot.append(rel)
            continue

        # skip already-handled
        if ".bak" in rel.lower() or ".tmp" in rel.lower() or ".old" in rel.lower():
            skipped_bak.append(rel)
            continue

        # guardrail check
        if _should_skip(rel):
            skipped_guardrail.append(rel)
            continue

        # compute destination, preserving folder structure inside quarantine
        dest = QUARANTINE / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        moved.append(rel)

    # summary
    print(f"MOVED     : {len(moved)}")
    print(f"GUARDRAIL : {len(skipped_guardrail)} (protected)")
    print(f"BAK/TMP   : {len(skipped_bak)}")
    print(f"NOT_FOUND : {len(skipped_dot)}")
    print(f"QUARANTINE: {QUARANTINE}")
    if moved:
        print("\nFirst 20 moved:")
        for p in moved[:20]:
            print(f"  {p}")
    if skipped_guardrail:
        print("\nFirst 20 guardrail-protected:")
        for p in skipped_guardrail[:20]:
            print(f"  {p}")

    # persist counts for halt-condition report
    import json as _json
    summary = {
        "phase": "FASE_1_ORPHAN_PURGE",
        "moved_count": len(moved),
        "guardrail_protected_count": len(skipped_guardrail),
        "bak_tmp_skipped": len(skipped_bak),
        "not_found": len(skipped_dot),
        "quarantine_dir": str(QUARANTINE),
    }
    (ROOT / "_quarantine_manifest.json").write_text(
        _json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nManifest written to _quarantine_manifest.json")


if __name__ == "__main__":
    main()
