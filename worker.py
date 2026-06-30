"""
Worker daemon do FraLib.

Faz loop: pega job -> processa -> heartbeat -> sucesso/falha. Roda em paralelo
ao servidor web (PM2 sobe N instancias). SELECT FOR UPDATE SKIP LOCKED garante
que cada job e pego por exatamente um worker.

Tipos de job suportados:
    pipeline_lead          -> roda o pipeline completo para 1 lead
    franz_outreach         -> Franz/SDR envia o WhatsApp do site pronto
    lead_supply_hunter     -> abastece inventario de leads
    lead_supply_caio       -> qualifica lead bruto do inventario
    lead_production_tick   -> consome 1 lead aprovado e agenda pipeline

Configuracao por env:
    WORKER_POLL_SECONDS    intervalo entre tentativas de claim (default 3s)
    WORKER_HEARTBEAT_SECS  intervalo de heartbeat durante job (default 30s)
    WORKER_REAP_SECS       a cada N segundos roda reap_dead_workers (default 60s)
"""
import asyncio
import importlib
import json
import logging
import os
import signal
import sys
import time
import socket
import threading
from typing import Optional
from pathlib import Path

# Carrega .env ANTES de importar database (que valida DATABASE_URL no import).
from dotenv import load_dotenv
_ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=_ROOT_DIR / ".env", override=False)
load_dotenv(dotenv_path=_ROOT_DIR / "backend" / ".env", override=False)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for _rel in ("backend", "backend/core", "backend/agents", "backend/endpoints", "backend/services"):
    sys.path.insert(0, os.path.join(BASE_DIR, _rel))

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
JOB_MAX_SECS = int(os.environ.get("WORKER_JOB_MAX_SECS", "1800"))
LEAD_SUPPLY_SYNC_SECS = int(os.environ.get("LEAD_SUPPLY_SYNC_SECS", "300"))
FRANZ_RECONCILE_SECS = int(os.environ.get("FRALIB_FRANZ_RECONCILE_SECS", "300"))
FRANZ_RECONCILE_LIMIT = int(os.environ.get("FRALIB_FRANZ_RECONCILE_LIMIT", "25"))
FRANZ_OUTREACH_SPACING_SECS = int(os.environ.get("FRALIB_FRANZ_OUTREACH_SPACING_SECS", "600"))
OUTBOUND_QUEUE_PROCESS_SECS = int(os.environ.get("FRALIB_OUTBOUND_QUEUE_PROCESS_SECS", "30"))
TMP_CLEANUP_HIGH_WATERMARK = float(os.environ.get("WORKER_TMP_CLEANUP_HIGH_WATERMARK", "0.50"))
TMP_CLEANUP_CRITICAL_WATERMARK = float(os.environ.get("WORKER_TMP_CLEANUP_CRITICAL_WATERMARK", "0.80"))
WORKER_JOB_TYPES = [
    item.strip()
    for item in os.environ.get(
        "WORKER_JOB_TYPES", "pipeline_lead,pipeline_multiplos,franz_outreach,lead_supply_hunter,lead_supply_caio,lead_production_tick"
    ).split(",")
    if item.strip()
]
SDR_OUTREACH_JOB_TYPES = {"franz_outreach", "bryan_outreach"}

WORKER_ID = job_queue.generate_worker_id()
_running = True
_current_job_id = None


def _mask_db_url(url: str | None) -> str:
    if not url:
        return "unset"
    text = str(url)
    if "@" in text and "://" in text:
        prefix, suffix = text.split("://", 1)
        if "@" in suffix:
            creds, host = suffix.split("@", 1)
            if ":" in creds:
                user, _password = creds.split(":", 1)
                return f"{prefix}://{user}:***@{host}"
    return text.replace("://", "://***@") if "://" in text else text


def _startup_diagnostics() -> None:
    db_url = os.environ.get("DATABASE_URL")
    tenant_id = os.environ.get("WORKER_TENANT_ID")
    queue_name = os.environ.get("WORKER_QUEUE_NAME")
    log.info("startup env DATABASE_URL=%s", _mask_db_url(db_url))
    log.info(
        "startup filters WORKER_TENANT_ID=%s WORKER_QUEUE_NAME=%s WORKER_JOB_TYPES=%s",
        tenant_id or "unset",
        queue_name or "unset",
        ",".join(WORKER_JOB_TYPES) or "unset",
    )
    if db_url:
        log.info("startup db_host=%s", _extract_db_host(db_url))
    else:
        log.warning("startup db_host=unset DATABASE_URL ausente")


def _extract_db_host(url: str) -> str:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.hostname or "unknown"
    except Exception:
        return "unknown"


