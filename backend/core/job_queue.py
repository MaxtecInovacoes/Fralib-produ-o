"""
Job queue persistente em Postgres.

Filosofia: nada de Redis/Celery por enquanto. Uma tabela `jobs` no proprio
banco com SELECT FOR UPDATE SKIP LOCKED faz o trabalho de uma fila distribuida
ate volumes na ordem de centenas de jobs/dia. Quando isso virar gargalo, dai
sim a gente troca pra Dramatiq.

Estados possiveis:
    pending           - aguardando ser pego pelo worker
    running           - em execucao (worker_heartbeat atualizado a cada 30s)
    completed         - terminou OK
    failed_retriable  - falhou mas pode tentar de novo, esperando next_retry_at
    failed_permanent  - esgotou tentativas, viu pra pipeline_failures

Crash recovery: se um worker morrer mid-job, o heartbeat para. Outro worker
(ou o reaper periodico) detecta `running` com heartbeat > 5min e devolve pra
pending. Idempotency_key garante que o mesmo trabalho nao seja enfileirado
em duplicata por dois requests concorrentes.
"""

import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy import text
from sqlalchemy.orm import Session


# Backoff exponencial em segundos: tentativa 1 -> 30s, 2 -> 2min, 3 -> 8min
_BACKOFF = [30, 120, 480]
# Franz/SDR: mais tentativas com backoff mais longo (WhatsApp instável)
_BACKOFF_BRYAN = [60, 120, 240, 480, 960]
_PIPELINE_JOB_TYPES = ("pipeline_lead", "pipeline_multiplos", "pipeline_main")
_MAX_PIPELINES_GLOBAL = int(os.environ.get("MAX_PIPELINES_GLOBAL", "1"))


def enqueue(
    db: Session,
    tipo: str,
    payload: Dict[str, Any],
    tenant_id: Optional[int] = None,
    max_attempts: int = 3,
    idempotency_key: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
    delay_seconds: int = 0,
    priority: int = 2,
    run_id: Optional[str] = None,
) -> Optional[int]:
    """
    Enfileira um job. Retorna o job_id, ou None se ja existia um com a mesma
    idempotency_key (caso comum: dois requests concorrentes pro mesmo lead).

    Priority: 1=Pro (alta), 2=Starter (normal), 3=Trial (baixa).
    """
    next_retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
    try:
        row = db.execute(
            text("""
            INSERT INTO jobs (tipo, payload, tenant_id, max_attempts,
                              idempotency_key, checkpoint_id, next_retry_at, priority, run_id)
            VALUES (:tipo, CAST(:payload AS jsonb), :tenant_id, :max_attempts,
                    :idem, :ckpt, :next_retry_at, :priority, :run_id)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING id
        """),
            {
                "tipo": tipo,
                "payload": json.dumps(payload),
                "tenant_id": tenant_id,
                "max_attempts": max_attempts,
                "idem": idempotency_key,
                "ckpt": checkpoint_id,
                "next_retry_at": next_retry_at,
                "priority": priority,
                "run_id": run_id,
            },
        ).fetchone()
        db.commit()
        return row[0] if row else None
    except Exception as e:
        db.rollback()
        raise


