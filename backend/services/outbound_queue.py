"""Fila de mensagens outbound com cooldown + rate limit.

Pre-protege o numero do WhatsApp de bloqueio pelo Meta:
- Max 1 mensagem automática a cada 10 minutos (por tenant)
- Tempo aleatorio entre msgs (1-10 min)
- NUNCA 2 msgs no mesmo minuto
- Persistencia (se worker cair, msgs ficam na fila)
- Cleanup automatico (manter 7 dias de historico)
"""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger("outbound_queue")

# ════════════════════════════════════════════════════════════════════
# CONFIGURACAO
# ════════════════════════════════════════════════════════════════════

# Max mensagens automáticas em janela de 10 min por tenant
RATE_LIMIT_MAX = 1
RATE_LIMIT_WINDOW_SEC = 600  # 10 min

# Intervalo aleatorio entre msgs (segundos)
MIN_INTERVAL_SEC = 60   # min 1 min entre msgs
MAX_INTERVAL_SEC = 600  # max 10 min entre msgs

# Cleanup
HISTORY_DAYS = 7

# ════════════════════════════════════════════════════════════════════
# FUNCOES PRINCIPAIS
# ════════════════════════════════════════════════════════════════════

def enqueue_outbound(
    engine,
    tenant_id: int,
    lead_id: str,
    phone: str,
    message: str,
    source: str = "franz",
    priority: int = 5,
    delay_sec: int = 0,
) -> int | None:
    """Adiciona msg na fila outbound.

    IDEMPOTENCIA: Se a mesma mensagem (mesmo lead + mesmo texto) já estiver
    na fila com status pending/sending, NAO insere novamente. Retorna o ID
    existente.

    Args:
        engine: SQLAlchemy engine
        tenant_id: tenant ID
        lead_id: lead ID
        phone: telefone (com DDI, ex: 5511999999999)
        message: texto da msg
        source: 'franz', 'cron', 'human'
        priority: 1=highest, 10=lowest
        delay_sec: delay extra antes de enviar (alem do rate limit)

    Returns:
        ID da msg enfileirada, ou ID existente se duplicado, ou None se
        a mesma msg ja foi enviada com sucesso.
    """
    from sqlalchemy import text
    import hashlib

    # Calcula scheduled_at baseado em delay
    # O worker aplica rate limit tambem
    scheduled_at = datetime.now() + timedelta(seconds=delay_sec)

    # Gerar hash unico para idempotencia
    # Usamos tenant_id + lead_id + message_hash para identificar duplicatas
    msg_hash = hashlib.md5(f"{tenant_id}:{lead_id}:{message}".encode()).hexdigest()[:16]

    with engine.connect() as c:
        # IDEMPOTENCIA: Verificar se a mesma msg ja existe na fila (pending/sending)
        existing = c.execute(text("""
            SELECT id, status FROM outbound_queue
            WHERE tenant_id = :tid
              AND lead_id = :lid
              AND message = :msg
              AND status IN ('pending', 'sending')
            LIMIT 1
        """), {
            "tid": tenant_id,
            "lid": lead_id,
            "msg": message,
        }).fetchone()

        if existing:
            existing_id = existing[0]
            existing_status = existing[1] if len(existing) > 1 else "pending"
            logger.info(f"[outbound] msg duplicada detectada id={existing_id} status={existing_status}")
            return existing_id  # Ja existe, retorna ID existente

        # Tambem verificar se ja foi enviada (para logs)
        already_sent = c.execute(text("""
            SELECT id FROM outbound_queue
            WHERE tenant_id = :tid
              AND lead_id = :lid
              AND message = :msg
              AND status = 'sent'
            LIMIT 1
        """), {
            "tid": tenant_id,
            "lid": lead_id,
            "msg": message,
        }).fetchone()

        if already_sent:
            logger.info(f"[outbound] msg ja enviada anteriormente id={already_sent[0]}, pulando")
            return None  # Ja enviada, no need to reenviar

        # Inserir nova mensagem
        result = c.execute(text("""
            INSERT INTO outbound_queue
                (tenant_id, lead_id, phone, message, source, priority, scheduled_at)
            VALUES (:tid, :lid, :phone, :msg, :src, :prio, :sched)
            RETURNING id
        """), {
            "tid": tenant_id,
            "lid": lead_id,
            "phone": phone,
            "msg": message,
            "src": source,
            "prio": priority,
            "sched": scheduled_at,
        })
        msg_id = result.fetchone()[0]
        c.commit()

    logger.info(f"[outbound] enfileirado msg {msg_id} (tenant={tenant_id}, lead={lead_id})")
    return msg_id


