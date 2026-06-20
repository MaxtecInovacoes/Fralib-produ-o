"""Small helpers extracted from the pipeline orchestrator.

This module keeps the orchestrator focused on control flow while preserving the
current behavior and logging contract.
"""

from __future__ import annotations

from typing import Any


def log_legacy_queue_id(queue_id: int | None, logger) -> None:
    """Keep the legacy queue_id contract isolated in one place."""
    if queue_id:
        logger.info("[Pipeline] queue_id legado ignorado; jobs e checkpoints sao canonicos")


def build_existing_lead_pipeline_config(
    *,
    segmento: str,
    cidade: str,
    queue_id: int | None,
    forcar_renovacao: bool,
    run_id: str,
    job_id: int | str | None,
    test_number: str | None,
    skip_franz_outreach: bool,
) -> dict[str, Any]:
    """Build the canonical config payload for an existing-lead pipeline run."""
    config: dict[str, Any] = {
        "segmento": segmento,
        "cidade": cidade,
        "quantidade": 1,
        "score_minimo": 0,
        "queue_id": queue_id,
        "_forcar_renovacao": bool(forcar_renovacao),
        "_run_id": run_id,
        "_job_id": job_id,
    }
    if test_number:
        config["_bryan_test_number"] = str(test_number)
    if skip_franz_outreach:
        config["_skip_franz_outreach"] = True
    return config
