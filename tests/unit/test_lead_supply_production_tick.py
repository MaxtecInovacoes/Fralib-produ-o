from backend.services.lead_supply_providers.maps import _idempotency_key_for


def test_inventory_idempotency_key_stays_stable_for_active_job():
    assert (
        _idempotency_key_for("abc123", "run999", retry_terminal=False)
        == "inventory-pipeline-abc123"
    )


def test_inventory_idempotency_key_changes_for_terminal_retry():
    assert (
        _idempotency_key_for("abc123", "run999", retry_terminal=True)
        == "inventory-pipeline-abc123-run999"
    )
