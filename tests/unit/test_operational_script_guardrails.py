from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_mercadopago_reconcile_blocks_live_outside_prod_and_supports_fixture():
    source = _read("scripts/vps_reconcile_mercadopago_payments.py")

    assert "FRALIB_ENV" in source
    assert "Mercado Pago live reconcile is blocked outside FRALIB_ENV=prod" in source
    assert "--fixture-json" in source
    assert "_load_fixture_payments" in source
    assert "fixture --apply is blocked outside FRALIB_ENV=prod" in source


def test_hermes_canary_record_is_prod_only():
    source = _read("scripts/hermes_canary.py")

    assert "Hermes canary --record is blocked outside FRALIB_ENV=prod" in source
    assert "record_incident" in source
    assert "pipeline.py" in source
    assert "--dry-run" in source


def test_prod_launch_validator_blocks_remote_base_url_by_default():
    source = _read("scripts/vps_validate_prod_launch.py")

    assert "def _local_base_url" in source
    assert "--allow-remote-read" in source
    assert "Remote base-url blocked" in source
    assert "http://localhost:8000" in source
