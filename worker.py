"""Worker daemon — consome fila Postgres e dispara agentes.

Loop: claim_next() → run_pipeline() → mark done/failed.
"""

import asyncio
import logging
import os
import signal
import sys
import time

from backend.core.database import inicializar_database
from backend.core.db_imports import text  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("worker")


_running = True


def _shutdown(signum, frame):
    global _running
    logger.info("Sinal %s recebido, parando após próximo job", signum)
    _running = False


signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)


JOB_TIPOS = _load_job_tipos()


def _load_job_tipos() -> tuple:
    """Lê WORKER_JOB_TYPES do env (comma-separated). Fallback para hardcoded."""
    env_val = os.environ.get("WORKER_JOB_TYPES", "").strip()
    if env_val:
        return tuple(t.strip() for t in env_val.split(",") if t.strip())
    # Fallback: job types padrão (todos os tipos exceto outreach)
    return (
        "pipeline_lead",
        "lead_production_tick",
        "lead_supply_caio",
        "lead_supply_hunter",
    )


def _run_pipeline_job(db, job) -> bool:
    """pipeline_lead: roda o Manager e fecha o loop de inventário."""
    from backend.core import job_queue
    from backend.agents.manager.agent import run_pipeline, PipelineState
    from backend.services import lead_supply_engine

    payload = job["payload"] or {}
    # Hydration: se payload tem _lead_id_existente mas lead_data vazio,
    # busca os dados do lead no banco para que step_hunter não falhe com
    # "Hunter sem lead" quando o job é reprocessado sem payload completo.
    if not payload.get("lead_data"):
        _existing_id = payload.get("_lead_id_existente") or str(job.get("run_id") or "")
        if _existing_id:
            lead_row = db.execute(
                text(
                    "SELECT nome, cidade, telefone, segmento, rating, dados_completos "
                    "FROM leads WHERE id = :id LIMIT 1"
                ),
                {"id": str(_existing_id)},
            ).fetchone()
            if lead_row:
                payload = dict(payload)
                import json as _json
                _dados = lead_row[5] if lead_row[5] else {}
                if isinstance(_dados, str):
                    _dados = _json.loads(_dados) if _dados else {}
                payload["lead_data"] = {
                    "nome": lead_row[0],
                    "cidade": lead_row[1],
                    "telefone": lead_row[2],
                    "segmento": lead_row[3],
                    "rating": float(lead_row[4]) if lead_row[4] is not None else None,
                    "reviews_count": int(_dados.get("reviews_count") or _dados.get("total_avaliacoes") or len(_dados.get("reviews", []))),
                    "fotos": _dados.get("fotos", []),
                    "website": _dados.get("website", ""),
                    "whatsapp": _dados.get("whatsapp") or lead_row[2],
                    "endereco": _dados.get("endereco", ""),
                    "market_intelligence": _dados.get("market_intelligence"),
                    "descricao": _dados.get("descricao", ""),
                }
    state = PipelineState(
        tenant_id=job["tenant_id"],
        run_id=str(job.get("run_id") or payload.get("_run_id") or job["id"]),
        # Cascade: _lead_id_existente (legacy) -> lead_id (canonical) -> job_id
        lead_id=str(
            payload.get("_lead_id_existente")
            or payload.get("lead_id")
            or job["id"]
        ),
        job_id=job["id"],
        segmento=payload.get("segmento", ""),
        cidade=payload.get("cidade", ""),
        lead_data=payload.get("lead_data", {}),
    )
    final = run_pipeline(state)
    success = final.current_state == "done"
    if success:
        job_queue.mark_success(db, job["id"])
        job_status = "completed"
    else:
        logger.error(
            "PIPELINE_FAILED lead_id=%s tenant_id=%s fase=%s error=%s history=%s",
            state.lead_id, state.tenant_id, final.current_state, final.error,
            final.history[-3:] if final.history else [],
        )
        # Persiste erro estruturado no banco para dashboard/queries
        try:
            import traceback as tb_mod
            from backend.services.lead_supply_engine import log_pipeline_error
            err_step = final.error_step or final.current_state
            err_type = final.error.split(":")[0] if final.error and ": " in final.error else "PipelineError"
            log_pipeline_error(
                db, state.lead_id, state.tenant_id,
                step=err_step,
                exception_type=err_type,
                message=(final.error or "pipeline falhou"),
                traceback_str=None,  # traceback já vai no log
            )
        except Exception as log_e:
            logger.warning("Failed to persist pipeline_error_log: %s", log_e)
        job_status = job_queue.mark_failure(db, job["id"], error=final.error or "pipeline falhou")
    # Loop-closer: atualiza lead_inventory e re-arma o próximo tick.
    lead_supply_engine.handle_pipeline_job_finished(
        db,
        job,
        success=success,
        job_status=job_status,
        fase=final.current_state,
        mensagem=final.error or None,
    )
    logger.info("Job %s (pipeline_lead): %s", job["id"], "done" if success else job_status)
    return True


def _run_supply_job(db, job) -> bool:
    """lead_production_tick / lead_supply_caio / lead_supply_hunter."""
    from backend.core import job_queue
    from backend.services import lead_supply_engine

    tipo = job["tipo"]
    payload = job["payload"] or {}
    tenant_id = job["tenant_id"]
    try:
        if tipo == "lead_production_tick":
            lead_supply_engine.run_production_tick(db, payload, tenant_id)
        elif tipo == "lead_supply_caio":
            lead_supply_engine.run_caio_job(db, payload, tenant_id)
        elif tipo == "lead_supply_hunter":
            asyncio.run(lead_supply_engine.run_hunter_job(db, payload, tenant_id))
        else:
            job_queue.mark_failure(db, job["id"], error=f"tipo desconhecido: {tipo}", retriable=False)
            logger.warning("Job %s: tipo desconhecido %s", job["id"], tipo)
            return True
        job_queue.mark_success(db, job["id"])
        logger.info("Job %s (%s): done", job["id"], tipo)
    except Exception as exc:
        status = job_queue.mark_failure(db, job["id"], error=str(exc)[:1000], fase=tipo)
        logger.exception("Job %s (%s) falhou: %s -> %s", job["id"], tipo, exc, status)
    return True


def run_one() -> bool:
    """Processa 1 job. Retorna True se processou, False se fila vazia."""
    try:
        from backend.core import job_queue
        from backend.core.database import SessionLocal
        from backend.core.job_queue import generate_worker_id

        db = SessionLocal()
        worker_id = generate_worker_id()
        try:
            job = job_queue.claim_next(db, worker_id=worker_id, tipos=JOB_TIPOS)
            if not job:
                return False
            logger.info("Job claimed: %s (tipo=%s) worker=%s", job["id"], job["tipo"], worker_id)
            if job["tipo"] == "pipeline_lead":
                return _run_pipeline_job(db, job)
            return _run_supply_job(db, job)
        finally:
            db.close()
    except Exception as e:
        logger.exception("Erro processando job: %s", e)
        return False


def main() -> None:
    inicializar_database()
    logger.info("Worker started (PID %s)", os.getpid())
    poll_interval = int(os.getenv("WORKER_POLL_INTERVAL", "5"))
    while _running:
        processed = run_one()
        if not processed:
            time.sleep(poll_interval)


if __name__ == "__main__":
    main()