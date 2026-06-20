"""FraLib operational CLI."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env")


def _command_env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("TEST_DATABASE_URL") and env.get("DATABASE_URL"):
        test_url = _derive_test_database_url(env["DATABASE_URL"])
        if test_url:
            env["TEST_DATABASE_URL"] = test_url
    root = str(ROOT)
    backend = str(ROOT / "backend")
    pythonpath = env.get("PYTHONPATH", "")
    parts = [root, backend]
    if pythonpath:
        parts.append(pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def _derive_test_database_url(database_url: str) -> str:
    try:
        parsed = urlsplit(database_url)
    except Exception:
        return ""
    if not parsed.scheme or not parsed.netloc:
        return ""
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            "/fralib_test",
            parsed.query,
            parsed.fragment,
        )
    )


def smoke(args):
    cmd = [sys.executable, str(ROOT / "scripts" / "pipeline_smoke.py")]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.fix_locks:
        cmd.append("--fix-locks")
    return subprocess.call(cmd, cwd=str(ROOT), env=_command_env())


def pre_release_gate(args):
    commands = [
        [sys.executable, str(ROOT / "pipeline.py"), "smoke", "--dry-run"],
        [sys.executable, str(ROOT / "scripts" / "check_secret_hygiene.py")],
        [sys.executable, str(ROOT / "scripts" / "tenant_scope_audit.py")],
        [sys.executable, "-m", "pytest", "-q", "tests/integration/test_idor_multitenant.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/integration/test_job_queue_concurrency.py"],
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/unit/test_pipeline_builders_contract.py",
            "tests/unit/test_builder_publication_phase6_contract.py",
            "tests/unit/test_site_editor_security.py",
            "tests/unit/test_pipeline_route_contract.py",
            "tests/unit/test_security_scalability_contract.py",
            "tests/unit/test_html_quality_gate.py",
        ],
    ]
    for cmd in commands:
        code = subprocess.call(cmd, cwd=str(ROOT), env=_command_env())
        if code != 0:
            return code
    return 0


def recover_runtime(args):
    cmd = [sys.executable, str(ROOT / "scripts" / "recover_runtime.py")]
    return subprocess.call(cmd, cwd=str(ROOT), env=_command_env())


def reset_runtime(args):
    cmd = [sys.executable, str(ROOT / "scripts" / "reset_runtime.py")]
    if args.confirm:
        cmd.extend(["--confirm", args.confirm])
    if args.keep_sites:
        cmd.append("--keep-sites")
    return subprocess.call(cmd, cwd=str(ROOT), env=_command_env())


def reset_controlled_test(args):
    cmd = [sys.executable, str(ROOT / "scripts" / "reset_controlled_test.py")]
    if args.confirm:
        cmd.extend(["--confirm", args.confirm])
    cmd.extend(["--tenant", str(args.tenant)])
    if args.lead_id:
        cmd.extend(["--lead-id", args.lead_id])
    if args.site_slug:
        cmd.extend(["--site-slug", args.site_slug])
    return subprocess.call(cmd, cwd=str(ROOT), env=_command_env())


def builder_job(args):
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "builder_worker_job.py"),
        "--prd-json",
        args.prd_json,
        "--tenant-id",
        str(args.tenant_id),
        "--job-id",
        args.job_id,
        "--target",
        args.target,
        "--model",
        args.model,
    ]
    if args.manifest_dir:
        cmd.extend(["--manifest-dir", args.manifest_dir])
    if args.execute:
        cmd.append("--execute")
    return subprocess.call(cmd, cwd=str(ROOT), env=_command_env())


def repair_provider_key(args):
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "repair_provider_key.py"),
        "--provider",
        args.provider,
        "--label",
        args.label,
        "--key-env",
        args.key_env,
    ]
    if args.base_url:
        cmd.extend(["--base-url", args.base_url])
    if args.model:
        cmd.extend(["--model", args.model])
    if args.created_by is not None:
        cmd.extend(["--created-by", str(args.created_by)])
    if args.apply:
        cmd.append("--apply")
    if args.mark_alerts_read:
        cmd.append("--mark-alerts-read")
    return subprocess.call(cmd, cwd=str(ROOT), env=_command_env())


def main():
    parser = argparse.ArgumentParser(prog="pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    smoke_parser = sub.add_parser("smoke", help="Run pipeline preflight smoke checks")
    smoke_parser.add_argument("--dry-run", action="store_true", help="Do not call LLM, deploy, or WhatsApp")
    smoke_parser.add_argument("--fix-locks", action="store_true", help="Reset stale pipeline locks older than 5 minutes")
    smoke_parser.set_defaults(func=smoke)

    gate_parser = sub.add_parser("pre-release-gate", help="Run required quality gate before release")
    gate_parser.set_defaults(func=pre_release_gate)

    rec_parser = sub.add_parser("recover-runtime", help="Safely recover runtime locks and stuck jobs")
    rec_parser.set_defaults(func=recover_runtime)

    reset_parser = sub.add_parser("reset-runtime", help="Reset runtime/test data while keeping users/config")
    reset_parser.add_argument("--confirm", default="", help="Required value: RESET")
    reset_parser.add_argument("--keep-sites", action="store_true", help="Do not remove generated site folders")
    reset_parser.set_defaults(func=reset_runtime)

    test_reset_parser = sub.add_parser("reset-controlled-test", help="Clean all residue before a controlled pipeline test")
    test_reset_parser.add_argument("--confirm", default="", help="Required value: RESET_TEST")
    test_reset_parser.add_argument("--tenant", type=int, default=2)
    test_reset_parser.add_argument("--lead-id", default="", help="Optional lead to reset to pending")
    test_reset_parser.add_argument("--site-slug", default="", help="Optional generated site slug to remove")
    test_reset_parser.set_defaults(func=reset_controlled_test)

    builder_parser = sub.add_parser("builder-job", help="Create an isolated post-PRD builder job")
    builder_parser.add_argument("--prd-json", required=True)
    builder_parser.add_argument("--tenant-id", required=True, type=int)
    builder_parser.add_argument("--job-id", required=True)
    builder_parser.add_argument("--target", default="landing-page", choices=["landing-page", "institutional-site", "app", "crm"])
    builder_parser.add_argument("--model", default="sonnet")
    builder_parser.add_argument("--manifest-dir", default="")
    builder_parser.add_argument("--execute", action="store_true")
    builder_parser.set_defaults(func=builder_job)

    key_parser = sub.add_parser("repair-provider-key", help="Validate and register an LLM provider key")
    key_parser.add_argument("--provider", default="anthropic", choices=["anthropic", "openai", "google", "groq", "openrouter"])
    key_parser.add_argument("--label", default="aibee-main")
    key_parser.add_argument("--base-url", default="")
    key_parser.add_argument("--model", default="")
    key_parser.add_argument("--key-env", default="FRALIB_PROVIDER_API_KEY")
    key_parser.add_argument("--created-by", type=int, default=None)
    key_parser.add_argument("--apply", action="store_true")
    key_parser.add_argument("--mark-alerts-read", action="store_true")
    key_parser.set_defaults(func=repair_provider_key)

    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