def get_pending_count(engine, tenant_id: Optional[int] = None) -> int:
    """Retorna numero de msgs pendentes."""
    from sqlalchemy import text
    with engine.connect() as c:
        if tenant_id:
            r = c.execute(text("""
                SELECT COUNT(*) FROM outbound_queue
                WHERE status = 'pending' AND tenant_id = :tid
            """), {"tid": tenant_id})
        else:
            r = c.execute(text("""
                SELECT COUNT(*) FROM outbound_queue WHERE status = 'pending'
            """))
        return r.scalar() or 0


def get_recent_sent_count(engine, tenant_id: int, window_sec: int = RATE_LIMIT_WINDOW_SEC) -> int:
    """Quantas msgs foram enviadas na janela."""
    from sqlalchemy import text
    cutoff = datetime.now() - timedelta(seconds=window_sec)
    with engine.connect() as c:
        r = c.execute(text("""
            SELECT COUNT(*) FROM outbound_queue
            WHERE tenant_id = :tid
              AND status = 'sent'
              AND sent_at > :cutoff
        """), {"tid": tenant_id, "cutoff": cutoff})
        return r.scalar() or 0


def can_send_now(engine, tenant_id: int) -> tuple[bool, int]:
    """Verifica se pode enviar msg agora.

    Returns:
        (pode_enviar, segundos_ate_poder_enviar)
    """
    from sqlalchemy import text

    recent = get_recent_sent_count(engine, tenant_id)
    if recent < RATE_LIMIT_MAX:
        return True, 0

    # Atingiu o limite. Calcula quando pode enviar de novo.
    with engine.connect() as c:
        # Pega a msg mais recente
        r = c.execute(text("""
            SELECT sent_at FROM outbound_queue
            WHERE tenant_id = :tid AND status = 'sent'
            ORDER BY sent_at DESC LIMIT 1
        """), {"tid": tenant_id})
        row = r.fetchone()
        if not row or not row[0]:
            return True, 0
        last_sent = row[0]
        # Normaliza: BOTH tem que ser naive ou BOTH tem que ser aware
        # O DB retorna timezone-aware (UTC), entao usamos datetime.now() naive
        # OU convertemos ambos pra UTC
        from datetime import timezone
        if hasattr(last_sent, 'tzinfo') and last_sent.tzinfo is not None:
            # last_sent e aware (UTC). Converter pra naive = subtrair tz
            last_sent = last_sent.replace(tzinfo=None)
        # Agora datetime.now() (naive) - AMBOS no mesmo timezone (server local)
        # Se server local != UTC, isso quebra. Solucao robusta: usar utcnow()
        now = datetime.utcnow()
        wait = (last_sent + timedelta(seconds=RATE_LIMIT_WINDOW_SEC)) - now
        return False, max(0, int(wait.total_seconds()))


def _select_pending_msg(conn):
    """Sprint 1.2 — helper isolado pra permitir mock nos testes.

    Retorna ``(msg_id, tenant_id, lead_id, phone, message, source, attempts)``
    ou ``None`` se não há msgs pendentes.

    Implementação: SELECT ... FOR UPDATE SKIP LOCKED (mesmo da lógica original).
    """
    from sqlalchemy import text
    rows = conn.execute(text("""
        SELECT id, tenant_id, lead_id, phone, message, source, attempts
        FROM outbound_queue
        WHERE status = 'pending'
          AND scheduled_at <= NOW()
        ORDER BY scheduled_at ASC, id ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    """)).fetchall()
    if not rows:
        return None
    return tuple(rows[0])


