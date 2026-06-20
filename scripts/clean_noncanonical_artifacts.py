"""Audit or remove non-canonical FraLib workspace artifacts.

Default mode is read-only. Destructive cleanup requires:
    python scripts/clean_noncanonical_artifacts.py --apply --confirm CLEAN
"""

import argparse
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ARTIFACTS = [
    "PIPELINE_FIX_REPORT.md",
    "backend/agents/legacy_renderer_fixed.py",
    "backend/core/database_migrations.py",
    "coverage.xml",
    "frontend/design-system.css",
    "frontend/landing2.html",
    "frontend/landing_backup.html",
    "health-monitor-config.json",
    "htmlcov",
    "scripts/health-monitor.py",
    "scripts/maintenance.sh",
    "test_complete_pipeline.py",
    "test_pipeline_fix.py",
]


def _is_tracked(path: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", path],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Remove found artifacts")
    parser.add_argument("--confirm", default="", help="Required value with --apply: CLEAN")
    args = parser.parse_args()

    if args.apply and args.confirm != "CLEAN":
        print("Abortado. Use --apply --confirm CLEAN para remover artefatos.")
        return 2

    found = []
    for rel in ARTIFACTS:
        path = ROOT / rel
        if not path.exists():
            continue
        tracked = _is_tracked(rel)
        found.append((rel, tracked))
        status = "tracked" if tracked else "untracked"
        print(f"FOUND {status}: {rel}")
        if args.apply:
            if tracked:
                print(f"SKIP tracked: {rel}")
                continue
            _remove(path)
            print(f"REMOVED: {rel}")

    if not found:
        print("OK nenhum artefato nao-canonico encontrado")
    elif not args.apply:
        print("DRY-RUN use --apply --confirm CLEAN para remover os nao versionados")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
