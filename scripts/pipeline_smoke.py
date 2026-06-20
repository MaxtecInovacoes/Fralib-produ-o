"""Pipeline smoke test.

Dry-run mode checks runtime health without calling LLM providers, deploy, or WhatsApp.
"""

import argparse
import importlib
import json
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
for rel in ("backend", "backend/core", "backend/agents", "backend/endpoints", "backend/services", "backend/utils"):
    sys.path.insert(0, str(ROOT / rel))

load_dotenv(ROOT / ".env")
load_dotenv(BACKEND / ".env")

RESULTS = []
INITIAL_ENV = {
    key: os.getenv(key)
    for key in (
        "DATABASE_URL",
        "ANTHROPIC_API_KEY",
        "JINA_API_KEY",
        "JWT_SECRET_KEY",
        "FRALIB_SMOKE_STRICT_PORTS",
    )
}


@contextmanager
def step(name):
    start = time.perf_counter()
    status = "pass"
    detail = ""
    try:
        yield lambda d: None
    except Exception as exc:
        status = "fail"
        detail = f"{type(exc).__name__}: {exc}"
    finally:
        elapsed = time.perf_counter() - start
        RESULTS.append({"step": name, "status": status, "seconds": round(elapsed, 3), "detail": detail})
        marker = "PASS" if status == "pass" else "FAIL"
        print(f"[{marker}] {name} {elapsed:.2f}s {detail}")


def require_env():
    required = ("DATABASE_URL", "ANTHROPIC_API_KEY", "JINA_API_KEY", "JWT_SECRET_KEY")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError("missing env: " + ", ".join(missing))


def check_imports():
    modules = (
        "agents.caio",
        "agents.keyword_research",
        "agents.arquiteto_mestre",
        "agents.bloco_estrutura",
        "agents.bloco_copy",
        "services.builder_worker",
        "agents.validador",
        "endpoints.pipeline_endpoints",
    )
    for mod in modules:
        importlib.import_module(mod)


def check_db(fix_locks=False):
    initial_db_url = INITIAL_ENV.get("DATABASE_URL")
    if initial_db_url:
        os.environ["DATABASE_URL"] = initial_db_url
    sys.modules.pop("database", None)
    sys.modules.pop("core.database", None)
    from database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        try:
            db.execute(text("SELECT 1")).scalar()
        except Exception:
            if os.name == "nt" and os.getenv("FRALIB_SMOKE_STRICT_DB", "0") != "1":
                print("  warning: optional local database skipped on Windows dev")
                return
            raise
        if (os.getenv("DATABASE_URL") or "").startswith("sqlite"):
            print("  sqlite local DB ok; stale job SQL skipped")
            return
        if fix_locks:
            from core import job_queue

            reset = job_queue.reap_dead_workers(db, stale_minutes=5, reason="pipeline_smoke_fix")
            if reset:
                print("  stale jobs reset:", reset)
        stale = db.execute(
            text("""
                SELECT id, tenant_id, last_phase
                FROM public.jobs
                WHERE status = 'running'
                  AND COALESCE(worker_heartbeat, iniciado_em, criado_em)
                      < NOW() - interval '5 minutes'
            """)
        ).fetchall()
        if stale:
            raise RuntimeError(f"stale running jobs: {[row[0] for row in stale]}")
    finally:
        db.close()


def check_caio():
    from agents.caio import _calcular_score, verificar_se_e_rede

    score, _ = _calcular_score({"rating": 5, "reviews": 500, "possui_site": False, "fotos": 8})
    if score < 90:
        raise RuntimeError(f"unexpected hot lead score: {score}")
    if not verificar_se_e_rede("Smart Fit Academia"):
        raise RuntimeError("known chain detection failed")


