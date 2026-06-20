import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "controlled_pipeline_run.py"
SPEC = importlib.util.spec_from_file_location("controlled_pipeline_run", MODULE_PATH)
controlled_pipeline_run = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = controlled_pipeline_run
SPEC.loader.exec_module(controlled_pipeline_run)


def test_build_payload_skips_franz_by_default():
    payload = controlled_pipeline_run.build_payload(
        {"id": "lead-1", "segmento": "Academia", "cidade": "Colombo"},
        run_id="ctrl-test",
    )

    assert payload["_lead_id_existente"] == "lead-1"
    assert payload["_prompt_agent_flow"] is True
    assert payload["_controlled_test"] is True
    assert payload["_skip_franz_outreach"] is True


def test_franz_real_outreach_requires_env_token():
    try:
        controlled_pipeline_run.ensure_franz_allowed(True, env={})
    except controlled_pipeline_run.ControlledRunError as exc:
        assert "FRALIB_ALLOW_CONTROLLED_FRANZ" in str(exc)
    else:
        raise AssertionError("Franz outreach must be blocked without explicit env token")


def test_confirmation_required_for_non_dry_run():
    controlled_pipeline_run.require_confirmation(None, dry_run=True)

    try:
        controlled_pipeline_run.require_confirmation(None, dry_run=False)
    except controlled_pipeline_run.ControlledRunError as exc:
        assert "RUN_CONTROLLED_PIPELINE" in str(exc)
    else:
        raise AssertionError("production enqueue must require explicit confirmation")