def _set_llm_job_context(job: dict) -> None:
    payload = dict(job.get("payload") or {})
    tenant_id = job.get("tenant_id")
    run_id = job.get("run_id") or payload.get("_run_id")
    job_id = job.get("id")
    for module_name in ("llm_direct", "agents.llm_direct"):
        try:
            mod = importlib.import_module(module_name)
            if hasattr(mod, "set_llm_context"):
                mod.set_llm_context(user_id=tenant_id, run_id=run_id, job_id=job_id)
            elif hasattr(mod, "set_current_user_id"):
                mod.set_current_user_id(tenant_id)
        except Exception:
            pass


def _clear_llm_job_context() -> None:
    for module_name in ("llm_direct", "agents.llm_direct"):
        try:
            mod = importlib.import_module(module_name)
            if hasattr(mod, "clear_llm_context"):
                mod.clear_llm_context()
            elif hasattr(mod, "set_current_user_id"):
                mod.set_current_user_id(None)
        except Exception:
            pass


def _notificar_feedback_job(job: dict, status: str, fase: str, mensagem: str) -> None:
    """Publish retry/final failure feedback without exposing internal stack traces."""
    try:
        from sse_endpoints import adicionar_log

        payload = job_queue.formatar_feedback_job(
            job_id=job["id"],
            status=status,
            fase=fase,
            erro_tecnico=mensagem,
            attempts=int(job.get("attempts") or 0),
            max_attempts=int(job.get("max_attempts") or 0),
        )
        adicionar_log(
            json.dumps(payload, ensure_ascii=False),
            "warning" if status == "pending" else "error",
            user_id=job.get("tenant_id"),
        )
    except Exception as exc:
        log.warning(f"feedback SSE do job {job.get('id')} falhou: {exc}")


def _sdr_quality_hold_reason(db, lead_id: str | None, tenant_id: int | None) -> str | None:
    """Return a reason when a lead was quarantined after a publication incident."""

    if not lead_id or not tenant_id:
        return None
    try:
        from sqlalchemy import text as _txt

        row = db.execute(
            _txt(
                """
                SELECT
                    COALESCE(to_jsonb(l)->>'sdr_stage', '') AS lead_stage,
                    COALESCE(to_jsonb(l)->>'status', '') AS lead_status,
                    COALESCE(to_jsonb(l)->>'erro_pipeline', '') AS erro_pipeline,
                    COALESCE(to_jsonb(l)->>'pipeline_alerta', '') AS pipeline_alerta,
                    COALESCE(li.status, '') AS inventory_status,
                    COALESCE(li.erro, '') AS inventory_error
                FROM leads l
                LEFT JOIN lead_inventory li
                  ON li.lead_id = l.id
                 AND li.tenant_id = l.user_id
                WHERE l.id = :lead_id
                  AND l.user_id = :tenant_id
                LIMIT 1
                """
            ),
            {"lead_id": lead_id, "tenant_id": tenant_id},
        ).fetchone()
    except Exception as exc:
        log.warning(f"Franz: qualidade nao verificada lead={lead_id}: {exc}")
        return None
    if not row:
        return None

    values = [str(value or "").lower() for value in row]
    if any(value.startswith("blocked_quality") for value in values):
        return "lead bloqueado por incidente de qualidade"
    if any(value == "quality_hold" for value in values):
        return "lead/inventario em quality_hold"
    joined = " ".join(values)
    if "quality incident" in joined or "wrong-niche" in joined or "generic" in joined:
        return "alerta de qualidade bloqueia SDR"
    return None


def _shutdown(signum, frame):
    global _running
    if _current_job_id:
        log.info(f"sinal {signum} recebido, aguardando job atual id={_current_job_id}")
    else:
        log.info(f"sinal {signum} recebido, encerrando")
    _running = False


signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)


def _cleanup_old_workspaces(*, max_age_hours: int = 24) -> int:
    """Remove old or incomplete Vite workspaces so /tmp cannot fill up silently."""
    import shutil as _shutil
    import time as _time

    workspace_root = os.environ.get("FRALIB_BUILDER_SANDBOX_ROOT", "/tmp/fralib_builder")
    if not os.path.isdir(workspace_root):
        return 0

    removed = 0
    now = _time.time()
    max_age_seconds = max_age_hours * 3600

    for tenant_dir in os.listdir(workspace_root):
        tenant_path = os.path.join(workspace_root, tenant_dir)
        if not os.path.isdir(tenant_path):
            continue
        try:
            for job_dir in os.listdir(tenant_path):
                job_path = os.path.join(tenant_path, job_dir)
                if not os.path.isdir(job_path):
                    continue
                try:
                    mtime = os.path.getmtime(job_path)
                    node_modules = os.path.join(job_path, "node_modules")
                    plugin_react = os.path.join(node_modules, "@vitejs", "plugin-react")
                    old = (now - mtime) > max_age_seconds
                    incomplete = os.path.isdir(node_modules) and not os.path.isdir(plugin_react)
                    if old or incomplete:
                        _shutil.rmtree(job_path, ignore_errors=True)
                        removed += 1
                        if incomplete:
                            log.warning("workspace cleanup: node_modules incompleto em %s", job_path)
                except Exception:
                    pass
        except Exception:
            pass

    if removed > 0:
        log.info("workspace cleanup: removeu %s diretorios (max_age=%sh)", removed, max_age_hours)
    return removed