def claim_next(
    db: Session, worker_id: str, tipos: Optional[list] = None
) -> Optional[Dict[str, Any]]:
    """
    Pega o proximo job disponivel atomicamente. Retorna dict ou None se nao
    houver nada elegivel.

    SKIP LOCKED garante que dois workers concorrentes pegam jobs diferentes
    sem precisar de lock global.
    """
    filtro_tipo = ""
    params: Dict[str, Any] = {"worker_id": worker_id}
    if tipos:
        filtro_tipo = "AND tipo = ANY(:tipos)"
        params["tipos"] = tipos
    filtro_global = ""
    if _MAX_PIPELINES_GLOBAL > 0:
        filtro_global = """
              AND NOT (
                tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main')
                AND (
                    SELECT COUNT(*) FROM jobs running_global
                    WHERE running_global.status = 'running'
                      AND running_global.tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main')
                ) >= :max_pipelines_global
              )
        """
        params["max_pipelines_global"] = _MAX_PIPELINES_GLOBAL

    row = db.execute(
        text(f"""
        WITH claimed AS (
            SELECT id FROM jobs
            WHERE status = 'pending'
              AND attempts < max_attempts
              AND next_retry_at <= NOW() {filtro_tipo}
              {filtro_global}
              AND NOT (
                tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main')
                AND EXISTS (
                    SELECT 1 FROM jobs running
                    WHERE running.tenant_id = jobs.tenant_id
                      AND running.status = 'running'
                      AND running.tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main')
                )
              )
            ORDER BY
                CASE WHEN tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main') THEN 0 ELSE 1 END,
                priority ASC,
                COALESCE((
                    SELECT MAX(COALESCE(done.concluido_em, done.iniciado_em, done.criado_em))
                    FROM jobs done
                    WHERE done.tenant_id = jobs.tenant_id
                      AND done.status IN ('completed', 'failed_permanent')
                ), TIMESTAMP 'epoch') ASC,
                next_retry_at ASC,
                id ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        UPDATE jobs
        SET status = 'running',
            attempts = attempts + 1,
            iniciado_em = NOW(),
            worker_id = :worker_id,
            worker_heartbeat = NOW()
        FROM claimed
        WHERE jobs.id = claimed.id
        RETURNING jobs.id, jobs.tipo, jobs.payload, jobs.tenant_id,
                  jobs.attempts, jobs.max_attempts, jobs.checkpoint_id, jobs.last_phase,
                  jobs.run_id
    """),
        params,
    ).fetchone()
    db.commit()

    if not row:
        return None
    return {
        "id": row[0],
        "tipo": row[1],
        "payload": row[2] if isinstance(row[2], dict) else json.loads(row[2] or "{}"),
        "tenant_id": row[3],
        "attempts": row[4],
        "max_attempts": row[5],
        "checkpoint_id": row[6],
        "last_phase": row[7],
        "run_id": row[8],
    }


def heartbeat(db: Session, job_id: int) -> None:
    """Worker chama isso a cada 30s pra dizer que ainda esta vivo."""
    db.execute(
        text("UPDATE jobs SET worker_heartbeat = NOW() WHERE id = :id"), {"id": job_id}
    )
    db.commit()


def mark_success(db: Session, job_id: int) -> None:
    db.execute(
        text("""
        UPDATE jobs
        SET status = 'completed',
            concluido_em = NOW(),
            last_error = NULL,
            llm_tokens_used = COALESCE((
                SELECT SUM(input_tokens + output_tokens + cache_read_tokens + cache_created_tokens)
                FROM llm_budget_ledger
                WHERE job_id = jobs.id
                   OR (job_id IS NULL AND run_id = jobs.run_id)
            ), llm_tokens_used, 0),
            llm_cost_estimate = COALESCE((
                SELECT SUM(cost_usd)
                FROM llm_budget_ledger
                WHERE job_id = jobs.id
                   OR (job_id IS NULL AND run_id = jobs.run_id)
            ), llm_cost_estimate, 0)
        WHERE id = :id
    """),
        {"id": job_id},
    )
    db.commit()


def mark_interrupted(db: Session, job_id: int, reason: str = "worker_shutdown") -> None:
    """Devolve o job em execucao para pending sem consumir retry."""
    db.execute(
        text("""
        UPDATE jobs
        SET status = 'pending',
            last_error = COALESCE(last_error || ' | ', '') || :reason,
            worker_id = NULL,
            worker_heartbeat = NULL,
            next_retry_at = NOW()
        WHERE id = :id
          AND status = 'running'
    """),
        {"id": job_id, "reason": reason[:500]},
    )
    db.commit()


