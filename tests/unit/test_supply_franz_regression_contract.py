from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_franz_reconcile_does_not_reopen_failed_permanent_jobs():
    source = _read("worker.py")
    block = source[
        source.index("def _reconcile_missing_franz_jobs") :
        source.index("def _tenant_recent_outbound_wait_seconds")
    ]

    assert "Reaberto por reconcile" not in block
    assert "status IN ('failed_permanent', 'failed_retriable')" not in block
    assert "AND j.idempotency_key = 'franz-' || l.id" in block


def test_franz_watchdog_block_is_not_pipeline_failure_loop():
    source = _read("worker.py")
    block = source[
        source.index("if not franz_output or not franz_output.reply") :
        source.index("_prior_outbound = False")
    ]

    assert 'intent == "watchdog_blocked"' in block
    assert '"max_2_messages_without_response" in diagnostico' in block
    assert "return True, None, None" in block
    assert "Aguardando watchdog do SDR" in block
    assert '"outside_schedule" in diagnostico' in block
    assert "Fora do horario comercial do SDR" in block


def test_pipeline_failures_are_deduped_and_resolved_on_success():
    source = _read("backend/core/job_queue.py")
    success_block = source[source.index("def mark_success") : source.index("def mark_failure")]
    failure_block = source[source.index("def mark_failure") : source.index("def defer_without_attempt")]

    assert "UPDATE pipeline_failures" in success_block
    assert "resolvido = TRUE" in success_block
    assert "WHERE job_id = :id" in success_block

    assert "UPDATE pipeline_failures" in failure_block
    assert "RETURNING id" in failure_block
    assert "if existing_failure" in failure_block


def test_lead_supply_sync_recovers_caio_backlog():
    source = _read("backend/services/lead_supply_inventory.py")
    sync_block = source[source.index("def sync_supply") : source.index("def enqueue_hunter")]
    caio_block = source[source.index("def _enqueue_caio") : source.index("def _sync_caio_backlog")]

    assert "_sync_caio_backlog(" in sync_block
    assert "status IN ('raw', 'error_retry')" in source
    assert "idempotency_key=:idem" in caio_block
    assert "status IN ('failed_permanent','failed_retriable')" in caio_block


def test_pipeline_failure_retry_all_hydrates_inventory_payload():
    source = _read("backend/endpoints/falhas_endpoints.py")
    helper_block = source[
        source.index("def _hydrate_pipeline_retry_payload") :
        source.index("@router.get")
    ]
    retry_all_block = source[source.index("async def retry_all_falhas") :]

    assert 'payload["_inventory_id"]' in helper_block
    assert 'payload["_lead_id_existente"]' in helper_block
    assert "FROM lead_inventory" in helper_block
    assert "lead_supply_config" in helper_block
    assert "_hydrate_pipeline_retry_payload(db, tenant_id, payload, lead_id)" in retry_all_block


def test_sdr_save_and_send_preserves_generated_outgoing_message():
    source = _read("backend/agents/sdr_langgraph/agent.py")
    block = source[
        source.index("def node_save_and_send") :
        source.index("def build_sdr_graph")
    ]

    assert 'state.get("outgoing_message", "")' in block
    assert 'state["outgoing_message"] = reply' in block