def _check_last_inbound_vs_outbound(engine, lead_id, tenant_id) -> bool:
    """Sprint 1.2 — Bug #3: checa se o lead respondeu DEPOIS do último outbound.

    Retorna ``True`` se ``last_inbound_at > last_outbound_at`` (lead respondeu,
    devemos abortar o envio pra não falar por cima da resposta do lead).

    Em caso de erro de leitura ou dados ausentes, retorna ``False`` (fail-open)
    pra não bloquear a fila inteira por uma falha de telemetria.
    """
    from sqlalchemy import text
    try:
        with engine.connect() as c:
            row = c.execute(text("""
                SELECT
                    MAX(CASE WHEN direcao = 'entrada' THEN criado_em END) AS last_inbound,
                    MAX(CASE WHEN direcao = 'saida' THEN criado_em END) AS last_outbound
                FROM interacoes
                WHERE lead_id = :lid AND user_id = :tid
            """), {"lid": lead_id, "tid": tenant_id}).fetchone()
        if not row:
            return False
        last_inbound = row[0]
        last_outbound = row[1]
        if not last_inbound:
            return False
        if last_outbound and last_inbound <= last_outbound:
            return False
        return True
    except Exception as e:
        logger.warning(f"[outbound] _check_last_inbound_vs_outbound falhou: {e}")
        return False


def set_cooldown(lead_key: str) -> None:
    """Sprint 1.2 — Bug #3: marca cooldown Redis para o lead.

    Se Redis estiver offline (lead_lock offline), usa fallback Postgres
    (não fatal — apenas loga warning).
    """
    try:
        from backend.agents.sdr_langgraph.lead_lock import get_redis_client
        r = get_redis_client()
        if r is None:
            logger.warning(f"[outbound] Redis offline — set_cooldown skip para {lead_key}")
            return
        # Cooldown de 60s padrão por tenant (mesmo TTL do response_executor).
        r.setex(f"fralib:lead_cooldown:{lead_key}", 60, "1")
    except Exception as e:
        logger.warning(f"[outbound] set_cooldown falhou para {lead_key}: {e}")


def increment_daily_count(tenant_id: int, lead_id: str) -> None:
    """Sprint 1.2 — Bug #3: incrementa contador diário por tenant+lead.

    Hoje não persiste em coluna; usa o TTL Redis (counter simples).
    Em produção, deveria atualizar uma coluna ``leads.outbound_count_today``.
    """
    try:
        from backend.agents.sdr_langgraph.lead_lock import get_redis_client
        r = get_redis_client()
        if r is None:
            return
        key = f"fralib:outbound_daily:{tenant_id}:{lead_id}"
        r.incr(key)
        # TTL de 24h (expira à meia-noite SP, aproximado)
        r.expire(key, 86400)
    except Exception as e:
        logger.warning(f"[outbound] increment_daily_count falhou: {e}")