def check_prd_contract():
    from agents.prompts_arquiteto import REQUIRED_SECTIONS, _garantir_secoes_obrigatorias

    sections = _garantir_secoes_obrigatorias([{"name": "hero", "layout_type": "hero-split"}])
    names = {section["name"] for section in sections}
    missing = set(REQUIRED_SECTIONS) - names
    if missing:
        raise RuntimeError("missing required sections: " + ", ".join(sorted(missing)))


def check_context_contract():
    banned_terms = (
        "theo.py",
        "builder_poc.py",
        "liz.py",
        "alex.py",
        "theo_agent_loop",
        "bryan_agent_loop",
        "arquiteto_agent_loop",
        "temp-open-design",
        "FRALIB_FINAL",
        "fralib_deploy",
        "fralib_temp",
    )
    roots = ("AGENTS.md", "CLAUDE.md", "README.md", "docs", "backend", "frontend", "server.py", "worker.py")
    skip_parts = {
        "__pycache__",
        ".pytest_cache",
        "jina_cache",
        "node_modules",
        "unsplash_cache",
    }
    offenders = []

    def iter_files():
        for rel in roots:
            path = ROOT / rel
            if path.is_file():
                yield path
            elif path.is_dir():
                for item in path.rglob("*"):
                    if item.is_file() and not any(part in skip_parts for part in item.parts):
                        yield item

    for path in iter_files():
        if path.suffix.lower() in {
            ".bak",
            ".backup",
            ".pyc",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".gif",
            ".ico",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for term in banned_terms:
            if term in text:
                offenders.append(f"{path.relative_to(ROOT)}:{term}")
                break
        if len(offenders) >= 20:
            break

    if offenders:
        raise RuntimeError("legacy context terms found: " + ", ".join(offenders))


def check_landing_visual_lock():
    import subprocess

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_landing_visual_lock.py")],
        check=True,
    )


def check_frontend_canonical():
    import subprocess

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_frontend_canonical.py")],
        check=True,
    )


def check_deploy_contract():
    import subprocess

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_deploy_contract.py")],
        check=True,
    )


def check_phase6_contracts():
    import subprocess

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--confcutdir=tests/unit",
            "--no-cov",
            str(ROOT / "tests" / "unit" / "test_builder_publication_phase6_contract.py"),
        ],
        check=True,
    )


def check_ports():
    ports = {"fralib": 8000, "meowhats": 3001, "postgres": 5433}
    strict = os.getenv("FRALIB_SMOKE_STRICT_PORTS", "0") == "1" or os.name != "nt"
    for name, port in ports.items():
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                print(f"  {name}:127.0.0.1:{port} ok")
        except OSError:
            if strict:
                raise
            print(f"  warning: optional local port skipped on Windows dev: {name}:{port}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="No LLM, deploy, WhatsApp, or scraper calls")
    parser.add_argument("--fix-locks", action="store_true", help="Reap stale running jobs older than 5 minutes")
    args = parser.parse_args()

    if not args.dry_run:
        raise SystemExit("Use --dry-run. Live smoke is intentionally not implemented yet.")

    total = time.perf_counter()
    with step("env"):
        require_env()
    with step("imports"):
        check_imports()
    with step("database-and-locks"):
        check_db(fix_locks=args.fix_locks)
    with step("caio-rules"):
        check_caio()
    with step("prd-contract"):
        check_prd_contract()
    with step("context-contract"):
        check_context_contract()
    with step("landing-visual-lock"):
        check_landing_visual_lock()
    with step("frontend-canonical"):
        check_frontend_canonical()
    with step("deploy-contract"):
        check_deploy_contract()
    with step("phase6-contracts"):
        check_phase6_contracts()
    with step("local-ports"):
        check_ports()

    report = {
        "mode": "dry-run",
        "seconds": round(time.perf_counter() - total, 3),
        "tokens_observed": 0,
        "llm_calls": 0,
        "deploy": "skipped",
        "whatsapp": "skipped",
        "results": RESULTS,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if any(row["status"] != "pass" for row in RESULTS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

