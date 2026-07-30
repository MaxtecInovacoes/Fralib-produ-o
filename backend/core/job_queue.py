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
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy import text
from sqlalchemy.orm import Session


# Backoff exponencial em segundos: tentativa 1 -> 30s, 2 -> 2min, 3 -> 8min
_BACKOFF = [30, 120, 480]
# Bryan: mais tentativas com backoff mais longo (WhatsApp instável)
_BACKOFF_BRYAN = [60, 120, 240, 480, 960]


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
) -> Optional[int]:
    """
    Enfileira um job. Retorna o job_id, ou None se ja existia um com a mesma
    idempotency_key (caso comum: dois requests concorrentes pro mesmo lead).

    Priority: 1=Pro (alta), 2=Starter (normal), 3=Trial (baixa).
    """
    next_retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
    try:
        row = db.execute(text("""
            INSERT INTO jobs (tipo, payload, tenant_id, max_attempts,
                              idempotency_key, checkpoint_id, next_retry_at, priority)
            VALUES (:tipo, CAST(:payload AS jsonb), :tenant_id, :max_attempts,
                    :idem, :ckpt, :next_retry_at, :priority)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING id
        """), {
            "tipo": tipo,
            "payload": json.dumps(payload),
            "tenant_id": tenant_id,
            "max_attempts": max_attempts,
            "idem": idempotency_key,
            "ckpt": checkpoint_id,
            "next_retry_at": next_retry_at,
            "priority": priority,
        }).fetchone()
        db.commit()
        return row[0] if row else None
    except Exception as e:
        db.rollback()
        raise


def claim_next(db: Session, worker_id: str, tipos: Optional[list] = None) -> Optional[Dict[str, Any]]:
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

    row = db.execute(text(f"""
        WITH claimed AS (
            SELECT id FROM jobs
            WHERE status = 'pending'
              AND attempts < max_attempts
              AND COALESCE(next_retry_at, 'epoch'::timestamp) <= NOW() {filtro_tipo}
              {filtro_global}
              {filtro_tenant_lock}
            ORDER BY
                CASE
                    WHEN tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main') THEN 0
                    WHEN tipo = 'lead_production_tick' THEN 1
                    WHEN tipo = 'lead_supply_caio' THEN 2
                    WHEN tipo = 'lead_supply_hunter' THEN 3
                    WHEN tipo IN ('franz_outreach', 'bryan_outreach') THEN 4
                    ELSE 5
                END,
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
                  jobs.attempts, jobs.max_attempts, jobs.checkpoint_id, jobs.last_phase
    """), params).fetchone()
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
    }


def heartbeat(db: Session, job_id: int) -> None:
    """Worker chama isso a cada 30s pra dizer que ainda esta vivo."""
    db.execute(text("UPDATE jobs SET worker_heartbeat = NOW() WHERE id = :id"), {"id": job_id})
    db.commit()


def mark_success(db: Session, job_id: int) -> None:
    db.execute(text("""
        UPDATE jobs SET status = 'completed', concluido_em = NOW(), last_error = NULL
        WHERE id = :id
    """), {"id": job_id})
    db.commit()