def mark_failure(
    db: Session,
    job_id: int,
    error: str,
    fase: Optional[str] = None,
    retriable: bool = True,
    lead_id: Optional[str] = None,
    lead_nome: Optional[str] = None,
    delay_seconds: Optional[int] = None,
) -> str:
    """
    Marca o job como falho.

    - Se retriable=True e ainda ha attempts disponiveis: agenda retry com backoff.
      Volta pra status='pending' apos next_retry_at.
    - delay_seconds: override do backoff padrao (ex: rate limit com cooldown conhecido).
    - Caso contrario: marca como failed_permanent e move pra pipeline_failures
      pra o usuario ver no dashboard.

    Retorna o status final ('pending', 'failed_retriable' ou 'failed_permanent').
    """
    job = db.execute(
        text("""
        SELECT attempts, max_attempts, tenant_id, checkpoint_id, payload
        FROM jobs WHERE id = :id
    """),
        {"id": job_id},
    ).fetchone()
    if not job:
        return "missing"

    attempts, max_attempts, tenant_id, checkpoint_id, payload = job
    payload_dict: Dict[str, Any] = {}
    if isinstance(payload, dict):
        payload_dict = payload
    elif isinstance(payload, str):
        try:
            payload_dict = json.loads(payload or "{}")
        except Exception:
            payload_dict = {}
    if not lead_id:
        lead_id = (
            payload_dict.get("_lead_id_existente")
            or payload_dict.get("lead_id")
            or payload_dict.get("_lead_id")
        )
    if not lead_nome:
        lead_nome = payload_dict.get("lead_nome") or payload_dict.get("nome")
    if lead_id and not lead_nome:
        lead_row = db.execute(
            text("SELECT nome FROM leads WHERE id = :id LIMIT 1"),
            {"id": str(lead_id)},
        ).fetchone()
        if lead_row and lead_row[0]:
            lead_nome = str(lead_row[0])
    # Determinar backoff baseado no tipo do job
    _tipo_job = None
    if payload_dict:
        _tipo_job = payload_dict.get("_job_tipo")
    # Buscar tipo do job direto da tabela se não veio no payload
    if not _tipo_job:
        _tipo_row = db.execute(
            text("SELECT tipo FROM jobs WHERE id = :id"), {"id": job_id}
        ).fetchone()
        _tipo_job = _tipo_row[0] if _tipo_row else None
    _backoff_table = (
        _BACKOFF_BRYAN
        if _tipo_job in {"franz_outreach", "bryan_outreach"}
        else _BACKOFF
    )

    pode_tentar_mais = retriable and attempts < max_attempts
    if pode_tentar_mais:
        delay = (
            delay_seconds
            if delay_seconds is not None
            else _backoff_table[min(attempts - 1, len(_backoff_table) - 1)]
        )
        db.execute(
            text("""
            UPDATE jobs
            SET status = 'pending',
                last_error = :err,
                last_phase = :fase,
                next_retry_at = NOW() + (:delay || ' seconds')::interval,
                worker_id = NULL,
                worker_heartbeat = NULL,
                llm_tokens_used = COALESCE((
                    SELECT SUM(input_tokens + output_tokens + cache_read_tokens + cache_created_tokens)
                    FROM llm_budget_ledger
                    WHERE job_id = jobs.id
                       OR (job_id IS NULL AND run_id = jobs.run_id)
                ), llm_tokens_used, 0),
                llm_cost_estimate = COALESCE((
                    SELECT SUM(cost_usd)
                    FROM llm_budget_ledger
                    WHERE job_id = jobs.id
                       OR (job_id IS NULL AND run_id = jobs.run_id)
                ), llm_cost_estimate, 0)
            WHERE id = :id
        """),
            {"id": job_id, "err": error[:2000], "fase": fase, "delay": delay},
        )
        db.commit()
        return "pending"

    # Esgotou retries ou falha nao-retriable: parquear em pipeline_failures
    db.execute(
        text("""
        UPDATE jobs
        SET status = 'failed_permanent',
            last_error = :err,
            last_phase = :fase,
            concluido_em = NOW(),
            llm_tokens_used = COALESCE((
                SELECT SUM(input_tokens + output_tokens + cache_read_tokens + cache_created_tokens)
                FROM llm_budget_ledger
                WHERE job_id = jobs.id
                   OR (job_id IS NULL AND run_id = jobs.run_id)
            ), llm_tokens_used, 0),
            llm_cost_estimate = COALESCE((
                SELECT SUM(cost_usd)
                FROM llm_budget_ledger
                WHERE job_id = jobs.id
                   OR (job_id IS NULL AND run_id = jobs.run_id)
            ), llm_cost_estimate, 0)
        WHERE id = :id
    """),
        {"id": job_id, "err": error[:2000], "fase": fase},
    )

    mensagem_amigavel = _formatar_mensagem_amigavel(fase, error)
    db.execute(
        text("""
        INSERT INTO pipeline_failures
            (tenant_id, job_id, lead_id, lead_nome, fase,
             mensagem_amigavel, erro_tecnico, tentativas_automaticas,
             checkpoint_id, payload)
        VALUES (:tenant, :jid, :lid, :lnome, :fase,
                :msg, :err, :tent, :ckpt, CAST(:payload AS jsonb))
    """),
        {
            "tenant": tenant_id,
            "jid": job_id,
            "lid": lead_id,
            "lnome": lead_nome,
            "fase": fase,
            "msg": mensagem_amigavel,
            "err": error[:2000],
            "tent": attempts,
            "ckpt": checkpoint_id,
            "payload": json.dumps(payload)
            if isinstance(payload, dict)
            else (payload or "{}"),
        },
    )
    db.commit()
    return "failed_permanent"