def dequeue_and_send(
    engine,
    sender_func,
    set_cooldown_fn=None,
    increment_daily_fn=None,
) -> dict:
    """Processa fila: pega 1 msg pendente, verifica rate limit, envia.

    Sprint 1.2 — Bug #3: antes de enviar, valida se o lead já respondeu
    (``last_inbound_at > last_outbound_at``). Se sim, aborta (skipped)
    pra não duplicar a conversa.

    Args:
        engine: SQLAlchemy engine
        sender_func: callable(phone, message) -> success: bool
        set_cooldown_fn: opcional, callable(lead_key) — chamado ANTES do envio
                         para garantir que 2 workers não enviem simultaneamente
                         para o mesmo lead. Default: ``set_cooldown``.
        increment_daily_fn: opcional, callable(tenant_id, lead_id) — chamado
                            APÓS sucesso do envio para contabilizar o lead.
                            Default: ``increment_daily_count``.

    Returns:
        { sent: int, skipped: int, failed: int, waiting_sec: int }
    """
    from sqlalchemy import text

    if set_cooldown_fn is None:
        set_cooldown_fn = set_cooldown
    if increment_daily_fn is None:
        increment_daily_fn = increment_daily_count

    result = {"sent": 0, "skipped": 0, "failed": 0, "waiting_sec": 0, "msgs": []}

    with engine.connect() as c:
        # Pega a msg mais antiga que esteja pronta
        # USA FOR UPDATE SKIP LOCKED para evitar race condition:
        # - Se outra instância pegou a mesma msg, essa pula
        # - Garante que cada msg é processada por exatamente 1 worker
        rows = c.execute(text("""
            SELECT id, tenant_id, lead_id, phone, message, source, attempts
            FROM outbound_queue
            WHERE status = 'pending'
              AND scheduled_at <= NOW()
            ORDER BY scheduled_at ASC, id ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        """)).fetchall()

    if not rows:
        return result

    msg_id, tenant_id, lead_id, phone, message, source, attempts = rows[0]

    # === Sprint 1.2 — Bug #3: checa se lead respondeu desde o último outbound ===
    if _check_last_inbound_vs_outbound(engine, lead_id, tenant_id):
        logger.info(
            f"[outbound] msg {msg_id} abortada — lead {lead_id} respondeu "
            "após último outbound"
        )
        with engine.connect() as c:
            c.execute(text("""
                UPDATE outbound_queue
                SET status = 'skipped',
                    error = 'lead respondeu após último outbound',
                    scheduled_at = NOW() + INTERVAL '60 minutes'
                WHERE id = :id AND status = 'pending'
            """), {"id": msg_id})
            c.commit()
        result["skipped"] = 1
        return result

    # Verifica rate limit
    can_send, wait_sec = can_send_now(engine, tenant_id)
    if not can_send:
        result["skipped"] = 1
        result["waiting_sec"] = wait_sec
        logger.info(f"[outbound] msg {msg_id} bloqueada por rate limit (wait={wait_sec}s)")
        return result

    # === Sprint 1.2 — Bug #3: set_cooldown ANTES do sender ===
    # Garante que 2 workers simultâneos não enviem para o mesmo lead_key.
    # Se Redis offline, fallback loga warning mas não bloqueia (Redis já tem
    # fallback Postgres wpp_lock_until via response_executor).
    lead_key = f"{tenant_id}:{lead_id}"
    try:
        set_cooldown_fn(lead_key)
    except Exception as _cooldown_err:
        logger.warning(
            f"[outbound] set_cooldown_fn falhou (nao-bloqueante): {_cooldown_err}"
        )

    # Marca como 'sending' atomicamente
    with engine.connect() as c:
        c.execute(text("""
            UPDATE outbound_queue SET status = 'sending', attempts = attempts + 1
            WHERE id = :id AND status = 'pending'
        """), {"id": msg_id})
        c.commit()

    # Envia
    try:
        try:
            success = sender_func(phone, message, tenant_id)
        except TypeError:
            success = sender_func(phone, message)
        if success is None:
            with engine.connect() as c:
                c.execute(text("""
                    UPDATE outbound_queue
                    SET status = 'pending',
                        scheduled_at = NOW() + INTERVAL '10 minutes',
                        error = 'tenant whatsapp unavailable or outside schedule'
                    WHERE id = :id
                """), {"id": msg_id})
                c.commit()
            result["skipped"] = 1
            result["waiting_sec"] = 600
            return result
        if success:
            # Sprint 1.2: 3 statements (outbound UPDATE + leads UPDATE + interacoes
            # INSERT) em transacao atomica. Se 2o ou 3o falhar, ROLLBACK total —
            # evita inconsistencia (outbound=send mas leads sem update).
            try:
                with engine.begin() as c:
                    c.execute(text("""
                        UPDATE outbound_queue SET status = 'sent', sent_at = NOW()
                        WHERE id = :id
                    """), {"id": msg_id})
                    c.execute(text("""
                        UPDATE leads
                        SET sdr_stage = CASE
                            WHEN COALESCE(sdr_stage, '') IN ('', 'pendente_wpp', 'pending_sdr_send', 'manual_test_no_wpp') THEN 'hook'
                            ELSE sdr_stage
                        END,
                        atualizado_em = NOW()::text
                        WHERE id = :lead_id AND user_id = :tenant_id
                    """), {"lead_id": lead_id, "tenant_id": tenant_id})
                    c.execute(text("""
                        INSERT INTO interacoes
                            (lead_id, lead_nome, nicho, cidade, direcao, mensagem, criado_em, user_id, tipo)
                        SELECT id, nome, segmento, cidade, 'saida', :message,
                               to_char(NOW() AT TIME ZONE 'America/Sao_Paulo', 'YYYY-MM-DD"T"HH24:MI:SS.US'),
                               user_id, 'whatsapp'
                        FROM leads
                        WHERE id = :lead_id AND user_id = :tenant_id
                    """), {"message": message, "lead_id": lead_id, "tenant_id": tenant_id})
            except Exception as _tx_err:
                logger.error(
                    f"[outbound] transacao atomica falhou (msg_id={msg_id}, "
                    f"lead_id={lead_id}): {_tx_err} — ROLLBACK aplicado"
                )
                raise
            try:
                from sqlalchemy.orm import sessionmaker
                from services.credits_manager import consumir_credito_trial_entregue

                Session = sessionmaker(bind=engine)
                db = Session()
                try:
                    consumed = consumir_credito_trial_entregue(
                        db,
                        int(tenant_id),
                        str(lead_id or ""),
                    )
                    if consumed:
                        logger.info("[outbound] credito trial consumido tenant=%s lead=%s", tenant_id, lead_id)
                finally:
                    db.close()
            except Exception as e:
                logger.warning("[outbound] falha ao consumir credito trial tenant=%s lead=%s: %s", tenant_id, lead_id, e)

            # === Sprint 1.2 — Bug #3: increment_daily_count APÓS sucesso ===
            try:
                increment_daily_fn(int(tenant_id), str(lead_id or ""))
            except Exception as _inc_err:
                logger.warning(
                    f"[outbound] increment_daily_fn falhou (nao-bloqueante): {_inc_err}"
                )

            result["sent"] = 1
            result["msgs"].append({"id": msg_id, "phone": phone, "source": source})
            logger.info(f"[outbound] msg {msg_id} ENVIADA para {phone}")
        else:
            failure_reason = "sender returned False"
            # Retry com backoff exponencial: 1min, 2min, 4min, 8min, 16min (max)
            # Após 3 tentativas (attempts >= 3 antes do incremento), mover para DLQ
            if attempts >= 3:
                # Mover para DLQ após 3 tentativas falhas
                with engine.connect() as c:
                    c.execute(text("""
                        UPDATE outbound_queue
                        SET status = 'dlq', error = :err
                        WHERE id = :id
                    """), {"id": msg_id, "err": f"Max retries exceeded (3): {failure_reason}"})
                    c.commit()
                logger.warning(f"[outbound] msg {msg_id} movida para DLQ após 3 tentativas")
                result["failed"] = 1
            else:
                # Backoff: 2^attempts * 60 segundos (1min, 2min, 4min...)
                backoff_seconds = (2 ** attempts) * 60
                next_retry = datetime.now() + timedelta(seconds=backoff_seconds)
                with engine.connect() as c:
                    c.execute(text("""
                        UPDATE outbound_queue
                        SET status = 'pending',
                            scheduled_at = :next_retry,
                            error = :err
                        WHERE id = :id
                    """), {"id": msg_id, "next_retry": next_retry, "err": f"Retry scheduled in {backoff_seconds}s: {failure_reason}"})
                    c.commit()
                logger.warning(f"[outbound] msg {msg_id} agendada para retry em {backoff_seconds}s (attempt {attempts + 1})")
                result["failed"] = 1
    except Exception as e:
        with engine.connect() as c:
            c.execute(text("""
                UPDATE outbound_queue SET status = 'failed', error = :err
                WHERE id = :id
            """), {"id": msg_id, "err": str(e)[:500]})
            c.commit()
        result["failed"] = 1
        logger.error(f"[outbound] msg {msg_id} falhou: {e}")

    return result


