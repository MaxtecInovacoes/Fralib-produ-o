"""
Worker daemon do FraLib.

Faz loop: pega job -> processa -> heartbeat -> sucesso/falha. Roda em paralelo
ao servidor web (PM2 sobe N instancias). SELECT FOR UPDATE SKIP LOCKED garante
que cada job e pego por exatamente um worker.

Tipos de job suportados:
    pipeline_lead     -> roda o pipeline completo para 1 lead (config no payload)

Configuracao por env:
    WORKER_POLL_SECONDS    intervalo entre tentativas de claim (default 3s)
    WORKER_HEARTBEAT_SECS  intervalo de heartbeat durante job (default 30s)
    WORKER_REAP_SECS       a cada N segundos roda reap_dead_workers (default 60s)
"""
import asyncio
import logging
import os
import signal
import sys
import time
from typing import Optional

# Carrega .env ANTES de importar database (que valida DATABASE_URL no import).
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, '/root/fralib/backend')
sys.path.insert(0, '/root/fralib/backend/core')
sys.path.insert(0, '/root/fralib/backend/agents')
sys.path.insert(0, '/root/fralib/backend/endpoints')

# Em Windows local, esses paths nao existem mas os imports funcionam pelos
# sys.path do server.py. Em prod sempre /root/fralib.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'agents'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'endpoints'))

from database import SessionLocal, inicializar_database
import job_queue

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [worker] %(levelname)s %(message)s',
)
log = logging.getLogger("fralib.worker")

POLL_SECONDS = int(os.environ.get("WORKER_POLL_SECONDS", "3"))
HEARTBEAT_SECS = int(os.environ.get("WORKER_HEARTBEAT_SECS", "30"))
REAP_SECS = int(os.environ.get("WORKER_REAP_SECS", "60"))

WORKER_ID = job_queue.generate_worker_id()
_running = True


def _shutdown(signum, frame):
    global _running
    log.info(f"sinal {signum} recebido, encerrando apos job atual")
    _running = False


signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)


async def _heartbeat_loop(job_id: int, stop_event: asyncio.Event):
    """Roda em paralelo ao processamento do job, batendo heartbeat ate parar."""
    while not stop_event.is_set():
        try:
            db = SessionLocal()
            try:
                job_queue.heartbeat(db, job_id)
            finally:
                db.close()
        except Exception as e:
            log.warning(f"heartbeat job {job_id} falhou: {e}")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=HEARTBEAT_SECS)
        except asyncio.TimeoutError:
            pass


async def _executar_job(job: dict) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Executa o job de acordo com seu tipo. Retorna (sucesso, fase_em_erro, mensagem_erro).
    Fase_em_erro ajuda a montar mensagem amigavel.
    """
    tipo = job["tipo"]
    payload = job["payload"] or {}
    tenant_id = job["tenant_id"]

    if tipo == "pipeline_lead":
        # Import tardio: evita carregar todo o pipeline em workers idle.
        from pipeline_endpoints import executar_pipeline_completo

        try:
            resultado = await executar_pipeline_completo(
                payload, tenant_id, queue_id=payload.get("queue_id"),
            )
            if resultado and resultado.get("sucesso"):
                return True, None, None
            fase = (resultado or {}).get("fase") or "pipeline"
            erro = (resultado or {}).get("erro") or "Pipeline retornou sem sucesso"
            return False, fase, str(erro)
        except Exception as e:
            return False, "pipeline", str(e)

    if tipo == "pipeline_multiplos":
        # Executa N tentativas ate atingir quantidade_alvo (compat com fluxo antigo).
        from pipeline_endpoints import executar_pipeline_multiplos

        try:
            await executar_pipeline_multiplos(
                payload, tenant_id, queue_id=payload.get("queue_id"),
            )
            return True, None, None
        except Exception as e:
            return False, "pipeline", str(e)

    return False, "desconhecido", f"tipo de job nao reconhecido: {tipo}"


async def _process_one(job: dict) -> None:
    job_id = job["id"]
    log.info(f"job {job_id} ({job['tipo']}) tenant={job['tenant_id']} attempt={job['attempts']}/{job['max_attempts']}")

    stop_event = asyncio.Event()
    hb_task = asyncio.create_task(_heartbeat_loop(job_id, stop_event))

    try:
        sucesso, fase, mensagem = await _executar_job(job)
    finally:
        stop_event.set()
        try:
            await asyncio.wait_for(hb_task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass

    db = SessionLocal()
    try:
        if sucesso:
            job_queue.mark_success(db, job_id)
            log.info(f"job {job_id} concluido")
        else:
            # Degradação graceful: se foi rate limit, re-enfileira com delay maior
            is_rate_limit = mensagem and ("rate limit" in mensagem.lower() or "limite de uso" in mensagem.lower())
            if is_rate_limit:
                # Espera proporcional à tentativa: 60s, 120s, 180s...
                delay = 60 * job["attempts"]
                log.warning(f"job {job_id} rate-limited — re-enfileirando com delay {delay}s")
                status = job_queue.mark_failure(
                    db, job_id, error=f"Rate limit — retry em {delay}s", fase=fase,
                    retriable=True, delay_seconds=delay,
                    lead_nome=(job["payload"] or {}).get("nome"),
                )
            else:
                status = job_queue.mark_failure(
                    db, job_id, error=mensagem or "erro desconhecido", fase=fase,
                    retriable=True,
                    lead_nome=(job["payload"] or {}).get("nome"),
                )
            log.warning(f"job {job_id} -> {status} (fase={fase}): {mensagem}")
    except Exception as e:
        log.error(f"erro ao marcar resultado do job {job_id}: {e}")
    finally:
        db.close()


async def _main_loop():
    log.info(f"worker iniciado id={WORKER_ID} poll={POLL_SECONDS}s")
    last_reap = 0.0
    last_ckpt_reap = 0.0

    while _running:
        # Reap periodico de workers mortos
        now = time.time()
        if now - last_reap >= REAP_SECS:
            try:
                db = SessionLocal()
                try:
                    n = job_queue.reap_dead_workers(db)
                    if n:
                        log.warning(f"reaper ressuscitou {n} jobs travados")
                finally:
                    db.close()
            except Exception as e:
                log.warning(f"reaper falhou: {e}")
            last_reap = now

        # Reap periodico de checkpoints expirados (a cada 1h)
        if now - last_ckpt_reap >= 3600:
            try:
                from agents.pipeline_checkpoint import limpar_checkpoints_expirados
                limpar_checkpoints_expirados(max_age_hours=24)
            except Exception as e:
                log.warning(f"checkpoint reaper falhou: {e}")
            last_ckpt_reap = now

        # Tenta pegar proximo job
        try:
            db = SessionLocal()
            try:
                job = job_queue.claim_next(db, WORKER_ID, tipos=["pipeline_lead", "pipeline_multiplos"])
            finally:
                db.close()
        except Exception as e:
            log.error(f"claim_next falhou: {e}")
            await asyncio.sleep(POLL_SECONDS)
            continue

        if job is None:
            await asyncio.sleep(POLL_SECONDS)
            continue

        try:
            await _process_one(job)
        except Exception as e:
            log.exception(f"erro inesperado processando job: {e}")

    log.info("worker encerrado")


if __name__ == "__main__":
    try:
        inicializar_database()
    except Exception as e:
        log.warning(f"inicializar_database falhou (pode ja estar inicializado): {e}")

    asyncio.run(_main_loop())