def defer_without_attempt(
    db: Session,
    job_id: int,
    *,
    reason: str,
    fase: str = "deferred",
    delay_seconds: int = 1800,
) -> str:
    """Adia um job por condicao externa sem consumir tentativa.

    Usado para esperas operacionais como janela de SDR ou WhatsApp
    desconectado. O job ja foi claimed e teve attempts incrementado; aqui
    compensamos esse incremento para nao esgotar retry por uma espera normal.
    """
    db.execute(
        text("""
        UPDATE jobs
        SET status = 'pending',
            attempts = GREATEST(attempts - 1, 0),
            last_error = :err,
            last_phase = :fase,
            next_retry_at = NOW() + (:delay || ' seconds')::interval,
            worker_id = NULL,
            worker_heartbeat = NULL
        WHERE id = :id
    """),
        {
            "id": job_id,
            "err": (reason or "deferred")[:2000],
            "fase": fase,
            "delay": max(30, int(delay_seconds or 1800)),
        },
    )
    db.commit()
    return "pending"


def reap_dead_workers(db: Session, dead_after_minutes: int = 5) -> int:
    """
    Detecta jobs travados em 'running' cujo worker morreu (heartbeat antigo)
    e devolve eles pra 'pending' pra outro worker tentar de novo.

    Retorna quantidade de jobs ressuscitados. Deveria rodar a cada minuto.
    """
    dialect_name = getattr(getattr(db, "bind", None), "dialect", None)
    dialect_name = getattr(dialect_name, "name", "")
    if dialect_name == "sqlite":
        rows = db.execute(
            text("""
            SELECT id, attempts, COALESCE(last_error, '')
            FROM jobs
            WHERE status = 'running'
        """)
        ).fetchall()
        ids = []
        for job_id, attempts, last_error in rows:
            ids.append((job_id,))
            db.execute(
                text("""
                UPDATE jobs
                SET status = 'pending',
                    attempts = CASE WHEN attempts > 0 THEN attempts - 1 ELSE 0 END,
                    last_error = CASE
                        WHEN COALESCE(last_error, '') = '' THEN 'worker_died'
                        ELSE last_error || ' | worker_died'
                    END,
                    worker_id = NULL,
                    worker_heartbeat = NULL,
                    next_retry_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """),
                {"id": job_id},
            )
        db.commit()
        return len(ids)

    result = db.execute(
        text("""
        UPDATE jobs
        SET status = 'pending',
            attempts = GREATEST(attempts - 1, 0),
            last_error = COALESCE(last_error || ' | ', '') || 'worker_died',
            worker_id = NULL,
            worker_heartbeat = NULL,
            next_retry_at = NOW()
        WHERE status = 'running'
          AND worker_heartbeat < NOW() - (:mins || ' minutes')::interval
        RETURNING id
    """),
        {"mins": dead_after_minutes},
    )
    ids = result.fetchall()
    db.commit()
    return len(ids)


def finalize_exhausted_jobs(db: Session) -> int:
    """Fecha jobs pendentes que ja consumiram todas as tentativas."""
    rows = db.execute(
        text("""
        SELECT id, COALESCE(last_error, 'tentativas esgotadas'), payload
        FROM jobs
        WHERE status = 'pending'
          AND attempts >= max_attempts
    """)
    ).fetchall()
    total = 0
    for job_id, error, payload in rows:
        status = mark_failure(
            db,
            job_id,
            error=f"Tentativas esgotadas: {error}",
            fase="worker_recovery",
            retriable=False,
        )
        if status == "failed_permanent":
            total += 1
    return total


