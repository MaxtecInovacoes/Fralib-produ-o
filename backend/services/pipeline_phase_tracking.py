"""Rastreamento de fase atual dos jobs da pipeline."""

from sqlalchemy import text


PIPELINE_PHASE_BY_NUM = {
    1: "hunter",
    2: "caio",
    3: "jina",
    4: "market_intelligence",
    5: "media",
    6: "prompt_agent",
    7: "variation",
    8: "designer",
    9: "builder_renderer",
    10: "deploy",
    11: "franz",
}


def pipeline_phase_key(fase_num: int, label: str = "") -> str:
    if int(fase_num or 0) == 6 and "arquiteto" in (label or "").lower():
        return "designer"
    return PIPELINE_PHASE_BY_NUM.get(int(fase_num or 0), f"fase_{fase_num}")


def set_pipeline_job_phase(engine, config: dict | None, tenant_id: int, fase: str, label: str = "") -> None:
    """Persiste a fase atual do job para reconstruir progresso apos refresh."""
    config = config or {}
    job_id = config.get("_job_id")
    run_id = config.get("_run_id")
    if not job_id and not run_id:
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE jobs
                SET last_phase = :fase,
                    worker_heartbeat = NOW()
                WHERE tenant_id = :tenant_id
                  AND (
                        (:job_id IS NOT NULL AND id = :job_id)
                     OR (:job_id IS NULL AND :run_id IS NOT NULL AND run_id = :run_id)
                  )
                  AND status IN ('running', 'pending', 'failed_retriable')
                """
            ),
            {
                "fase": str(fase or label or "pipeline")[:80],
                "tenant_id": tenant_id,
                "job_id": job_id,
                "run_id": run_id,
            },
        )
