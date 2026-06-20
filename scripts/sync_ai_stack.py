"""Synchronize versioned LiteLLM stack files into /opt/ai-stack on the VPS."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "infra" / "ai-stack"
TARGET_DIR = Path("/opt/ai-stack")
FILES = ("docker-compose.yml", "litellm_config.yaml", "README.md", ".env.example")


def _backup_if_changed(source: Path, target: Path) -> None:
    if not target.exists() or target.read_bytes() == source.read_bytes():
        return
    backup_dir = target.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    shutil.copy2(target, backup_dir / f"{target.name}.{stamp}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync FraLib LiteLLM stack")
    parser.add_argument("--target", default=str(TARGET_DIR))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    target_dir = Path(args.target)
    planned = []
    for name in FILES:
        source = SOURCE_DIR / name
        target = target_dir / name
        if not source.exists():
            raise SystemExit(f"arquivo fonte ausente: {source}")
        changed = not target.exists() or target.read_bytes() != source.read_bytes()
        planned.append((name, changed))

    for name, changed in planned:
        print(f"{'UPDATE' if changed else 'OK'} {target_dir / name}")
    if not args.apply:
        print("DRY RUN: use --apply para sincronizar")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    for name, changed in planned:
        if not changed:
            continue
        source = SOURCE_DIR / name
        target = target_dir / name
        _backup_if_changed(source, target)
        shutil.copy2(source, target)
    print(f"sync concluido: {target_dir}")


if __name__ == "__main__":
    main()
