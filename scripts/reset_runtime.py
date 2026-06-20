"""Reset operacional do FraLib.

Mantem usuarios/auth/configuracoes e limpa somente dados de runtime/teste.
"""

import argparse
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_TABLES = [
    "site_visitas",
    "interacoes",
    "pipeline_failures",
    "pipeline_executions",
    "pipeline_queue",
    "jobs",
    "pipeline_state",
    "leads",
]
RUNTIME_DIRS = [
    ROOT / "checkpoints",
    ROOT / "logs" / "pipeline_trace",
]
SITES_DIR = Path("/var/www/fralib/sites")


def _safe_clear_dir(path: Path) -> int:
    path.mkdir(parents=True, exist_ok=True)
    count = 0
    for child in list(path.iterdir()):
        if child.is_file() or child.is_symlink():
            child.unlink()
            count += 1
        elif child.is_dir():
            shutil.rmtree(child)
            count += 1
    return count


def _clear_sites() -> int:
    SITES_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    base = SITES_DIR.resolve()
    for child in list(SITES_DIR.iterdir()):
        resolved = child.resolve()
        if child.is_dir() and child.name.isdigit() and str(resolved).startswith(str(base)):
            shutil.rmtree(child)
            count += 1
    return count


def reset_runtime(args) -> int:
    if args.confirm != "RESET":
        print("Abortado. Use: python pipeline.py reset-runtime --confirm RESET")
        return 2

    load_dotenv(ROOT / ".env")
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as conn:
        for table in RUNTIME_TABLES:
            exists = conn.execute(text("select to_regclass(:table)"), {"table": table}).scalar()
            if not exists:
                continue
            deleted = conn.execute(text("delete from " + table)).rowcount
            print(f"deleted {table}: {deleted}")

    for path in RUNTIME_DIRS:
        print(f"cleared {path}: {_safe_clear_dir(path)}")

    if not args.keep_sites:
        print(f"removed site tenant dirs: {_clear_sites()}")

    print("OK reset-runtime")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", default="", help="Required value: RESET")
    parser.add_argument("--keep-sites", action="store_true", help="Do not remove /var/www/fralib/sites/{tenant}")
    return reset_runtime(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
