"""Prepare a clean, reproducible pipeline test run.

Keeps users/config/leads by default, but removes runtime residue that can make a
controlled visual test reuse stale outputs.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
SITES_DIR = Path("/var/www/fralib/sites")
CACHE_DIRS = [
    ROOT / "checkpoints",
    ROOT / "logs" / "pipeline_trace",
    ROOT / "logs" / "builder_manifests",
    ROOT / ".tmp" / "builder-workspaces",
    ROOT / "backend" / "agents" / "jina_cache",
    ROOT / "backend" / "agents" / "unsplash_cache",
    ROOT / "backend" / "agents" / "pexels_cache",
]
CACHE_TABLES = [
    "keyword_cache",
    "leads_cache",
    "pipeline_checkpoints",
]


ALLOWED_TABLES = frozenset({
    "jobs",
    "pipeline_queue",
    "pipeline_failures",
    "pipeline_executions",
    "pipeline_state",
    "keyword_cache",
    "leads_cache",
    "pipeline_checkpoints",
    "leads",
})


def _table_exists(conn, table: str) -> bool:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' is not in the whitelist")
    return bool(conn.execute(text("select to_regclass(:t)"), {"t": table}).scalar())


def _columns(conn, table: str) -> set[str]:
    rows = conn.execute(
        text(
            """
            select column_name
            from information_schema.columns
            where table_name=:table
            """
        ),
        {"table": table},
    ).fetchall()
    return {row[0] for row in rows}


def _delete_by_tenant(conn, table: str, tenant: int) -> int:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' is not in the whitelist")
    if not _table_exists(conn, table):
        return 0
    cols = _columns(conn, table)
    if "tenant_id" in cols:
        return conn.execute(text(f"DELETE FROM {table} WHERE tenant_id = :tenant"), {"tenant": tenant}).rowcount
    if "user_id" in cols:
        return conn.execute(text(f"DELETE FROM {table} WHERE user_id = :tenant"), {"tenant": tenant}).rowcount
    return 0


def _clear_dir(path: Path) -> int:
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


def _remove_site(tenant: int, slug: str | None) -> int:
    if not slug:
        return 0
    target = (SITES_DIR / str(tenant) / slug).resolve()
    base = (SITES_DIR / str(tenant)).resolve()
    if not str(target).startswith(str(base)) or not target.exists():
        return 0
    shutil.rmtree(target)
    return 1


def reset_controlled_test(args) -> int:
    if args.confirm != "RESET_TEST":
        print("Abortado. Use --confirm RESET_TEST")
        return 2

    load_dotenv(ROOT / ".env")
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as conn:
        for table in ("jobs", "pipeline_queue", "pipeline_failures", "pipeline_executions"):
            deleted = _delete_by_tenant(conn, table, args.tenant)
            print(f"deleted {table}: {deleted}")
        if _table_exists(conn, "pipeline_state"):
            deleted = conn.execute(
                text("delete from pipeline_state where tenant_id=:tenant"),
                {"tenant": args.tenant},
            ).rowcount
            print(f"deleted pipeline_state: {deleted}")
        for table in CACHE_TABLES:
            if table not in ALLOWED_TABLES:
                raise ValueError(f"Table '{table}' is not in the whitelist")
            if _table_exists(conn, table):
                deleted = conn.execute(text(f"DELETE FROM {table}")).rowcount
                print(f"deleted {table}: {deleted}")
        if args.lead_id and _table_exists(conn, "leads"):
            cols = _columns(conn, "leads")
            ALLOWED_LEAD_COLS = frozenset({"processado", "erro_pipeline", "tentativas", "status"})
            sets = []
            if "processado" in cols:
                sets.append("processado = false")
            if "erro_pipeline" in cols:
                sets.append("erro_pipeline = NULL")
            if "tentativas" in cols:
                sets.append("tentativas = 0")
            if "status" in cols:
                sets.append("status = 'pendente'")
            if sets:
                updated = conn.execute(
                    text(f"UPDATE leads SET {', '.join(sets)} WHERE id = :lead_id AND user_id = :tenant"),
                    {"lead_id": args.lead_id, "tenant": args.tenant},
                ).rowcount
                print(f"updated lead reset: {updated}")

    for path in CACHE_DIRS:
        print(f"cleared {path}: {_clear_dir(path)}")
    print(f"removed site slug: {_remove_site(args.tenant, args.site_slug)}")
    print("OK reset-controlled-test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", default="", help="Required value: RESET_TEST")
    parser.add_argument("--tenant", type=int, default=2)
    parser.add_argument("--lead-id", default="")
    parser.add_argument("--site-slug", default="")
    return reset_controlled_test(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())