def _heartbeat_loop(job_id: int, stop_event: threading.Event):
    """Roda em thread real para sobreviver a chamadas bloqueantes do pipeline."""
    while not stop_event.is_set():
        try:
            db = SessionLocal()
            try:
                job_queue.heartbeat(db, job_id)
            finally:
                db.close()
        except Exception as e:
            log.warning(f"heartbeat job {job_id} falhou: {e}")
        stop_event.wait(HEARTBEAT_SECS)


def _sync_all_lead_supply(db) -> dict:
    """Keep active lead-supply tenants moving without requiring an admin page visit."""
    if not {
        "lead_supply_hunter",
        "lead_supply_caio",
        "lead_production_tick",
    }.intersection(WORKER_JOB_TYPES):
        return {"checked": 0, "synced": 0, "skipped": "lead_supply_jobs_disabled"}

    from sqlalchemy import text as _txt
    from services import lead_supply_engine

    rows = db.execute(
        _txt(
            """
            SELECT tenant_id
            FROM lead_supply_config
            WHERE ativo = TRUE
              AND (hunter_pausado = FALSE OR producao_pausada = FALSE)
            ORDER BY tenant_id
            LIMIT 200
            """
        )
    ).fetchall()
    checked = 0
    synced = 0
    errors: list[dict[str, str]] = []
    for row in rows:
        tenant_id = int(row[0])
        checked += 1
        try:
            lead_supply_engine.sync_supply(db, tenant_id)
            synced += 1
        except Exception as exc:
            db.rollback()
            errors.append({"tenant_id": str(tenant_id), "error": str(exc)[:160]})
    return {"checked": checked, "synced": synced, "errors": errors[:5]}


def _reconcile_missing_franz_jobs(db) -> dict:
    """Enfileira sites prontos que ficaram sem job do Franz.

    O envio continua respeitando janela/guard do Franz. Aqui apenas criamos
    jobs idempotentes para leads que ja deveriam estar aguardando contato.
    """
    if "franz_outreach" not in WORKER_JOB_TYPES:
        return {"checked": 0, "enqueued": 0, "skipped": "franz_disabled"}

    from sqlalchemy import text as _txt

    rows = db.execute(
        _txt(
            """
            SELECT
                l.id,
                l.user_id,
                l.nome,
                l.cidade,
                l.segmento,
                COALESCE(NULLIF(l.telefone_whatsapp, ''), NULLIF(l.whatsapp, ''), l.telefone, '') AS whatsapp,
                l.telefone,
                COALESCE(l.rating, 0) AS rating,
                COALESCE(l.score, 0) AS score,
                COALESCE(NULLIF(l.tier, ''), 'STANDARD') AS tier,
                COALESCE(l.site_url, l.url_site, '') AS site_url
            FROM leads l
            WHERE l.status = 'concluido'
              AND COALESCE(l.sdr_stage, '') IN (
                  'pending_sdr_send',
                  'pendente_wpp',
                  'hook',
                  'sdr_enqueue_failed'
              )
              AND COALESCE(l.site_url, l.url_site, '') <> ''
              AND COALESCE(NULLIF(l.telefone_whatsapp, ''), NULLIF(l.whatsapp, ''), l.telefone, '') <> ''
              AND NOT EXISTS (
                  SELECT 1
                  FROM jobs j
                  WHERE j.tenant_id = l.user_id
                    AND j.tipo = 'franz_outreach'
                    AND j.idempotency_key = 'franz-' || l.id
                    AND j.status IN ('pending', 'running', 'completed', 'done_finished')
              )
            ORDER BY l.processado_em DESC NULLS LAST, l.criado_em DESC NULLS LAST
            LIMIT :limit
            """
        ),
        {"limit": max(1, FRANZ_RECONCILE_LIMIT)},
    ).fetchall()

    enqueued = 0
    reopened = 0
    for row in rows:
        lead_id, tenant_id, nome, cidade, segmento, whatsapp, telefone, rating, score, tier, site_url = row
        payload = {
            "nome": nome or "",
            "cidade": cidade or "",
            "segmento": segmento or "",
            "telefone": telefone or whatsapp or "",
            "whatsapp": whatsapp or telefone or "",
            "rating": float(rating or 0),
            "site_url": site_url or "",
            "score_caio": int(score or 0),
            "tier": tier or "STANDARD",
            "lead_id": str(lead_id),
            "tenant_id": int(tenant_id),
            "_reconciled": True,
        }
        idem = f"franz-{lead_id}"
        reopened_row = db.execute(
            _txt(
                """
                UPDATE jobs
                SET status = 'pending',
                    payload = CAST(:payload AS jsonb),
                    tenant_id = :tenant_id,
                    attempts = 0,
                    max_attempts = GREATEST(max_attempts, 5),
                    next_retry_at = NOW(),
                    last_phase = 'franz_reconcile',
                    last_error = 'Reaberto por reconcile: site publicado sem contato ativo',
                    worker_id = NULL,
                    worker_heartbeat = NULL
                WHERE tipo = 'franz_outreach'
                  AND idempotency_key = :idem
                  AND status IN ('failed_permanent', 'failed_retriable')
                RETURNING id
                """
            ),
            {
                "payload": json.dumps(payload),
                "tenant_id": int(tenant_id),
                "idem": idem,
            },
        ).fetchone()
        if reopened_row:
            db.commit()
            reopened += 1
            continue

        job_id = job_queue.enqueue(
            db,
            tipo="franz_outreach",
            payload=payload,
            tenant_id=int(tenant_id),
            max_attempts=5,
            idempotency_key=idem,
        )
        if job_id:
            enqueued += 1
    return {"checked": len(rows), "enqueued": enqueued, "reopened": reopened}


