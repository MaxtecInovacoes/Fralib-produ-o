import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "pipeline_harness.py"
SPEC = importlib.util.spec_from_file_location("pipeline_harness", MODULE_PATH)
pipeline_harness = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pipeline_harness
SPEC.loader.exec_module(pipeline_harness)


def test_database_url_guard_allows_only_test_or_sqlite_urls():
    assert pipeline_harness.database_url_is_safe("sqlite:///:memory:")[0] is True
    assert pipeline_harness.database_url_is_safe("postgresql://u:p@localhost/fralib_test")[0] is True
    assert pipeline_harness.database_url_is_safe("postgresql://u:p@db/fralib_db")[0] is False


def test_environment_guard_blocks_live_secret_markers():
    env = {"DATABASE_URL": "sqlite:///:memory:", "ANTHROPIC_API_KEY": "secret"}

    try:
        pipeline_harness.validate_environment(env)
    except pipeline_harness.HarnessError as exc:
        assert "ANTHROPIC_API_KEY" in str(exc)
    else:
        raise AssertionError("live key marker must block harness runs")


def test_scenario_contract_rejects_forbidden_capabilities():
    data = {
        "mode": "dry-run",
        "allowed_capabilities": ["live_llm"],
        "forbidden_capabilities": sorted(pipeline_harness.FORBIDDEN_CAPABILITIES),
        "expected_phases": ["builder_renderer"],
    }

    try:
        pipeline_harness.validate_scenario(data)
    except pipeline_harness.HarnessError as exc:
        assert "forbidden capabilities" in str(exc)
    else:
        raise AssertionError("live capability must be rejected")


def test_all_versioned_scenarios_pass_contract_with_safe_env():
    env = {"DATABASE_URL": "sqlite:///:memory:"}
    scenarios = [item["name"] for item in pipeline_harness.list_scenarios()]

    assert scenarios
    for name in scenarios:
        report = pipeline_harness.run_scenario(name, dry_run=True, env=env)
        assert report["ok"] is True, report


def test_audit_classifies_known_legacy_and_dangerous_files():
    entries = {entry["file"]: entry for entry in pipeline_harness.audit_tests()["entries"]}

    assert entries["tests/unit/test_pipeline_builders_contract.py"]["classification"] == "ATUAL"
    assert entries["scripts/vps_reconcile_mercadopago_payments.py"]["classification"] == "PERIGOSO"
    assert entries["scripts/test_sdr_bryan.py"]["classification"] in {"LEGADO_SEGURO", "PERIGOSO"}