def generate_worker_id() -> str:
    """ID unico do processo worker (pra rastrear quem pegou o que)."""
    return f"worker-{secrets.token_hex(4)}"


# ===== Mensagens amigaveis por fase =====
# Quando o sistema mostra erro pro cliente, fala em portugues do cotidiano.
# Tecnico vai no erro_tecnico pra suporte.
_MENSAGENS = {
    "hunter": "Não conseguimos encontrar novos leads para esses critérios. Tente outro nicho ou cidade maior.",
    "caio": "O sistema teve dificuldade pra qualificar este lead. Vamos pular pro próximo.",
    "agente_nicho": "Não conseguimos montar o briefing de nicho desta vez. Tente reprocessar.",
    "jina": "A pesquisa de referências externas falhou. Vamos tentar novamente em alguns minutos.",
    "arquiteto_mestre": "Tivemos um problema ao planejar o design. Reprocessar costuma resolver.",
    "builder_renderer": "O Builder não conseguiu concluir um site publicável nesta tentativa.",
    "worker_timeout": "A geração demorou mais do que o limite desta tentativa.",
    "validador": "A auditoria de qualidade não passou. Estamos investigando.",
    "deploy": "Falhou ao publicar o site no servidor. Pode ser um problema temporário de disco.",
    "healthcheck": "O site foi gerado mas ficou com problema (faltou texto, link de WhatsApp ou dados essenciais). Clique em 'Tentar de novo' que vamos refazer.",
    "franz": "O site foi gerado, mas não conseguimos enviar a mensagem pelo WhatsApp com o Franz. Verifique se o WhatsApp está conectado.",
    "bryan": "O site foi gerado, mas não conseguimos enviar a mensagem pelo WhatsApp com o Franz. Verifique se o WhatsApp está conectado.",
}


def normalizar_fase_falha(fase: Optional[str], erro_tecnico: str) -> str:
    fase_normalizada = str(fase or "").strip().lower()
    erro_normalizado = str(erro_tecnico or "").lower()
    if "builder_renderer" in erro_normalizado or fase_normalizada == "builder_renderer":
        return "builder_renderer"
    if "timeout" in erro_normalizado or fase_normalizada == "worker_timeout":
        return "worker_timeout"
    return fase_normalizada or "pipeline"


def _formatar_mensagem_amigavel(fase: Optional[str], erro_tecnico: str) -> str:
    fase_normalizada = normalizar_fase_falha(fase, erro_tecnico)
    if fase_normalizada in _MENSAGENS:
        return _MENSAGENS[fase_normalizada]
    # Fallback humano
    return (
        "Algo deu errado ao processar este lead. Tente novamente — costuma funcionar."
    )


def formatar_feedback_job(
    *,
    job_id: int,
    status: str,
    fase: Optional[str],
    erro_tecnico: str,
    attempts: int,
    max_attempts: int,
) -> Dict[str, Any]:
    """Create an actionable tenant-facing event while keeping raw errors private."""
    fase_normalizada = normalizar_fase_falha(fase, erro_tecnico)
    mensagem = _formatar_mensagem_amigavel(fase_normalizada, erro_tecnico)
    if status == "pending":
        return {
            "type": "pipeline_retry",
            "severity": "wait",
            "title": "Nova tentativa automática",
            "message": (
                f"{mensagem} Tentativa {attempts} de {max_attempts} encerrada; "
                "uma nova tentativa foi agendada automaticamente."
            ),
            "fase": fase_normalizada,
            "job_id": job_id,
            "tentativa": attempts,
            "max_tentativas": max_attempts,
        }
    return {
        "type": "pipeline_error",
        "severity": "error",
        "title": "Não foi possível concluir este site",
        "message": (
            f"{mensagem} As tentativas automáticas terminaram. "
            "Use 'Tentar novamente', busque outro lead ou fale com o suporte."
        ),
        "fase": fase_normalizada,
        "job_id": job_id,
        "tentativa": attempts,
        "max_tentativas": max_attempts,
        "credito_consumido": False,
    }
