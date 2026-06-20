"""Synchronize the installed VPS deploy hook from the versioned repo copy.

This script exists because the Git post-receive hook lives outside the working
tree, so normal deploys cannot update the installed hook by themselves.
"""

from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_SOURCE = Path("/root/fralib/scripts/post-receive")
DEFAULT_TARGET = Path("/root/repos/fralib/hooks/post-receive")
DEFAULT_BACKUP_DIR = Path("/root/fralib-hook-backups")
REQUIRED_TOKENS = (
    "verify_frontend_canonical.py",
    "frontend/llms.txt",
    "fralib-worker",
    "fralib-hermes-watchdog",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _validate_source(source: Path) -> str:
    if not source.exists():
        raise SystemExit(f"source hook not found: {source}")
    content = _read(source)
    missing = [token for token in REQUIRED_TOKENS if token not in content]
    if missing:
        raise SystemExit(f"source hook missing required tokens: {', '.join(missing)}")
    if not content.startswith("#!/bin/bash"):
        raise SystemExit("source hook must start with #!/bin/bash")
    return content


def _backup(target: Path, backup_dir: Path) -> Path | None:
    if not target.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backup_dir / f"post-receive.{stamp}"
    shutil.copy2(target, backup)
    return backup


def sync_hook(source: Path, target: Path, backup_dir: Path, apply: bool) -> int:
    source_content = _validate_source(source)
    current_content = _read(target) if target.exists() else ""
    if current_content == source_content:
        print("deploy hook already synchronized")
        return 0

    print(f"deploy hook differs: {target}")
    if not apply:
        print("dry-run only; pass --apply to synchronize")
        return 1

    backup = _backup(target, backup_dir)
    if backup:
        print(f"backup: {backup}")

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.write_text(source_content, encoding="utf-8")
    os.chmod(tmp, 0o755)
    os.replace(tmp, target)
    os.chmod(target, 0o755)
    print(f"deploy hook synchronized: {target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync versioned FraLib deploy hook on VPS")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--apply", action="store_true", help="Write the installed hook")
    args = parser.parse_args()
    return sync_hook(args.source, args.target, args.backup_dir, args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