def _tenant_recent_outbound_wait_seconds(db, tenant_id: int | None) -> int:
    """Evita rajada de primeiro contato quando muitos jobs ficam elegiveis."""

    if not tenant_id or FRANZ_OUTREACH_SPACING_SECS <= 0:
        return 0
    from sqlalchemy import text as _txt

    row = db.execute(
        _txt(
            """
            WITH recent AS (
                SELECT MAX(criado_em::timestamp) AS last_outbound_at
                FROM interacoes
                WHERE user_id = :uid
                  AND direcao = 'saida'
                  AND criado_em ~ '^\\d{4}-\\d{2}-\\d{2}'
                  AND criado_em::timestamp >= (
                      NOW() AT TIME ZONE 'America/Sao_Paulo'
                  ) - (:spacing || ' seconds')::interval
            )
            SELECT EXTRACT(EPOCH FROM (
                (NOW() AT TIME ZONE 'America/Sao_Paulo') - last_outbound_at
            ))::int AS elapsed
            FROM recent
            """
        ),
        {"uid": int(tenant_id), "spacing": int(FRANZ_OUTREACH_SPACING_SECS)},
    ).fetchone()
    elapsed = None if not row else row[0]
    if elapsed is None:
        return 0
    return max(0, int(FRANZ_OUTREACH_SPACING_SECS) - int(elapsed))


def _normalize_outbound_jid(target: str) -> str:
    target = (target or "").strip()
    if "@" in target:
        return target
    digits = "".join(ch for ch in target if ch.isdigit())
    return f"{digits}@s.whatsapp.net" if digits else target


