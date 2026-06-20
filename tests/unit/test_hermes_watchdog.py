from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.services.hermes_watchdog import (
    auto_remediate_diagnostics,
    diagnose_snapshot,
    execute_guarded_action,
    guard_check,
    list_incidents,
    record_blocked_action,
)


def _sqlite_session():
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    return Session()


def test_guard_allows_exact_recover_runtime_command():
    decision = guard_check(
        action="recover_runtime",
        command=["python", "pipeline.py", "recover-runtime"],
    )
    command_only = guard_check(command="python pipeline.py smoke --dry-run")
    payment_dry_run = guard_check(
        action="mp_reconcile_dry_run",
        command="python scripts/vps_reconcile_mercadopago_payments.py --hours 24 --dry-run",
    )
    payment_apply = guard_check(
        action="mp_reconcile_apply",
        command="python scripts/vps_reconcile_mercadopago_payments.py --hours 24 --apply",
    )

    assert decision["allowed"] is True
    assert decision["reasons"] == []
    assert command_only["allowed"] is True
    assert command_only["reasons"] == []
    assert payment_dry_run["allowed"] is True
    assert payment_apply["allowed"] is True


def test_guard_blocks_destructive_commands():
    examples = [
        "pm2 kill",
        "rm -rf /var/www/fralib",
        "scp file root@host:/root/fralib",
        "DELETE FROM jobs",
        "python pipeline.py reset-runtime --confirm RESET",
    ]

    for command in examples:
        decision = guard_check(command=command)
        assert decision["allowed"] is False
        assert decision["reasons"], command


def test_blocked_action_records_append_only_incident():
    db = _sqlite_session()

    result = record_blocked_action(
        db,
        command="rm -rf /var/www/fralib",
        actor_id=7,
    )
    incidents = list_incidents(db)

    assert result["recorded"] is True
    assert result["decision"]["allowed"] is False
    assert len(incidents) == 1
    assert incidents[0]["incident_type"] == "blocked_action"
    assert incidents[0]["severity"] == "SEV3"
    assert incidents[0]["actor_id"] == 7


def test_execute_guarded_action_blocks_destructive_without_subprocess(monkeypatch):
    db = _sqlite_session()
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("destructive action must not run")

    monkeypatch.setattr("backend.services.hermes_watchdog.subprocess.run", fake_run)

    result = execute_guarded_action(
        db,
        command="rm -rf /var/www/fralib",
        actor_id=7,
    )
    incidents = list_incidents(db)

    assert result["executed"] is False
    assert result["blocked"] is True
    assert calls == []
    assert incidents[0]["incident_type"] == "blocked_action"


def test_execute_guarded_action_runs_allowlisted_recovery_and_cooldown(monkeypatch):
    db = _sqlite_session()
    calls = []

    class FakeResult:
        returncode = 0
        stdout = "OK recover_runtime"
        stderr = ""

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return FakeResult()

    monkeypatch.setattr("backend.services.hermes_watchdog.subprocess.run", fake_run)

    first = execute_guarded_action(db, action="recover_runtime", cooldown_seconds=300)
    second = execute_guarded_action(db, action="recover_runtime", cooldown_seconds=300)
    incidents = list_incidents(db)

    assert first["executed"] is True
    assert first["ok"] is True
    assert second["executed"] is False
    assert second["skipped"] == "cooldown"
    assert len(calls) == 1
    assert calls[0][-2:] == ["pipeline.py", "recover-runtime"]
    assert incidents[0]["incident_type"] == "remediation_applied"


def test_auto_remediate_runs_only_known_allowlisted_playbooks(monkeypatch):
    db = _sqlite_session()
    calls = []

    class FakeResult:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return FakeResult()

    monkeypatch.setenv("HERMES_AUTOREMEDIATE", "1")
    monkeypatch.setattr("backend.services.hermes_watchdog.subprocess.run", fake_run)

    results = auto_remediate_diagnostics(
        db,
        [
            {"incident_type": "worker_stale", "evidence": {"jobs": [{"id": 1}]}},
            {
                "incident_type": "pm2_process_down",
                "evidence": {
                    "processes": [
                        {"name": "fralib", "status": "errored"},
                        {"name": "postgres", "status": "down"},
                    ]
                },
            },
            {"incident_type": "redis_unavailable", "evidence": {}},
        ],
    )

    assert len(results) == 2
    assert any(cmd[-2:] == ["pipeline.py", "recover-runtime"] for cmd in calls)
    assert ["pm2", "restart", "fralib"] in calls
    assert not any("postgres" in cmd for cmd in calls)


def test_diagnose_snapshot_flags_stale_running_jobs():
    snapshot = {
        "jobs": {
            "stale_running": [
                {
                    "id": 123,
                    "tipo": "pipeline_lead",
                    "tenant_id": 2,
                    "last_phase": "builder_renderer",
                    "heartbeat_age_seconds": 800,
                }
            ]
        },
        "payments": {"last_24h": {"errors": 0}},
        "redis": {"status": "ok"},
        "api": {"status": "ok"},
        "whatsapp": {"status": "auth_required"},
        "env": {"fralib_env": "prod"},
        "pm2": {"status": "ok", "processes": []},
    }

    incidents = diagnose_snapshot(snapshot)

    assert len(incidents) == 1
    assert incidents[0]["severity"] == "SEV2"
    assert incidents[0]["incident_type"] == "worker_stale"
    assert incidents[0]["evidence"]["jobs"][0]["id"] == 123
