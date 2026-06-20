"""FraLib local pipeline harness.

The harness is a dry-run bench for the active pipeline contract. It validates
fixtures, scenarios and safety guardrails without calling live providers,
deploy, WhatsApp, Mercado Pago, Hunter or paid scrapers.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = ROOT / "tests" / "harness" / "scenarios"
FIXTURE_DIR = ROOT / "tests" / "harness" / "fixtures"

ACTIVE_PHASES = {
    "lead_supply",
    "caio",
    "market_intel",
    "site_prompt_agent",
    "builder_renderer",
    "deploy_dry_run",
    "franz_sdr_simulated",
    "payment_dry_run",
    "worker_recover_dry_run",
}

FORBIDDEN_CAPABILITIES = {
    "live_llm",
    "live_hunter",
    "live_whatsapp",
    "live_deploy",
    "live_mercadopago",
    "paid_scraper",
    "external_http",
}

LIVE_SECRET_KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "JINA_API_KEY",
    "HUNTER_API_KEY",
    "MERCADOPAGO_ACCESS_TOKEN",
    "WHATSAPP_TOKEN",
    "MEOWHATS_API_KEY",
    "FRALIB_PROVIDER_API_KEY",
)

SAFE_COMMANDS = {
    ("python", "pipeline.py", "smoke", "--dry-run"),
    ("python", "scripts/pipeline_smoke.py", "--dry-run"),
    ("python", "scripts/vps_reconcile_mercadopago_payments.py", "--hours", "24", "--dry-run"),
    (
        "python",
        "scripts/vps_reconcile_mercadopago_payments.py",
        "--hours",
        "24",
        "--dry-run",
        "--fixture-json",
        "tests/harness/fixtures/payment_approved_dry_run.json",
    ),
    ("python", "pipeline.py", "recover-runtime"),
}

AUDIT_TARGET_SCRIPT_NAMES = {
    "pipeline_smoke.py",
    "check_deploy_contract.py",
    "verify_frontend_canonical.py",
    "tenant_scope_audit.py",
    "hermes_canary.py",
    "vps_validate_prod_launch.py",
    "vps_reconcile_mercadopago_payments.py",
    "audit_published_sites.py",
    "sdr_scenario_evals.py",
    "test_sdr_langgraph.py",
    "test_sdr_bryan.py",
    "test_personas.py",
    "test_evogym_sdr.py",
}

AUDIT_PATTERNS = {
    "PERIGOSO": (
        "requests.",
        "subprocess.run",
        "subprocess.call",
        "ssh ",
        "scp ",
        "rsync ",
        "deploy",
        "WhatsApp",
        "meowhats",
        "Mercado Pago",
        "MERCADOPAGO",
        "DATABASE_URL",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "JINA_API_KEY",
        "--apply",
    ),
    "EXTERNAL_LITERAL": (
        "http://",
        "https://",
        "WhatsApp",
        "meowhats",
        "Mercado Pago",
        "MERCADOPAGO",
    ),
    "OBSOLETO": (
        "bryan_agent_loop",
        "theo_agent_loop",
        "agent_loop",
        "sandbox-agent",
        "Bolt",
        "FRALIB_FINAL",
        "fralib_temp",
        "temp-open-design",
    ),
    "LEGADO_SEGURO": (
        "bryan",
        "Bryan",
        "openui",
        "html_quality_gate",
        "HTML gate",
    ),
    "ATUAL": (
        "lead_supply",
        "Caio",
        "caio",
        "site_prompt_agent",
        "builder_renderer",
        "vite",
        "Vite",
        "React",
        "tenant",
        "Mercado Pago",
        "sdr",
        "Franz",
        "Hermes",
        "guard",
        "pipeline",
        "phase6",
        "visual_contract",
    ),
    "DUPLICADO_FRAGIL": (
        "sleep",
        "timeout",
        "localhost",
        "127.0.0.1",
        "port",
        "conftest",
        "coverage",
    ),
}


class HarnessError(RuntimeError):
    pass


@dataclass
class StepResult:
    step: str
    status: str
    seconds: float
    evidence: list[str]
    detail: str = ""


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HarnessError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise HarnessError(f"invalid json {path}: {exc}") from exc


def scenario_path(name: str) -> Path:
    if not name or any(part in name for part in ("..", "/", "\\")):
        raise HarnessError("invalid scenario name")
    return SCENARIO_DIR / f"{name}.json"


def list_scenarios() -> list[dict]:
    scenarios = []
    for path in sorted(SCENARIO_DIR.glob("*.json")):
        data = load_json(path)
        scenarios.append(
            {
                "name": data.get("name", path.stem),
                "description": data.get("description", ""),
                "file": str(path.relative_to(ROOT)),
            }
        )
    return scenarios


def database_url_is_safe(value: str | None) -> tuple[bool, str]:
    if not value:
        return True, "DATABASE_URL absent"
    parsed = urlparse(value)
    if parsed.scheme.startswith("sqlite"):
        return True, "sqlite database"
    db_name = parsed.path.rsplit("/", 1)[-1].lower()
    if "test" in db_name or "harness" in db_name:
        return True, f"test database: {db_name}"
    return False, f"non-test database blocked: {db_name or parsed.path}"


def live_secret_markers(env: dict[str, str] | None = None) -> list[str]:
    env = env or os.environ
    if env.get("FRALIB_HARNESS_IGNORE_LOCAL_KEYS") == "1":
        return []
    return [key for key in LIVE_SECRET_KEYS if env.get(key)]


def validate_environment(env: dict[str, str] | None = None) -> list[str]:
    env = env or os.environ
    evidence = []
    ok, detail = database_url_is_safe(env.get("DATABASE_URL"))
    evidence.append(detail)
    if not ok:
        raise HarnessError(detail)
    secrets = live_secret_markers(env)
    if secrets:
        raise HarnessError(
            "live provider/payment/WhatsApp keys present; unset them or set "
            "FRALIB_HARNESS_IGNORE_LOCAL_KEYS=1 for local key-presence audits only: "
            + ", ".join(secrets)
        )
    evidence.append("no live secret markers in process environment")
    return evidence


def validate_scenario(data: dict) -> list[str]:
    evidence = []
    if data.get("mode") != "dry-run":
        raise HarnessError("scenario mode must be dry-run")
    allowed = set(data.get("allowed_capabilities", []))
    forbidden_allowed = sorted(allowed & FORBIDDEN_CAPABILITIES)
    if forbidden_allowed:
        raise HarnessError("scenario allows forbidden capabilities: " + ", ".join(forbidden_allowed))
    declared_forbidden = set(data.get("forbidden_capabilities", []))
    missing_forbidden = sorted(FORBIDDEN_CAPABILITIES - declared_forbidden)
    if missing_forbidden:
        raise HarnessError("scenario must explicitly forbid: " + ", ".join(missing_forbidden))
    phases = data.get("expected_phases") or []
    unknown = sorted(set(phases) - ACTIVE_PHASES)
    if unknown:
        raise HarnessError("scenario uses phases outside active pipeline: " + ", ".join(unknown))
    if not phases:
        raise HarnessError("scenario must declare expected_phases")
    for command in data.get("safe_commands", []):
        command_tuple = tuple(command)
        if command_tuple not in SAFE_COMMANDS:
            raise HarnessError("command is not in harness allowlist: " + " ".join(command))
    evidence.append("dry-run scenario")
    evidence.append("forbidden capabilities explicitly blocked")
    evidence.append("expected phases are active pipeline phases")
    return evidence


def validate_fixtures(data: dict) -> list[str]:
    evidence = []
    for fixture in data.get("fixtures", []):
        path = FIXTURE_DIR / fixture
        payload = load_json(path)
        evidence.append(f"fixture ok: {path.relative_to(ROOT)} keys={','.join(sorted(payload.keys()))}")
    return evidence


def run_step(name: str, func) -> StepResult:
    start = time.perf_counter()
    try:
        evidence = func()
        return StepResult(name, "PASS", round(time.perf_counter() - start, 4), evidence)
    except Exception as exc:
        return StepResult(name, "FAIL", round(time.perf_counter() - start, 4), [], f"{type(exc).__name__}: {exc}")


def run_scenario(name: str, *, dry_run: bool, env: dict[str, str] | None = None) -> dict:
    if not dry_run:
        raise HarnessError("harness requires --dry-run")
    data = load_json(scenario_path(name))
    results = [
        run_step("environment_guard", lambda: validate_environment(env)),
        run_step("scenario_contract", lambda: validate_scenario(data)),
        run_step("fixtures", lambda: validate_fixtures(data)),
        run_step(
            "pass_fail_criteria",
            lambda: [f"criterion: {item}" for item in data.get("pass_criteria", [])],
        ),
    ]
    ok = all(item.status == "PASS" for item in results)
    return {
        "scenario": data.get("name", name),
        "description": data.get("description", ""),
        "mode": "dry-run",
        "ok": ok,
        "expected_phases": data.get("expected_phases", []),
        "mocked_systems": data.get("mocked_systems", []),
        "results": [item.__dict__ for item in results],
    }


def discover_audit_files() -> list[Path]:
    files = sorted((ROOT / "tests").rglob("test*.py"))
    files.extend(sorted((ROOT / "tests").rglob("*_test.py")))
    for path in sorted((ROOT / "scripts").glob("*.py")):
        if path.name in AUDIT_TARGET_SCRIPT_NAMES:
            files.append(path)
    return sorted(set(files))


def classify_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    hits: dict[str, list[str]] = {}
    for category, patterns in AUDIT_PATTERNS.items():
        matched = [pattern for pattern in patterns if pattern in text or pattern.lower() in rel.lower()]
        if matched:
            hits[category] = matched[:8]

    guardrail_test = "guard" in text.lower() and (
        "blocks" in text.lower() or "blocked" in text.lower() or "must not" in text.lower()
    )
    dangerous = "PERIGOSO" in hits
    unit_uses_safe_sqlite = rel.startswith("tests/unit/") and "sqlite://" in text
    mocked_requests = "monkeypatch.setattr" in text and "requests." in text
    local_test_db_guard = (
        "fralib_test" in text
        and "urlsplit" in text
        and ("localhost" in text or "127.0.0.1" in text)
    )
    read_only_contract = rel in {
        "scripts/check_deploy_contract.py",
        "scripts/sdr_scenario_evals.py",
        "tests/unit/test_designer_prd_contract.py",
        "tests/unit/test_html_quality_gate.py",
        "tests/unit/test_operational_script_guardrails.py",
        "tests/unit/test_secret_hygiene_contract.py",
        "tests/unit/test_security_scalability_contract.py",
    }
    mocked_llm = "monkeypatch.setattr" in text and "call_claude" in text
    smoke_dry_run_guarded = rel == "scripts/pipeline_smoke.py" and "Live smoke is intentionally not implemented yet" in text
    if rel.startswith("tests/unit/") and guardrail_test:
        dangerous = False
    if unit_uses_safe_sqlite or mocked_requests or local_test_db_guard or read_only_contract or mocked_llm:
        dangerous = False
    if smoke_dry_run_guarded:
        dangerous = False
    if rel.endswith("tests/unit/test_pipeline_harness.py"):
        dangerous = False

    explicit_legacy = "pytest.mark.legacy" in text
    bryan_legacy = explicit_legacy or "bryan" in rel.lower()

    if rel.endswith("tests/unit/test_pipeline_harness.py"):
        classification = "ATUAL"
    elif read_only_contract or mocked_llm:
        classification = "ATUAL"
    elif dangerous:
        classification = "PERIGOSO"
    elif explicit_legacy:
        classification = "LEGADO_SEGURO"
    elif bryan_legacy and "LEGADO_SEGURO" in hits:
        classification = "LEGADO_SEGURO"
    elif "OBSOLETO" in hits and "ATUAL" not in hits:
        classification = "OBSOLETO"
    elif "LEGADO_SEGURO" in hits and "ATUAL" not in hits:
        classification = "LEGADO_SEGURO"
    elif "DUPLICADO_FRAGIL" in hits and "ATUAL" not in hits:
        classification = "DUPLICADO_FRAGIL"
    elif "ATUAL" in hits:
        classification = "ATUAL"
    elif rel.startswith("tests/e2e/") and "EXTERNAL_LITERAL" in hits:
        classification = "DUPLICADO_FRAGIL"
    else:
        classification = "DUPLICADO_FRAGIL"

    return {
        "file": rel,
        "classification": classification,
        "evidence": hits,
    }


def audit_tests() -> dict:
    entries = [classify_file(path) for path in discover_audit_files()]
    summary: dict[str, int] = {}
    for entry in entries:
        summary[entry["classification"]] = summary.get(entry["classification"], 0) + 1
    return {
        "mode": "static-audit",
        "files": len(entries),
        "summary": dict(sorted(summary.items())),
        "entries": entries,
    }


def print_json(payload: dict | list) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="FraLib local dry-run pipeline harness")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List harness scenarios")

    audit = sub.add_parser("audit-tests", help="Classify tests and smoke/contract scripts")
    audit.add_argument("--json", action="store_true", help="Emit JSON")

    run = sub.add_parser("run", help="Run harness scenario(s)")
    run.add_argument("--scenario", default="", help="Scenario name")
    run.add_argument("--all", action="store_true", help="Run all scenarios")
    run.add_argument("--dry-run", action="store_true", help="Required: do not call live systems")

    args = parser.parse_args()
    try:
        if args.command == "list":
            print_json(list_scenarios())
            return 0
        if args.command == "audit-tests":
            report = audit_tests()
            if args.json:
                print_json(report)
            else:
                print(f"files={report['files']} summary={report['summary']}")
                for entry in report["entries"]:
                    print(f"{entry['classification']}\t{entry['file']}\t{entry['evidence']}")
            return 0
        if args.command == "run":
            names = [item["name"] for item in list_scenarios()] if args.all else [args.scenario]
            if not names or not names[0]:
                raise HarnessError("provide --scenario <name> or --all")
            reports = [run_scenario(name, dry_run=args.dry_run) for name in names]
            print_json({"ok": all(item["ok"] for item in reports), "scenarios": reports})
            return 0 if all(item["ok"] for item in reports) else 1
    except HarnessError as exc:
        print_json({"ok": False, "error": str(exc)})
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