def _process_outbound_queue_cycle() -> dict:
    """Processa 1 mensagem automatica respeitando fila por tenant."""

    from services.outbound_queue import process_queue_once
    import requests

    meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001").rstrip("/")
    meowhats_key = os.getenv("MEOWHATS_KEY", "").strip()
    if not meowhats_key:
        return {"sent": 0, "skipped": 0, "failed": 1, "error": "MEOWHATS_KEY ausente"}

    def _send(target: str, message: str, tenant_id: int | None = None):
        if not tenant_id:
            return False
        tenant_key = f"fralib_user_{int(tenant_id)}"
        if not _dentro_do_horario(int(tenant_id)):
            log.info("outbound_queue aguardando horario tenant=%s", tenant_id)
            return None
        try:
            status = requests.get(
                f"{meowhats_url}/api/sessions/{tenant_key}/status",
                headers={"X-API-Key": meowhats_key},
                timeout=8,
            )
            if status.status_code != 200 or "connected" not in status.text.lower():
                return None
        except Exception:
            return None

        jid = _normalize_outbound_jid(target)
        if not jid:
            return False
        response = requests.post(
            f"{meowhats_url}/api/sessions/{tenant_key}/send",
            headers={"X-API-Key": meowhats_key},
            json={"jid": jid, "type": "text", "text": message},
            timeout=15,
        )
        if response.status_code != 200:
            log.warning(
                "outbound_queue send failed tenant=%s status=%s body=%s",
                tenant_id,
                response.status_code,
                (response.text or "")[:160],
            )
        return response.status_code == 200

    db = SessionLocal()
    try:
        return process_queue_once(db.get_bind(), _send)
    finally:
        db.close()


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
        from pipeline_orchestrator_service import executar_pipeline_completo, executar_pipeline_lead_existente

        try:
            if payload.get("_lead_id_existente"):
                resultado = await executar_pipeline_lead_existente(
                    payload.get("_lead_id_existente"),
                    tenant_id,
                    forcar_renovacao=bool(payload.get("_forcar_renovacao")),
                    queue_id=payload.get("queue_id"),
                    run_id=payload.get("_run_id"),
                    job_id=payload.get("_job_id"),
                    test_number=payload.get("_bryan_test_number"),
                    skip_franz_outreach=bool(payload.get("_skip_franz_outreach")),
                )
            else:
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
        from pipeline_orchestrator_service import executar_pipeline_multiplos

        try:
            resultado = await executar_pipeline_multiplos(
                payload, tenant_id, queue_id=payload.get("queue_id"),
            )
            if resultado and resultado.get("sucesso"):
                return True, None, None
            fase = (resultado or {}).get("fase") or "pipeline"
            erro = (resultado or {}).get("erro") or "Pipeline retornou sem sucesso"
            return False, fase, str(erro)
        except Exception as e:
            return False, "pipeline", str(e)

    if tipo == "lead_supply_hunter":
        try:
            from services import lead_supply_engine

            db_supply = SessionLocal()
            try:
                result = await lead_supply_engine.run_hunter_job(
                    db_supply, payload, tenant_id
                )
            finally:
                db_supply.close()
            if result.get("ok"):
                return True, None, None
            return False, "lead_supply_hunter", result.get("error") or "Hunter nao abasteceu inventario"
        except Exception as e:
            return False, "lead_supply_hunter", str(e)

    if tipo == "lead_supply_caio":
        try:
            from services import lead_supply_engine

            db_supply = SessionLocal()
            try:
                result = lead_supply_engine.run_caio_job(db_supply, payload, tenant_id)
            finally:
                db_supply.close()
            if result.get("ok"):
                return True, None, None
            return False, "lead_supply_caio", result.get("error") or "Caio nao qualificou lead"
        except Exception as e:
            return False, "lead_supply_caio", str(e)

    if tipo == "lead_production_tick":
        try:
            from services import lead_supply_engine

            db_supply = SessionLocal()
            try:
                result = lead_supply_engine.run_production_tick(
                    db_supply, payload, tenant_id
                )
            finally:
                db_supply.close()
            if result.get("ok"):
                return True, None, None
            return False, "lead_production_tick", result.get("error") or "Tick de producao falhou"
        except Exception as e:
            return False, "lead_production_tick", str(e)

    if tipo in SDR_OUTREACH_JOB_TYPES:
        # Job separado: gera mensagem + envia WhatsApp
        try:
            from sdr_langgraph import iniciar_contato, FranzInput, _dentro_do_horario
            from whatsapp_listener import is_tenant_connected, _salvar_interacao
            import httpx, re as _re, os as _os
            from sqlalchemy import text as _txt
            from services.credits_manager import plano_tem_sdr, consumir_credito_trial_entregue
            from services.sdr_gateway import (
                SdrMessageContext,
                evaluate_sdr_output,
                has_prior_outbound,
            )

            _db_plan = SessionLocal()
            try:
                _plan_row = _db_plan.execute(
                    _txt("SELECT plano, status, trial_expires_at FROM users WHERE id=:id"),
                    {"id": tenant_id},
                ).fetchone()
                _plano = ((_plan_row[0] if _plan_row else "") or "").lower()
                _status = ((_plan_row[1] if _plan_row else "") or "").lower()
                _trial_expires_at = _plan_row[2] if _plan_row else None
                if not plano_tem_sdr(_plano, _status, _trial_expires_at):
                    if payload.get("lead_id"):
                        _db_plan.execute(
                            _txt(
                                "UPDATE leads SET sdr_stage='blocked_plan' WHERE id=:id AND user_id=:uid"
                            ),
                            {"id": payload.get("lead_id"), "uid": tenant_id},
                        )
                        _db_plan.commit()
                    log.info(f"Franz: pulado por plano/status tenant={tenant_id} plano={_plano} status={_status}")
                    return True, None, None
            finally:
                _db_plan.close()

            _db_quality = SessionLocal()
            try:
                _hold_reason = _sdr_quality_hold_reason(
                    _db_quality, payload.get("lead_id"), tenant_id
                )
                if _hold_reason:
                    _db_quality.execute(
                        _txt(
                            """
                            UPDATE leads
                            SET sdr_stage='blocked_quality_incident',
                                atualizado_em=NOW()::text
                            WHERE id=:id AND user_id=:uid
                            """
                        ),
                        {"id": payload.get("lead_id"), "uid": tenant_id},
                    )
                    _db_quality.commit()
                    log.warning(
                        f"Franz: envio bloqueado por qualidade lead={payload.get('nome')} "
                        f"reason={_hold_reason}"
                    )
                    return True, None, None
            finally:
                _db_quality.close()

            franz_input = FranzInput(
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
            franz_output = iniciar_contato(franz_input, user_id=tenant_id)

            if not franz_output or not franz_output.reply or not franz_output.reply.strip():
                intent = (getattr(franz_output, "intent", "") or "").lower()
                next_stage = (getattr(franz_output, "next_stage", "") or "").lower()
                proximo_passo = (getattr(franz_output, "proximo_passo", "") or "").lower()
                diagnostico = f"{intent} {next_stage} {proximo_passo}"

                if (
                    intent == "fila"
                    or "horario" in diagnostico
                    or "horário" in diagnostico
                    or "aguardando" in diagnostico
                ):
                    log.info(f"Franz: reply vazio por agenda — lead {payload.get('nome')}")
                    return False, "franz_schedule", "Fora do horario do SDR"

                if (
                    intent == "skip_duplicado"
                    or "duplicado" in diagnostico
                    or "ja contatado" in diagnostico
                    or "já contatado" in diagnostico
                ):
                    log.info(f"Franz: reply vazio por lead duplicado — lead {payload.get('nome')}")
                    return True, None, None

                log.warning(
                    f"Franz: reply vazio inesperado — lead={payload.get('nome')} intent={intent or 'n/a'}"
                )
                return False, "franz", "Franz retornou reply vazio"

            _prior_outbound = False
            if payload.get("lead_id"):
                _db_guard = SessionLocal()
                try:
                    _prior_outbound = has_prior_outbound(
                        _db_guard, payload.get("lead_id"), tenant_id
                    )
                finally:
                    _db_guard.close()
            _guard = evaluate_sdr_output(
                SdrMessageContext(
                    tenant_id=tenant_id,
                    lead_id=payload.get("lead_id"),
                    lead_name=payload.get("nome", ""),
                    lead_segment=payload.get("segmento", ""),
                    stage=payload.get("sdr_stage") or "pendente_wpp",
                    next_stage=getattr(franz_output, "next_stage", "") or "",
                    message=franz_output.reply,
                    site_url=payload.get("site_url", ""),
                    prior_outbound=_prior_outbound,
                    direction="outbound",
                    plan_allows_sdr=True,
                    whatsapp_connected=True,
                    within_schedule=True,
                    site_ready=bool(payload.get("site_url")),
                )
            )
            if not _guard.allowed:
                log.warning(
                    f"Franz: envio bloqueado pelo guard lead={payload.get('nome')} "
                    f"code={_guard.code} reason={_guard.reason}"
                )
                if _guard.action == "defer":
                    fase = "franz_schedule" if _guard.code == "outside_schedule" else "franz"
                    return False, fase, _guard.reason
                return False, "franz_guard", _guard.reason

            tel = (payload.get("whatsapp") or payload.get("telefone") or "").strip()
            tel = _re.sub(r'\D', '', tel)
            if not tel.startswith('55'):
                tel = '55' + tel

            test_number = str(payload.get("_bryan_test_number") or _os.getenv("BRYAN_TEST_NUMBER", "")).strip()
            if test_number:
                test_number = _re.sub(r'\D', '', test_number)
                if not test_number.startswith('55'):
                    test_number = '55' + test_number
                tel = test_number

            if not payload.get("lead_id"):
                return False, "franz", "lead_id ausente para enfileirar primeiro contato"

            _db_queue = SessionLocal()
            try:
                from services.outbound_queue import enqueue_outbound

                enqueue_outbound(
                    engine=_db_queue.get_bind(),
                    tenant_id=int(tenant_id),
                    lead_id=payload.get("lead_id"),
                    phone=tel,
                    message=franz_output.reply,
                    source="franz_outreach",
                    priority=10,
                )
                log.info(
                    "Franz: primeiro contato enfileirado tenant=%s lead=%s",
                    tenant_id,
                    payload.get("nome"),
                )
                return True, None, None
            finally:
                _db_queue.close()
        except Exception as e:
            return False, "franz", str(e)

    return False, "desconhecido", f"tipo de job nao reconhecido: {tipo}"


async def _process_one(job: dict) -> None:
    global _current_job_id
    job_id = job["id"]
    payload = dict(job.get("payload") or {})
    payload.setdefault("_job_id", job_id)
    if job.get("run_id"):
        payload.setdefault("_run_id", job.get("run_id"))
    job["payload"] = payload
    trace_id = (job.get("payload") or {}).get("trace_id") or f"job-{job_id}"
    _current_job_id = job_id
    _set_llm_job_context(job)
    log.info(f"[{trace_id}] job {job_id} ({job['tipo']}) tenant={job['tenant_id']} attempt={job['attempts']}/{job['max_attempts']}")

    stop_event = threading.Event()
    hb_thread = threading.Thread(
        target=_heartbeat_loop,
        args=(job_id, stop_event),
        daemon=True,
        name=f"job-heartbeat-{job_id}",
    )
    hb_thread.start()

    try:
        try:
            sucesso, fase, mensagem = await asyncio.wait_for(_executar_job(job), timeout=JOB_MAX_SECS)
        except asyncio.TimeoutError:
            sucesso, fase, mensagem = False, "worker_timeout", f"job excedeu timeout de {JOB_MAX_SECS}s"
        except Exception as exc:
            sucesso, fase, mensagem = False, "worker_exception", str(exc)
    finally:
        stop_event.set()
        hb_thread.join(timeout=5)
        _current_job_id = None
        _clear_llm_job_context()

    db = SessionLocal()
    try:
        if sucesso:
            job_queue.mark_success(db, job_id)
            try:
                from services import lead_supply_engine
                lead_supply_engine.handle_pipeline_job_finished(
                    db, job, success=True, job_status="completed"
                )
            except Exception as _supply_done_err:
                log.warning(f"lead_supply finalizacao sucesso falhou: {_supply_done_err}")
            log.info(f"[{trace_id}] job {job_id} concluido")
        else:
            fase = job_queue.normalizar_fase_falha(fase, mensagem or "")
            # Degradação graceful: se foi rate limit ou budget, re-enfileira com delay inteligente
            _msg_lower = (mensagem or "").lower()
            is_rate_limit = "rate limit" in _msg_lower or "limite de uso" in _msg_lower or "429" in _msg_lower
            is_budget = "budget" in _msg_lower or "limite diário" in _msg_lower or "tokens esgotado" in _msg_lower
            is_schedule_wait = "fora do horario" in _msg_lower or "fora do horário" in _msg_lower
            is_whatsapp_wait = (
                "whatsapp não conectado" in _msg_lower
                or "whatsapp nao conectado" in _msg_lower
                or "wpp não conectado" in _msg_lower
                or "wpp nao conectado" in _msg_lower
            )
            is_no_leads = (
                "nenhum lead" in _msg_lower
                or "todos os leads" in _msg_lower
                or "duplicata" in _msg_lower
                or "sem leads" in _msg_lower
            )

            if is_schedule_wait or is_whatsapp_wait:
                delay = 1800 if is_schedule_wait else 300
                reason = "SDR fora do horario" if is_schedule_wait else "WhatsApp desconectado"
                log.warning(f"[{trace_id}] job {job_id} {reason} — adiando sem consumir tentativa por {delay}s")
                status = job_queue.defer_without_attempt(
                    db,
                    job_id,
                    reason=f"{reason} — retry em {delay}s",
                    fase=fase,
                    delay_seconds=delay,
                )
            elif is_rate_limit:
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
                log.warning(f"[{trace_id}] job {job_id} rate-limited — adiando sem consumir tentativa por {delay}s")
                status = job_queue.defer_without_attempt(
                    db,
                    job_id,
                    reason=f"Rate limit — retry em {delay}s",
                    fase=fase or "pipeline",
                    delay_seconds=delay,
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
            elif is_no_leads:
                status = job_queue.mark_failure(
                    db, job_id, error=mensagem or "sem leads disponiveis", fase=fase,
                    retriable=False,
                    lead_nome=(job["payload"] or {}).get("nome"),
                )
            else:
                status = job_queue.mark_failure(
                    db, job_id, error=mensagem or "erro desconhecido", fase=fase,
                    retriable=True,
                    lead_nome=(job["payload"] or {}).get("nome"),
                )
            try:
                from services import lead_supply_engine
                lead_supply_engine.handle_pipeline_job_finished(
                    db,
                    job,
                    success=False,
                    job_status=status,
                    fase=fase,
                    mensagem=mensagem or "erro desconhecido",
                )
            except Exception as _supply_fail_err:
                log.warning(f"lead_supply finalizacao erro falhou: {_supply_fail_err}")
            log.warning(f"[{trace_id}] job {job_id} -> {status} (fase={fase}): {mensagem}")
            _notificar_feedback_job(job, status, fase, mensagem or "erro desconhecido")
    except Exception as e:
        log.error(f"erro ao marcar resultado do job {job_id}: {e}")
    finally:
        db.close()


async def _main_loop():
    log.info(f"worker iniciado id={WORKER_ID} poll={POLL_SECONDS}s tipos={WORKER_JOB_TYPES}")
    last_reap = 0.0
    last_ckpt_reap = 0.0
    last_poll_log = 0.0
    last_supply_sync = 0.0
    last_franz_reconcile = 0.0
    last_outbound_queue = 0.0

    while _running:
        now = time.time()
        if now - last_poll_log >= POLL_SECONDS:
            log.info(f"Worker polling... id={WORKER_ID}")
            last_poll_log = now

        # Sprint 14.9: cleanup de workspaces Vite antigos (>24h) ou disco >80%
        # Evita que /tmp/fralib_builder fique com 3.5G+ de workspaces
        # orfaos que enchem o disco e quebram o pipeline com Errno 28.
        if now - last_reap >= REAP_SECS:
            try:
                _cleanup_old_workspaces(max_age_hours=24)
            except Exception as _ws_exc:
                log.warning(f"workspace cleanup falhou: {_ws_exc}")

        # Cleanup por espaco em disco: se /tmp passar do watermark, limpa workspaces recentes.
        if now - last_reap >= REAP_SECS:
            try:
                import shutil as _shutil
                result = _shutil.disk_usage("/tmp")
                if result.total > 0:
                    pct = result.used / result.total
                    if pct > TMP_CLEANUP_CRITICAL_WATERMARK:
                        n = _cleanup_old_workspaces(max_age_hours=0)
                        log.warning(
                            "disco /tmp em %.0f%%: limpou %s workspaces (critical %.0f%%)",
                            pct * 100,
                            n,
                            TMP_CLEANUP_CRITICAL_WATERMARK * 100,
                        )
                    elif pct > TMP_CLEANUP_HIGH_WATERMARK:
                        n = _cleanup_old_workspaces(max_age_hours=1)
                        log.warning(
                            "disco /tmp em %.0f%%: limpou %s workspaces (high %.0f%%)",
                            pct * 100,
                            n,
                            TMP_CLEANUP_HIGH_WATERMARK * 100,
                        )
            except Exception as _disk_exc:
                pass
        if now - last_reap >= REAP_SECS:
            try:
                db = SessionLocal()
                try:
                    n = job_queue.reap_dead_workers(db)
                    spans_reaped = job_queue.reap_stale_spans(db)
                    finalized = job_queue.finalize_exhausted_jobs(db)
                    try:
                        from services import lead_supply_engine
                        inventory_reap = lead_supply_engine.reap_stale_inventory_locks(
                            db,
                            apply=True,
                            limit=50,
                        )
                    except Exception as inv_exc:
                        inventory_reap = {"error": str(inv_exc)}
                    if n:
                        log.warning(f"reaper ressuscitou {n} jobs travados")
                    if spans_reaped:
                        log.warning(f"reaper finalizou {spans_reaped} spans sem finalizacao")
                    if finalized:
                        log.warning(f"reaper finalizou {finalized} jobs sem tentativas")
                    if inventory_reap.get("actions"):
                        log.warning(
                            "reaper reconciliou %s lock(s) vencidos de inventario",
                            len(inventory_reap["actions"]),
                        )
                finally:
                    db.close()
            except Exception as e:
                log.warning(f"reaper falhou: {e}")
            last_reap = now

        # Sincroniza abastecimento/producao para todos os tenants ativos.
        if LEAD_SUPPLY_SYNC_SECS > 0 and now - last_supply_sync >= LEAD_SUPPLY_SYNC_SECS:
            try:
                db = SessionLocal()
                try:
                    supply_sync = _sync_all_lead_supply(db)
                    if supply_sync.get("synced") or supply_sync.get("errors"):
                        log.info(
                            "lead_supply sync global checked=%s synced=%s errors=%s",
                            supply_sync.get("checked", 0),
                            supply_sync.get("synced", 0),
                            len(supply_sync.get("errors") or []),
                        )
                finally:
                    db.close()
            except Exception as e:
                log.warning(f"lead_supply sync global falhou: {e}")
            last_supply_sync = now

        # Garante que site pronto sem contato tenha job do Franz.
        if FRANZ_RECONCILE_SECS > 0 and now - last_franz_reconcile >= FRANZ_RECONCILE_SECS:
            try:
                db = SessionLocal()
                try:
                    franz_sync = _reconcile_missing_franz_jobs(db)
                    if franz_sync.get("enqueued"):
                        log.warning(
                            "franz reconcile enfileirou %s site(s) sem contato",
                            franz_sync.get("enqueued", 0),
                        )
                finally:
                    db.close()
            except Exception as e:
                log.warning(f"franz reconcile falhou: {e}")
            last_franz_reconcile = now

        if (
            "franz_outreach" in WORKER_JOB_TYPES
            and OUTBOUND_QUEUE_PROCESS_SECS > 0
            and now - last_outbound_queue >= OUTBOUND_QUEUE_PROCESS_SECS
        ):
            try:
                queue_result = _process_outbound_queue_cycle()
                if queue_result.get("sent") or queue_result.get("failed") or queue_result.get("waiting_sec"):
                    log.info("outbound_queue cycle: %s", queue_result)
            except Exception as e:
                log.warning(f"outbound_queue cycle falhou: {e}")
            last_outbound_queue = now

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
                job = job_queue.claim_next(db, WORKER_ID, tipos=WORKER_JOB_TYPES)
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
    def _health_gate() -> None:
        # Fail-fast: se DB cair, worker não deve consumir fila.
        db = SessionLocal()
        db.close()
        # Dependências de runtime: apenas aviso, não bloqueia startup.
        for host, port in [("127.0.0.1", 3001)]:
            try:
                with socket.create_connection((host, port), timeout=2):
                    pass
            except OSError:
                log.warning(f"health-gate: dependência indisponível em {host}:{port}")

    _startup_diagnostics()
    log.info("worker boot pre-db-init pid=%s cwd=%s", os.getpid(), os.getcwd())
    try:
        log.info("worker database init starting")
        db_ready = inicializar_database()
        if db_ready is False:
            log.warning("worker database init skipped/timeout")
        else:
            log.info("worker database init complete")
    except Exception as e:
        log.warning(f"inicializar_database falhou (pode ja estar inicializado): {e}")
    _health_gate()

    asyncio.run(_main_loop())