def mark_interrupted(db: Session, job_id: int, reason: str = "worker_shutdown") -> None:
    """Devolve o job em execucao para pending sem consumir retry."""
    db.execute(text("""
        UPDATE jobs
        SET status = 'pending',
            last_error = COALESCE(last_error || ' | ', '') || :reason,
            worker_id = NULL,
            worker_heartbeat = NULL,
            next_retry_at = NOW()
        WHERE id = :id
          AND status = 'running'
    """), {"id": job_id, "reason": reason[:500]})
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
    job = db.execute(text("""
        SELECT attempts, max_attempts, tenant_id, checkpoint_id, payload
        FROM jobs WHERE id = :id
    """), {"id": job_id}).fetchone()
    if not job:
        return "missing"

    attempts, max_attempts, tenant_id, checkpoint_id, payload = job
    # Determinar backoff baseado no tipo do job
    _tipo_job = None
    if isinstance(payload, dict):
        _tipo_job = payload.get("_job_tipo")
    elif isinstance(payload, str):
        import json as _j
        try:
            _tipo_job = _j.loads(payload).get("_job_tipo")
        except Exception:
            pass
    # Buscar tipo do job direto da tabela se não veio no payload
    if not _tipo_job:
        _tipo_row = db.execute(text("SELECT tipo FROM jobs WHERE id = :id"), {"id": job_id}).fetchone()
        _tipo_job = _tipo_row[0] if _tipo_row else None
    _backoff_table = _BACKOFF_BRYAN if _tipo_job == "bryan_outreach" else _BACKOFF

    pode_tentar_mais = retriable and attempts < max_attempts
    if pode_tentar_mais:
        delay = delay_seconds if delay_seconds is not None else _backoff_table[min(attempts - 1, len(_backoff_table) - 1)]
        db.execute(text("""
            UPDATE jobs
            SET status = 'pending',
                last_error = :err,
                last_phase = :fase,
                next_retry_at = NOW() + (:delay || ' seconds')::interval,
                worker_id = NULL,
                worker_heartbeat = NULL
            WHERE id = :id
        """), {"id": job_id, "err": error[:2000], "fase": fase, "delay": delay})
        db.commit()
        return "pending"

    # Esgotou retries ou falha nao-retriable: parquear em pipeline_failures
    db.execute(text("""
        UPDATE jobs
        SET status = 'failed_permanent',
            last_error = :err,
            last_phase = :fase,
            concluido_em = NOW()
        WHERE id = :id
    """), {"id": job_id, "err": error[:2000], "fase": fase})

    mensagem_amigavel = _formatar_mensagem_amigavel(fase, error)
    db.execute(text("""
        INSERT INTO pipeline_failures
            (tenant_id, job_id, lead_id, lead_nome, fase,
             mensagem_amigavel, erro_tecnico, tentativas_automaticas,
             checkpoint_id, payload)
        VALUES (:tenant, :jid, :lid, :lnome, :fase,
                :msg, :err, :tent, :ckpt, CAST(:payload AS jsonb))
    """), {
        "tenant": tenant_id, "jid": job_id, "lid": lead_id, "lnome": lead_nome,
        "fase": fase, "msg": mensagem_amigavel, "err": error[:2000],
        "tent": attempts, "ckpt": checkpoint_id,
        "payload": json.dumps(payload) if isinstance(payload, dict) else (payload or "{}"),
    })
    db.commit()
    return "failed_permanent"


def reap_dead_workers(db: Session, dead_after_minutes: int = 5) -> int:
    """
    Detecta jobs travados em 'running' cujo worker morreu (heartbeat antigo)
    e devolve eles pra 'pending' pra outro worker tentar de novo.

    Retorna quantidade de jobs ressuscitados. Deveria rodar a cada minuto.
    """
    result = db.execute(text("""
        UPDATE jobs
        SET status = 'pending',
            last_error = COALESCE(last_error || ' | ', '') || 'worker_died',
            worker_id = NULL,
            worker_heartbeat = NULL,
            next_retry_at = NOW()
        WHERE status = 'running'
          AND worker_heartbeat < NOW() - (:mins || ' minutes')::interval
        RETURNING id
    """), {"mins": dead_after_minutes})
    ids = result.fetchall()
    db.commit()
    return len(ids)


def generate_worker_id() -> str:
    """ID unico do processo worker (pra rastrear quem pegou o que)."""
    return f"worker-{secrets.token_hex(4)}"


# ===== Mensagens amigaveis por fase =====
# Quando o sistema mostra erro pro cliente, fala em portugues do cotidiano.
# Tecnico vai no erro_tecnico pra suporte.
_MENSAGENS = {
    "hunter": "Não conseguimos encontrar novos leads para esses critérios. Tente outro nicho ou cidade maior.",
    "caio": "O sistema teve dificuldade pra qualificar este lead. Vamos pular pro próximo.",
    "theo": "Não conseguimos montar o briefing estratégico desta vez. Tente reprocessar.",
    "jina": "A pesquisa de referências externas falhou. Vamos tentar novamente em alguns minutos.",
    "arquiteto": "Tivemos um problema ao planejar o design. Reprocessar costuma resolver.",
    "liam": "O gerador de HTML não respondeu corretamente. Isso geralmente é resolvido com 'Tentar de novo'.",
    "liz": "A auditoria de qualidade não passou. Estamos investigando.",
    "deploy": "Falhou ao publicar o site no servidor. Pode ser um problema temporário de disco.",
    "healthcheck": "O site foi gerado mas ficou com problema (faltou texto, link de WhatsApp ou dados essenciais). Clique em 'Tentar de novo' que vamos refazer.",
    "bryan": "O site foi gerado, mas não conseguimos enviar a mensagem pelo WhatsApp. Verifique se o WhatsApp está conectado.",
}


def _formatar_mensagem_amigavel(fase: Optional[str], erro_tecnico: str) -> str:
    if fase and fase.lower() in _MENSAGENS:
        return _MENSAGENS[fase.lower()]
    # Fallback humano
    return "Algo deu errado ao processar este lead. Tente novamente — costuma funcionar."