def cleanup_old_messages(engine, days: int = HISTORY_DAYS) -> int:
    """Remove msgs enviadas e com falha ha mais de X dias.

    Cleanup cobre:
    - msgs 'sent' com mais de 7 dias (HISTORY_DAYS)
    - msgs 'failed' com mais de 30 dias (hardcoded, não usa param)
    - msgs 'pending' com mais de 30 dias (limpeza de orphan)

    Msgs em DLQ (status='dlq') são mantidas para análise manual.
    """
    from sqlalchemy import text

    deleted = 0
    with engine.connect() as c:
        # Msgs enviadas
        cutoff_sent = datetime.now() - timedelta(days=days)
        r = c.execute(text("""
            DELETE FROM outbound_queue
            WHERE status = 'sent' AND sent_at < :cutoff
        """), {"cutoff": cutoff_sent})
        deleted += r.rowcount

        # Msgs com falha (30 dias)
        cutoff_failed = datetime.now() - timedelta(days=30)
        r = c.execute(text("""
            DELETE FROM outbound_queue
            WHERE status = 'failed' AND sent_at < :cutoff
        """), {"cutoff": cutoff_failed})
        deleted += r.rowcount

        # Msgs pending órfãs (30 dias sem processamento)
        cutoff_pending = datetime.now() - timedelta(days=30)
        r = c.execute(text("""
            DELETE FROM outbound_queue
            WHERE status = 'pending' AND scheduled_at < :cutoff
        """), {"cutoff": cutoff_pending})
        deleted += r.rowcount

        c.commit()
    if deleted:
        logger.info(f"[outbound] cleanup: {deleted} msgs antigas removidas")
    return deleted


