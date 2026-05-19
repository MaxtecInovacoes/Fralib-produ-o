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
sys.path.insert(0, '/root/fralib/backend/services')

# Em Windows local, esses paths nao existem mas os imports funcionam pelos
# sys.path do server.py. Em prod sempre /root/fralib.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'agents'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'endpoints'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'services'))

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
_current_job_id = None


def _shutdown(signum, frame):
    global _running
    if _current_job_id:
        log.info(f"sinal {signum} recebido, encerrando apos job atual id={_current_job_id}")
        try:
            db = SessionLocal()
            try:
                job_queue.mark_interrupted(db, _current_job_id, "worker_shutdown")
            finally:
                db.close()
        except Exception as e:
            log.warning(f"nao foi possivel marcar job interrompido: {e}")
    else:
        log.info(f"sinal {signum} recebido, encerrando")
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
    payload = dict(job["payload"] or {})
    tenant_id = job["tenant_id"]
    payload.setdefault("trace_id", f"job-{job['id']}")

    if tipo == "pipeline_lead":
        # Import tardio: evita carregar todo o pipeline em workers idle.
        from pipeline_endpoints import executar_pipeline_completo

        try:
            resultado = await executar_pipeline_completo(
                payload, tenant_id, queue_id=payload.get("queue_id"),
                resume_from_phase=job.get("last_phase") or 0,
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

    if tipo == "bryan_outreach":
        # Job separado: gera mensagem + envia WhatsApp
        try:
            from bryan import iniciar_contato, BryanInput
            from whatsapp_listener import is_tenant_connected
            import httpx, re as _re, os as _os

            bryan_input = BryanInput(
                nome=payload.get("nome", ""),
                cidade=payload.get("cidade", ""),
                segmento=payload.get("segmento", ""),
                telefone=payload.get("telefone", ""),
                whatsapp=payload.get("whatsapp", ""),
                rating=payload.get("rating", 0.0),
                site_url=payload.get("site_url", ""),
                score_caio=payload.get("score_caio", 0),
                tier=payload.get("tier", "STANDARD"),
                proof=payload.get("proof"),
                concorrentes=payload.get("concorrentes"),
            )
            bryan_output = iniciar_contato(bryan_input, user_id=tenant_id)

            if not bryan_output or not bryan_output.reply or not bryan_output.reply.strip():
                log.info(f"Bryan: reply vazio (fora do horário?) — lead {payload.get('nome')}")
                return True, None, None  # Não é erro, só fora do horário

            # Enviar via WhatsApp
            _tenant_key = f"fralib_user_{tenant_id}"
            if not is_tenant_connected(_tenant_key):
                log.warning(f"Bryan: WPP não conectado para tenant {tenant_id}")
                return False, "bryan", "WhatsApp não conectado"

            meowhats_url = _os.getenv("MEOWHATS_URL", "http://localhost:3001")
            meowhats_key = _os.getenv("MEOWHATS_KEY", "")
            if not meowhats_key:
                return False, "bryan", "MEOWHATS_KEY ausente"

            tel = (payload.get("whatsapp") or payload.get("telefone") or "").strip()
            tel = _re.sub(r'\D', '', tel)
            if not tel.startswith('55'):
                tel = '55' + tel
            jid = f"{tel}@s.whatsapp.net"

            test_number = _os.getenv("BRYAN_TEST_NUMBER", "")
            if test_number:
                jid = f"{test_number}@s.whatsapp.net"

            with httpx.Client(timeout=10) as c:
                r = c.post(
                    f"{meowhats_url}/api/sessions/{_tenant_key}/send",
                    headers={"X-API-Key": meowhats_key},
                    json={"jid": jid, "type": "text", "text": bryan_output.reply}
                )
                if r.status_code == 200:
                    # Atualizar lead como contatado
                    _db_b = SessionLocal()
                    try:
                        from sqlalchemy import text as _txt
                        _db_b.execute(_txt("UPDATE leads SET sdr_stage='hook' WHERE id=:id AND user_id=:uid"),
                                      {"id": payload.get("lead_id"), "uid": tenant_id})
                        _db_b.commit()
                    finally:
                        _db_b.close()
                    log.info(f"Bryan: mensagem enviada para {tel[-4:]}*** | lead={payload.get('nome')}")
                    return True, None, None
                else:
                    return False, "bryan", f"Envio falhou: {r.text[:200]}"
        except Exception as e:
            return False, "bryan", str(e)

    return False, "desconhecido", f"tipo de job nao reconhecido: {tipo}"


async def _process_one(job: dict) -> None:
    global _current_job_id
    job_id = job["id"]
    trace_id = (job.get("payload") or {}).get("trace_id") or f"job-{job_id}"
    _current_job_id = job_id
    log.info(f"[{trace_id}] job {job_id} ({job['tipo']}) tenant={job['tenant_id']} attempt={job['attempts']}/{job['max_attempts']}")

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
        _current_job_id = None

    db = SessionLocal()
    try:
        if sucesso:
            job_queue.mark_success(db, job_id)
            log.info(f"[{trace_id}] job {job_id} concluido")
        else:
            # Degradação graceful: se foi rate limit ou budget, re-enfileira com delay inteligente
            _msg_lower = (mensagem or "").lower()
            is_rate_limit = "rate limit" in _msg_lower or "limite de uso" in _msg_lower or "429" in _msg_lower
            is_budget = "budget" in _msg_lower or "limite diário" in _msg_lower or "tokens esgotado" in _msg_lower

            if is_rate_limit:
                # Extrair cooldown real do erro (ex: "cooldown 60s" ou "resetado em: 35min")
                import re as _re_worker
                _cd_match = _re_worker.search(r'(\d+)\s*(?:min|m)', mensagem or '')
                _cd_sec_match = _re_worker.search(r'(\d+)\s*s', mensagem or '')
                if _cd_match:
                    delay = int(_cd_match.group(1)) * 60 + 60  # minutos + margem
                elif _cd_sec_match and int(_cd_sec_match.group(1)) > 30:
                    delay = int(_cd_sec_match.group(1)) + 30
                else:
                    delay = min(120 * job["attempts"], 600)  # max 10min
                log.warning(f"[{trace_id}] job {job_id} rate-limited — re-enfileirando com delay {delay}s")
                status = job_queue.mark_failure(
                    db, job_id, error=f"Rate limit — retry em {delay}s", fase=fase,
                    retriable=True, delay_seconds=delay,
                    lead_nome=(job["payload"] or {}).get("nome"),
                )
            elif is_budget:
                # Budget esgotado — delay longo (1h), não ficar tentando
                delay = 3600
                log.warning(f"[{trace_id}] job {job_id} budget esgotado — retry em {delay}s")
                status = job_queue.mark_failure(
                    db, job_id, error=f"Budget esgotado — retry em 1h", fase=fase,
                    retriable=True, delay_seconds=delay,
                    lead_nome=(job["payload"] or {}).get("nome"),
                )
            else:
                status = job_queue.mark_failure(
                    db, job_id, error=mensagem or "erro desconhecido", fase=fase,
                    retriable=True,
                    lead_nome=(job["payload"] or {}).get("nome"),
                )
            log.warning(f"[{trace_id}] job {job_id} -> {status} (fase={fase}): {mensagem}")
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
                job = job_queue.claim_next(db, WORKER_ID, tipos=["pipeline_lead", "pipeline_multiplos", "bryan_outreach"])
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
