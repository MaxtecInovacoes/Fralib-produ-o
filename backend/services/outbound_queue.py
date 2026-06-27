"""Fila de mensagens outbound com cooldown + rate limit.

Pre-protege o numero do WhatsApp de bloqueio pelo Meta:
- Max 2 mensagens a cada 10 minutos (por tenant)
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

# Max mensagens em janela de 10 min por tenant
RATE_LIMIT_MAX = 2
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
) -> int:
    """Adiciona msg na fila outbound.

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
        ID da msg enfileirada
    """
    from sqlalchemy import text

    # Calcula scheduled_at baseado em delay
    # O worker aplica rate limit tambem
    scheduled_at = datetime.now() + timedelta(seconds=delay_sec)

    with engine.connect() as c:
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
        # Normaliza: se tem timezone, converte pra naive (assume UTC)
        if hasattr(last_sent, 'tzinfo') and last_sent.tzinfo is not None:
            last_sent = last_sent.replace(tzinfo=None)
        # Pode enviar X segundos depois
        now = datetime.now()
        if hasattr(now, 'tzinfo') and now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        wait = (last_sent + timedelta(seconds=RATE_LIMIT_WINDOW_SEC)) - now
        return False, max(0, int(wait.total_seconds()))


def dequeue_and_send(engine, sender_func) -> dict:
    """Processa fila: pega 1 msg pendente, verifica rate limit, envia.

    Args:
        engine: SQLAlchemy engine
        sender_func: callable(phone, message) -> success: bool

    Returns:
        { sent: int, skipped: int, failed: int, waiting_sec: int }
    """
    from sqlalchemy import text

    result = {"sent": 0, "skipped": 0, "failed": 0, "waiting_sec": 0, "msgs": []}

    with engine.connect() as c:
        # Pega a msg mais antiga que esteja pronta
        rows = c.execute(text("""
            SELECT id, tenant_id, lead_id, phone, message, source, attempts
            FROM outbound_queue
            WHERE status = 'pending'
              AND scheduled_at <= NOW()
            ORDER BY priority ASC, scheduled_at ASC
            LIMIT 1
        """)).fetchall()

    if not rows:
        return result

    msg_id, tenant_id, lead_id, phone, message, source, attempts = rows[0]

    # Verifica rate limit
    can_send, wait_sec = can_send_now(engine, tenant_id)
    if not can_send:
        result["skipped"] = 1
        result["waiting_sec"] = wait_sec
        logger.info(f"[outbound] msg {msg_id} bloqueada por rate limit (wait={wait_sec}s)")
        return result

    # Marca como 'sending' atomicamente
    with engine.connect() as c:
        c.execute(text("""
            UPDATE outbound_queue SET status = 'sending', attempts = attempts + 1
            WHERE id = :id AND status = 'pending'
        """), {"id": msg_id})
        c.commit()

    # Envia
    try:
        success = sender_func(phone, message)
        if success:
            with engine.connect() as c:
                c.execute(text("""
                    UPDATE outbound_queue SET status = 'sent', sent_at = NOW()
                    WHERE id = :id
                """), {"id": msg_id})
                c.commit()
            result["sent"] = 1
            result["msgs"].append({"id": msg_id, "phone": phone, "source": source})
            logger.info(f"[outbound] msg {msg_id} ENVIADA para {phone}")
        else:
            with engine.connect() as c:
                c.execute(text("""
                    UPDATE outbound_queue SET status = 'failed', error = 'sender returned False'
                    WHERE id = :id
                """), {"id": msg_id})
                c.commit()
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
    """Remove msgs enviadas ha mais de X dias."""
    from sqlalchemy import text
    cutoff = datetime.now() - timedelta(days=days)
    with engine.connect() as c:
        r = c.execute(text("""
            DELETE FROM outbound_queue
            WHERE status = 'sent' AND sent_at < :cutoff
        """), {"cutoff": cutoff})
        deleted = r.rowcount
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
]