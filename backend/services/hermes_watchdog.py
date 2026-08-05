"""Read-only Hermes watchdog snapshots and guarded incident logging."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import urlopen

from sqlalchemy import text
from sqlalchemy.orm import Session


SAFE_ACTIONS: dict[str, list[str]] = {
    "smoke_dry_run": ["python", "pipeline.py", "smoke", "--dry-run"],
    "recover_runtime": ["python", "pipeline.py", "recover-runtime"],
    "mp_reconcile_dry_run": ["python", "scripts/vps_reconcile_mercadopago_payments.py", "--hours", "24", "--dry-run"],
    "mp_reconcile_apply": ["python", "scripts/vps_reconcile_mercadopago_payments.py", "--hours", "24", "--apply"],
}

SAFE_PM2_RESTARTS = {
    ("pm2", "restart", "fralib"),
    ("pm2", "restart", "fralib-worker"),
    ("pm2", "restart", "fralib-franz-worker"),
    ("pm2", "restart", "meowhats"),
}

# Mapeamento PM2 legacy -> systemd canonical (auto-detect)
PM2_TO_SYSTEMD = {
    "fralib": "fralib-api",
    "fralib-worker": "fralib-worker",
    "fralib-franz-worker": "fralib-franz",
    "fralib-wpp-listener": "fralib-wpp-listener",
    "fralib-hermes-watchdog": "fralib-hermes",
    "meowhats": "whatsmeow",  # whatsmeow fica como esta (ja em systemd)
}


def _detect_runtime() -> str:
    """Detecta runtime primario: systemd, pm2 ou none."""
    import shutil
    if shutil.which("systemctl"):
        try:
            import subprocess
            r = subprocess.run(
                ["systemctl", "list-unit-files", "fralib-*.service", "--no-legend"],
                capture_output=True, text=True, timeout=5
            )
            if r.stdout.strip():
                return "systemd"
        except Exception:
            pass
    if shutil.which("pm2"):
        return "pm2"
    return "none"


def _build_restart_command(legacy_pm2_name: str) -> list[str]:
    """Constroi comando de restart usando systemd OU pm2 (auto-detect).

    Args:
        legacy_pm2_name: nome antigo (PM2) - ex: 'fralib', 'fralib-worker'

    Returns:
        Lista com comando - ex: ['systemctl', 'restart', 'fralib-api']
                              ou ['pm2', 'restart', 'fralib']
    """
    runtime = _detect_runtime()
    if runtime == "systemd":
        canonical = PM2_TO_SYSTEMD.get(legacy_pm2_name, legacy_pm2_name)
        return ["systemctl", "restart", canonical]
    else:
        # Fallback PM2 (mantem comportamento legado)
        return ["pm2", "restart", legacy_pm2_name]


def _safe_restart_commands(legacy_pm2_names: list[str]) -> list[tuple]:
    """Versao auto-detect do SAFE_PM2_RESTARTS (tuplas para guardrail)."""
    runtime = _detect_runtime()
    result = set()
    for legacy_name in legacy_pm2_names:
        cmd = tuple(_build_restart_command(legacy_name))
        result.add(cmd)
    return result

DANGEROUS_PATTERNS = [
    r"\bscp\b",
    r"\brsync\b",
    r"\bpm2\s+kill\b",
    r"\brm\b",
    r"\bfind\b.*\b-delete\b",
    r"\btruncate\b",
    r"\bdelete\s+from\b",
    r"\bupdate\s+jobs\b",
    r"\bupdate\s+pipeline_queue\b",
    r"\breset-runtime\b",
    r"/var/www/fralib",
    r"/root/fralib",
]

ROOT = Path(__file__).resolve().parents[2]
REMEDIATION_INCIDENT_TYPES = {"remediation_applied", "remediation_failed"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_hermes_tables(db: Session) -> None:
    dialect = getattr(getattr(db, "bind", None), "dialect", None)
    is_postgres = getattr(dialect, "name", "") == "postgresql"
    if is_postgres:
        create_sql = """
        CREATE TABLE IF NOT EXISTS hermes_incidents (
            id SERIAL PRIMARY KEY,
            severity VARCHAR(20) NOT NULL,
            incident_type VARCHAR(80) NOT NULL,
            title TEXT NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'open',
            evidence JSONB DEFAULT '{}'::jsonb,
            recommended_action TEXT,
            source VARCHAR(80) DEFAULT 'hermes',
            actor_id INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    else:
        create_sql = """
        CREATE TABLE IF NOT EXISTS hermes_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            severity VARCHAR(20) NOT NULL,
            incident_type VARCHAR(80) NOT NULL,
            title TEXT NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'open',
            evidence TEXT DEFAULT '{}',
            recommended_action TEXT,
            source VARCHAR(80) DEFAULT 'hermes',
            actor_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    db.execute(text(create_sql))
    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_hermes_incidents_created
            ON hermes_incidents (created_at DESC)
            """
        )
    )
    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_hermes_incidents_status
            ON hermes_incidents (status, severity, created_at DESC)
            """
        )
    )
    db.commit()


def _fetch_all(db: Session, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    try:
        rows = db.execute(text(sql), params or {}).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        return [{"error": str(exc)}]


def _fetch_one(db: Session, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        row = db.execute(text(sql), params or {}).fetchone()
        return dict(row._mapping) if row else {}
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        return {"error": str(exc)}


def _pm2_snapshot() -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["pm2", "jlist"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode != 0:
            return {"status": "unknown", "error": (result.stderr or result.stdout or "").strip()[:500]}
        processes = []
        for item in json.loads(result.stdout or "[]"):
            env = item.get("pm2_env") or {}
            processes.append(
                {
                    "name": item.get("name"),
                    "status": env.get("status"),
                    "pid": item.get("pid"),
                    "restart_time": env.get("restart_time"),
                    "memory": (item.get("monit") or {}).get("memory"),
                    "cpu": (item.get("monit") or {}).get("cpu"),
                }
            )
        return {"status": "ok", "processes": processes}
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


def _redis_snapshot() -> dict[str, Any]:
    redis_url = (os.getenv("REDIS_URL") or "").strip()
    if not redis_url:
        return {"status": "skipped", "message": "REDIS_URL not configured"}
    try:
        import redis

        client = redis.from_url(redis_url)
        start = time.monotonic()
        pong = client.ping()
        return {"status": "ok" if pong else "error", "latency_ms": round((time.monotonic() - start) * 1000)}
    except ModuleNotFoundError:
        try:
            result = subprocess.run(
                ["redis-cli", "ping"],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0 and "PONG" in (result.stdout or ""):
                return {"status": "ok", "message": "PONG via redis-cli"}
            return {"status": "error", "message": (result.stderr or result.stdout or "").strip()[:300]}
        except Exception as cli_exc:
            return {"status": "error", "message": f"redis module missing; redis-cli failed: {cli_exc}"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def _http_probe(url: str, timeout_s: float = 1.5) -> dict[str, Any]:
    try:
        start = time.monotonic()
        with urlopen(url, timeout=timeout_s) as response:
            return {
                "status": "ok" if 200 <= response.status < 500 else "error",
                "code": response.status,
                "latency_ms": round((time.monotonic() - start) * 1000),
            }
    except HTTPError as exc:
        if exc.code in {401, 403}:
            return {"status": "auth_required", "code": exc.code, "latency_ms": 0}
        return {"status": "error", "code": exc.code, "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def _jobs_snapshot(db: Session) -> dict[str, Any]:
    by_status = _fetch_all(
        db,
        """
        SELECT status, tipo, COUNT(*) AS total
        FROM jobs
        WHERE criado_em > NOW() - INTERVAL '7 days'
        GROUP BY status, tipo
        ORDER BY status, tipo
        """,
    )
    oldest = _fetch_one(
        db,
        """
        SELECT id, tipo, tenant_id, status, last_phase, attempts, max_attempts,
               EXTRACT(EPOCH FROM (NOW() - COALESCE(worker_heartbeat, criado_em)))::int AS age_seconds
        FROM jobs
        WHERE status IN ('pending', 'running')
        ORDER BY COALESCE(worker_heartbeat, criado_em) ASC
        LIMIT 1
        """,
    )
    stale = _fetch_all(
        db,
        """
        SELECT id, tipo, tenant_id, last_phase,
               EXTRACT(EPOCH FROM (NOW() - worker_heartbeat))::int AS heartbeat_age_seconds
        FROM jobs
        WHERE status='running'
          AND worker_heartbeat < NOW() - INTERVAL '5 minutes'
        ORDER BY worker_heartbeat ASC
        LIMIT 20
        """,
    )
    return {"by_status": by_status, "oldest_active": oldest, "stale_running": stale}


def _queue_snapshot(db: Session) -> dict[str, Any]:
    return {"status": "legacy", "message": "pipeline_queue is audit-only; jobs is canonical"}


def _payment_snapshot(db: Session) -> dict[str, Any]:
    return {
        "last_24h": _fetch_one(
            db,
            """
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE processado = true) AS processed,
                   COUNT(*) FILTER (WHERE processado = false) AS unprocessed,
                   COUNT(*) FILTER (WHERE erro IS NOT NULL AND erro <> '') AS errors
            FROM mercadopago_events
            WHERE criado_em > NOW() - INTERVAL '24 hours'
            """,
        ),
        "recent_errors": _fetch_all(
            db,
            """
            SELECT event_id, tipo, user_id, payment_id, erro, criado_em
            FROM mercadopago_events
            WHERE erro IS NOT NULL AND erro <> ''
            ORDER BY criado_em DESC
            LIMIT 10
            """,
        ),
    }


def _provider_snapshot(db: Session) -> dict[str, Any]:
    return {
        "alerts_24h": _fetch_one(
            db,
            """
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE lido = false) AS open
            FROM provider_alerts
            WHERE criado_em > NOW() - INTERVAL '24 hours'
            """,
        )
    }


def collect_snapshot(db: Session) -> dict[str, Any]:
    """Collect operational evidence without mutating runtime state."""
    snapshot = {
        "ok": True,
        "generated_at": _utc_now(),
        "mode": "read_only",
        "env": {
            "fralib_env": os.getenv("FRALIB_ENV", "dev"),
            "app_url": os.getenv("APP_URL", ""),
            "mercadopago_configured": bool(os.getenv("MERCADOPAGO_ACCESS_TOKEN")),
            "mercadopago_webhook_secret": bool(os.getenv("MERCADOPAGO_WEBHOOK_SECRET")),
        },
        "database": _fetch_one(db, "SELECT 1 AS ok"),
        "pm2": _pm2_snapshot(),
        "redis": _redis_snapshot(),
        "api": _http_probe("http://127.0.0.1:8000/health"),
        "whatsapp": _http_probe("http://127.0.0.1:3001/health"),
        "jobs": _jobs_snapshot(db),
        "legacy_queue": _queue_snapshot(db),
        "payments": _payment_snapshot(db),
        "providers": _provider_snapshot(db),
    }
    snapshot["diagnostics"] = diagnose_snapshot(snapshot)
    return snapshot


def diagnose_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    incidents: list[dict[str, Any]] = []
    stale_jobs = [j for j in snapshot.get("jobs", {}).get("stale_running", []) if not j.get("error")]
    if stale_jobs:
        incidents.append(
            {
                "severity": "SEV2",
                "incident_type": "worker_stale",
                "title": f"{len(stale_jobs)} running job(s) with stale heartbeat",
                "recommended_action": "Run python pipeline.py recover-runtime; restart only fralib-worker if still stale.",
                "evidence": {"jobs": stale_jobs[:5]},
            }
        )

    payments = snapshot.get("payments", {}).get("last_24h", {})
    if payments.get("errors"):
        incidents.append(
            {
                "severity": "SEV1",
                "incident_type": "payment_webhook_errors",
                "title": f"{payments.get('errors')} Mercado Pago event(s) with errors in 24h",
                "recommended_action": "Run Mercado Pago reconciliation dry-run before applying idempotent repair.",
                "evidence": {"summary": payments, "recent_errors": snapshot.get("payments", {}).get("recent_errors", [])[:3]},
            }
        )

    redis_status = snapshot.get("redis", {}).get("status")
    if snapshot.get("env", {}).get("fralib_env") == "prod" and redis_status not in {"ok", "skipped"}:
        incidents.append(
            {
                "severity": "SEV2",
                "incident_type": "redis_unavailable",
                "title": "Redis is unavailable in production",
                "recommended_action": "Restore Redis through approved infra routine, then rerun smoke.",
                "evidence": snapshot.get("redis", {}),
            }
        )

    api_status = snapshot.get("api", {}).get("status")
    if api_status != "ok":
        incidents.append(
            {
                "severity": "SEV1",
                "incident_type": "api_unhealthy",
                "title": "API health probe failed",
                "recommended_action": "Inspect /health payload, fralib PM2 logs and deploy hook output.",
                "evidence": snapshot.get("api", {}),
            }
        )

    whatsapp_status = snapshot.get("whatsapp", {}).get("status")
    if whatsapp_status not in {"ok", "auth_required"}:
        incidents.append(
            {
                "severity": "SEV2",
                "incident_type": "whatsapp_bridge_unhealthy",
                "title": "WhatsApp bridge health probe failed",
                "recommended_action": "Restart only meowhats after Guard approval.",
                "evidence": snapshot.get("whatsapp", {}),
            }
        )

    pm2 = snapshot.get("pm2", {})
    if pm2.get("status") == "ok":
        down = [
            p for p in pm2.get("processes", [])
            if p.get("name") in {"fralib", "fralib-worker", "meowhats"} and p.get("status") != "online"
        ]
        if down:
            incidents.append(
                {
                    "severity": "SEV1",
                    "incident_type": "pm2_process_down",
                    "title": "Critical PM2 process is not online",
                    "recommended_action": "Restart only the affected allowlisted process after Guard approval.",
                    "evidence": {"processes": down},
                }
            )
    return incidents


def _json_dump(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, default=str)


def record_incident(
    db: Session,
    incident: dict[str, Any],
    *,
    source: str = "hermes",
    actor_id: int | None = None,
) -> int:
    ensure_hermes_tables(db)
    dialect = getattr(getattr(db, "bind", None), "dialect", None)
    is_postgres = getattr(dialect, "name", "") == "postgresql"
    sql = (
        """
        INSERT INTO hermes_incidents
            (severity, incident_type, title, evidence, recommended_action, source, actor_id)
        VALUES (:severity, :incident_type, :title, CAST(:evidence AS jsonb),
                :recommended_action, :source, :actor_id)
        RETURNING id
        """
        if is_postgres
        else
        """
        INSERT INTO hermes_incidents
            (severity, incident_type, title, evidence, recommended_action, source, actor_id)
        VALUES (:severity, :incident_type, :title, :evidence,
                :recommended_action, :source, :actor_id)
        RETURNING id
        """
    )
    row = db.execute(
        text(sql),
        {
            "severity": incident.get("severity") or "SEV4",
            "incident_type": incident.get("incident_type") or "unknown",
            "title": incident.get("title") or "Hermes incident",
            "evidence": _json_dump(incident.get("evidence") or {}),
            "recommended_action": incident.get("recommended_action") or "",
            "source": source,
            "actor_id": actor_id,
        },
    ).fetchone()
    db.commit()
    return int(row[0])


def list_incidents(db: Session, limit: int = 50) -> list[dict[str, Any]]:
    ensure_hermes_tables(db)
    rows = db.execute(
        text(
            """
            SELECT id, severity, incident_type, title, status, evidence,
                   recommended_action, source, actor_id, created_at
            FROM hermes_incidents
            ORDER BY created_at DESC, id DESC
            LIMIT :limit
            """
        ),
        {"limit": max(1, min(int(limit or 50), 200))},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def normalize_command(command: Any) -> list[str]:
    if isinstance(command, str):
        return [part for part in command.strip().split() if part]
    if isinstance(command, list):
        return [str(part) for part in command]
    return []


def guard_check(action: str | None = None, command: Any = None) -> dict[str, Any]:
    cmd = normalize_command(command)
    joined = " ".join(cmd) if cmd else (action or "")
    lowered = joined.lower()
    reasons = []

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, lowered):
            reasons.append(f"matched deny pattern: {pattern}")

    allowed = False
    if not reasons:
        if action in SAFE_ACTIONS and (not cmd or cmd == SAFE_ACTIONS[action]):
            allowed = True
        elif cmd and cmd in SAFE_ACTIONS.values():
            allowed = True
        elif tuple(cmd) in SAFE_PM2_RESTARTS:
            allowed = True

    if not allowed and not reasons:
        reasons.append("not in Hermes allowlist")

    return {
        "allowed": allowed,
        "action": action or "",
        "command": cmd,
        "reasons": reasons,
        "mode": "guarded",
    }


def record_blocked_action(
    db: Session,
    *,
    action: str | None = None,
    command: Any = None,
    actor_id: int | None = None,
) -> dict[str, Any]:
    decision = guard_check(action, command)
    if decision["allowed"]:
        return {"recorded": False, "decision": decision}
    incident = {
        "severity": "SEV3",
        "incident_type": "blocked_action",
        "title": "Hermes Guard blocked a non-allowlisted action",
        "recommended_action": "Escalate to human and implement through Git/versioned script if still needed.",
        "evidence": decision,
    }
    incident_id = record_incident(db, incident, source="hermes_guard", actor_id=actor_id)
    return {"recorded": True, "incident_id": incident_id, "decision": decision}


def _coerce_command_for_runtime(command: list[str]) -> list[str]:
    if command and command[0] == "python":
        return [sys.executable, *command[1:]]
    return command


def _parse_evidence(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _recent_remediation_exists(db: Session, action_key: str, cooldown_seconds: int) -> bool:
    ensure_hermes_tables(db)
    dialect = getattr(getattr(db, "bind", None), "dialect", None)
    is_postgres = getattr(dialect, "name", "") == "postgresql"
    if is_postgres:
        sql = """
            SELECT evidence
            FROM hermes_incidents
            WHERE incident_type IN ('remediation_applied', 'remediation_failed')
              AND created_at > NOW() - (:seconds || ' seconds')::interval
            ORDER BY created_at DESC
            LIMIT 50
        """
    else:
        sql = """
            SELECT evidence
            FROM hermes_incidents
            WHERE incident_type IN ('remediation_applied', 'remediation_failed')
              AND created_at > datetime('now', '-' || :seconds || ' seconds')
            ORDER BY created_at DESC
            LIMIT 50
        """
    rows = db.execute(text(sql), {"seconds": max(60, int(cooldown_seconds or 900))}).fetchall()
    for row in rows:
        evidence = _parse_evidence(dict(row._mapping).get("evidence"))
        if evidence.get("action_key") == action_key:
            return True
    return False


def execute_guarded_action(
    db: Session,
    *,
    action: str | None = None,
    command: Any = None,
    trigger: dict[str, Any] | None = None,
    source: str = "hermes_executor",
    actor_id: int | None = None,
    cooldown_seconds: int | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    """Execute one allowlisted action and append before/after evidence."""
    decision = guard_check(action=action, command=command)
    if not decision["allowed"]:
        blocked = record_blocked_action(db, action=action, command=command, actor_id=actor_id)
        return {"executed": False, "blocked": True, "decision": decision, "blocked_incident": blocked}

    cmd = decision["command"] or SAFE_ACTIONS.get(action or "", [])
    if not cmd:
        blocked = record_blocked_action(db, action=action, command=command, actor_id=actor_id)
        return {"executed": False, "blocked": True, "decision": decision, "blocked_incident": blocked}

    action_key = action or " ".join(cmd)
    cooldown = max(60, int(cooldown_seconds if cooldown_seconds is not None else os.getenv("HERMES_REMEDIATION_COOLDOWN_SECONDS", "900")))
    if _recent_remediation_exists(db, action_key, cooldown):
        return {"executed": False, "blocked": False, "skipped": "cooldown", "action_key": action_key, "cooldown_seconds": cooldown}

    runtime_cmd = _coerce_command_for_runtime(cmd)
    timeout = max(10, int(timeout_seconds if timeout_seconds is not None else os.getenv("HERMES_REMEDIATION_TIMEOUT_SECONDS", "120")))
    started = _utc_now()
    try:
        result = subprocess.run(
            runtime_cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            shell=False,
        )
        returncode = result.returncode
        stdout_tail = (result.stdout or "")[-4000:]
        stderr_tail = (result.stderr or "")[-4000:]
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout_tail = (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else ""
        stderr_tail = (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "timeout"

    evidence = {
        "action_key": action_key,
        "action": action or "",
        "command": cmd,
        "runtime_command": runtime_cmd,
        "guard": decision,
        "trigger": trigger or {},
        "started_at": started,
        "finished_at": _utc_now(),
        "returncode": returncode,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }
    incident_type = "remediation_applied" if returncode == 0 else "remediation_failed"
    incident_id = record_incident(
        db,
        {
            "severity": "SEV3" if returncode == 0 else "SEV2",
            "incident_type": incident_type,
            "title": f"Hermes remediation {'applied' if returncode == 0 else 'failed'}: {action_key}",
            "recommended_action": "Review before/after evidence; escalate if the same action repeats.",
            "evidence": evidence,
        },
        source=source,
        actor_id=actor_id,
    )
    return {
        "executed": True,
        "ok": returncode == 0,
        "incident_id": incident_id,
        "action_key": action_key,
        "returncode": returncode,
    }


def auto_remediate_diagnostics(
    db: Session,
    incidents: list[dict[str, Any]],
    *,
    actor_id: int | None = None,
    source: str = "hermes_auto",
) -> list[dict[str, Any]]:
    """Apply only bounded, allowlisted playbooks for known diagnostics."""
    if os.getenv("HERMES_AUTOREMEDIATE", "0").strip() not in {"1", "true", "yes", "on"}:
        return []

    results: list[dict[str, Any]] = []
    for incident in incidents:
        incident_type = incident.get("incident_type")
        if incident_type == "worker_stale":
            results.append(
                execute_guarded_action(
                    db,
                    action="recover_runtime",
                    trigger=incident,
                    source=source,
                    actor_id=actor_id,
                )
            )
        elif incident_type == "payment_webhook_errors":
            payment_action = (
                "mp_reconcile_apply"
                if os.getenv("HERMES_AUTOREMEDIATE_PAYMENT_APPLY", "0").strip() in {"1", "true", "yes", "on"}
                else "mp_reconcile_dry_run"
            )
            results.append(
                execute_guarded_action(
                    db,
                    action=payment_action,
                    trigger=incident,
                    source=source,
                    actor_id=actor_id,
                )
            )
        elif incident_type == "api_unhealthy":
            results.append(
                execute_guarded_action(
                    db,
                    command=_build_restart_command("fralib"),
                    trigger=incident,
                    source=source,
                    actor_id=actor_id,
                )
            )
        elif incident_type == "whatsapp_bridge_unhealthy":
            results.append(
                execute_guarded_action(
                    db,
                    command=_build_restart_command("meowhats"),
                    trigger=incident,
                    source=source,
                    actor_id=actor_id,
                )
            )
        elif incident_type == "pm2_process_down":
            for process in (incident.get("evidence") or {}).get("processes", []):
                name = process.get("name")
                if name in {"fralib", "fralib-worker", "meowhats"}:
                    results.append(
                        execute_guarded_action(
                            db,
                            command=_build_restart_command(name),
                            trigger=incident,
                            source=source,
                            actor_id=actor_id,
                        )
                    )
    return results


def run_scan(db: Session, *, actor_id: int | None = None, auto_remediate: bool = False) -> dict[str, Any]:
    snapshot = collect_snapshot(db)
    diagnostics = snapshot.get("diagnostics", [])
    incident_ids = [
        record_incident(db, incident, source="hermes_scan", actor_id=actor_id)
        for incident in diagnostics
    ]
    remediation_results = auto_remediate_diagnostics(db, diagnostics, actor_id=actor_id) if auto_remediate else []
    return {
        "snapshot": snapshot,
        "recorded_incident_ids": incident_ids,
        "remediation_results": remediation_results,
    }