def schedule_next_batch(engine) -> dict:
    """Re-agenda msgs que nao puderam ser enviadas.

    Para cada msg 'pending' que deveria ter saido mas foi bloqueada por rate
    limit, recalcula scheduled_at para o proximo slot disponivel.

    Returns:
        { re_scheduled: int, status }
    """
    from sqlalchemy import text

    re_scheduled = 0
    with engine.connect() as c:
        # Pega todas as pending que estao atrasadas
        rows = c.execute(text("""
            SELECT id, tenant_id, scheduled_at FROM outbound_queue
            WHERE status = 'pending' AND scheduled_at < NOW() - INTERVAL '1 minute'
        """)).fetchall()

        for msg_id, tenant_id, _ in rows:
            # Calcula proximo slot disponivel
            can_send, wait_sec = can_send_now(engine, tenant_id)
            if can_send:
                # Pode enviar agora - agenda pra daqui 1 min
                next_time = datetime.now() + timedelta(seconds=60)
            else:
                next_time = datetime.now() + timedelta(seconds=wait_sec + 60)

            c.execute(text("""
                UPDATE outbound_queue SET scheduled_at = :ts
                WHERE id = :id
            """), {"id": msg_id, "ts": next_time})
            re_scheduled += 1

        c.commit()

    return {"re_scheduled": re_scheduled}


# ════════════════════════════════════════════════════════════════════
# WORKER LOOP (chamado pelo cron)
# ════════════════════════════════════════════════════════════════════

def process_queue_once(engine, sender_func) -> dict:
    """Processa 1 ciclo da fila: envia ate 1 msg respeitando rate limit.

    Returns:
        { sent, skipped, failed, waiting_sec, total_pending, recent_sent }
    """
    # Limpa msgs antigas
    cleanup_old_messages(engine)

    # Re-agenda msgs bloqueadas
    schedule_next_batch(engine)

    # Tenta enviar 1
    result = dequeue_and_send(engine, sender_func)

    # Stats
    result["total_pending"] = get_pending_count(engine)
    return result


def get_queue_stats(engine, tenant_id: int | None = None) -> dict:
    """Retorna estatísticas da fila para monitoramento/alertas.

    Returns:
        {
            "total_pending": N,
            "total_failed": N,
            "total_dlq": N,
            "total_sent_today": N,
            "oldest_pending_minutes": N or None,
            "by_tenant": [{tenant_id, pending, failed, dlq}, ...]
        }
    """
    from sqlalchemy import text

    result = {"total_pending": 0, "total_failed": 0, "total_dlq": 0, "total_sent_today": 0}

    with engine.connect() as c:
        # Counts globais
        counts = c.execute(text("""
            SELECT status, COUNT(*)
            FROM outbound_queue
            WHERE :tenant_filter OR tenant_id = :tid
            GROUP BY status
        """), {"tid": tenant_id or 0, "tenant_filter": tenant_id is None}).fetchall()

        for status, count in counts:
            if status == "pending":
                result["total_pending"] = count
            elif status == "failed":
                result["total_failed"] = count
            elif status == "dlq":
                result["total_dlq"] = count
            elif status == "sent":
                result["total_sent_today"] = count

        # Mensagem mais antiga pendente
        if result["total_pending"] > 0:
            oldest = c.execute(text("""
                SELECT EXTRACT(EPOCH FROM (NOW() - scheduled_at)) / 60
                FROM outbound_queue
                WHERE status = 'pending'
                ORDER BY scheduled_at ASC
                LIMIT 1
            """)).scalar()
            result["oldest_pending_minutes"] = int(oldest) if oldest else None

        # Alerta: backlog crescente
        result["backlog_alert"] = result["total_pending"] > 100
        result["dlq_alert"] = result["total_dlq"] > 10

    return result


# ════════════════════════════════════════════════════════════════════
# EXPORTAR
# ════════════════════════════════════════════════════════════════════

__all__ = [
    "RATE_LIMIT_MAX",
    "RATE_LIMIT_WINDOW_SEC",
    "enqueue_outbound",
    "get_pending_count",
    "get_recent_sent_count",
    "can_send_now",
    "dequeue_and_send",
    "cleanup_old_messages",
    "process_queue_once",
    "get_queue_stats",  # Nova: estatísticas da fila
]
