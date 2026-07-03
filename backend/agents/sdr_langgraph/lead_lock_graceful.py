"""Sprint 1.1: graceful lead_lock — Redis offline nao bloqueia fluxo.

Problema P1: _lead_lock_guard original RAISE RuntimeError se Redis offline,
propagando pro whatsapp_listener e bloqueando TODO o processamento de msg.

Fix: versao "graceful" que retorna None (sem lock) e o caller faz dedup local.

API:
    with lead_lock_guard(lead_id) as lock:
        if lock is None:
            # Redis offline — processar mesmo assim com dedup local
            ...
        else:
            # Lock adquirido — processar com seguranca
            ...
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger("fralib.sdr.lead_lock_graceful")

REDIS_RETRY_COUNT = int(os.getenv("LEAD_LOCK_RETRY_COUNT", "3"))
REDIS_RETRY_BASE_DELAY = float(os.getenv("LEAD_LOCK_RETRY_BASE_DELAY", "0.5"))


def get_redis_client():
    """Tenta obter cliente Redis. Retorna None se offline.

    Import lazy pra nao quebrar modulos que nao tem Redis.
    """
    try:
        from agents.sdr_langgraph.lead_lock import get_redis_client as _orig
        return _orig()
    except Exception as e:
        logger.warning(f"[lead_lock_graceful] get_redis_client falhou: {e}")
        return None


@contextmanager
def lead_lock_guard(lead_id: str):
    """Lock graceful para lead. Retorna None se Redis offline (NUNCA raise).

    Comportamento:
      1. Tenta adquirir lock Redis com retry 3x
      2. Se todas tentativas falharem, log.warning e yield None
      3. Caller processa com dedup local

    ANTES (P1 bug): _lead_lock_guard levantava RuntimeError, quebrando
    whatsapp_listener inteiro se Redis offline.

    Args:
        lead_id: Identificador do lead

    Yields:
        redis_lock object se adquirido, None se Redis offline
    """
    redis_client = get_redis_client()

    if not redis_client:
        logger.warning(
            f"[lead_lock_graceful] Redis offline para lead {lead_id} "
            f"— processando SEM lock (dedup local ativo)"
        )
        yield None
        return

    lock_key = f"fralib:lead_lock:{lead_id}"
    try:
        redis_lock = redis_client.lock(
            lock_key,
            timeout=60.0,
            blocking_timeout=60.0,
        )
    except Exception as e:
        logger.warning(
            f"[lead_lock_graceful] Falha ao criar lock object para {lead_id}: {e} "
            f"— processando SEM lock"
        )
        yield None
        return

    # Retry com backoff exponencial
    last_error = None
    for attempt in range(1, REDIS_RETRY_COUNT + 1):
        try:
            acquired = redis_lock.acquire(blocking=True, blocking_timeout=60.0)
            if acquired:
                try:
                    yield redis_lock
                finally:
                    try:
                        redis_lock.release()
                    except Exception:
                        pass
                return
            else:
                last_error = f"Timeout (tentativa {attempt}/{REDIS_RETRY_COUNT})"
        except Exception as e:
            last_error = str(e)
            logger.warning(
                f"[lead_lock_graceful] Tentativa {attempt}/{REDIS_RETRY_COUNT} falhou "
                f"para {lead_id}: {e}"
            )
            # Tenta reconectar
            try:
                redis_client = get_redis_client()
                if redis_client:
                    redis_lock = redis_client.lock(lock_key, timeout=60.0, blocking_timeout=60.0)
            except Exception:
                pass

        # Backoff se nao e' ultima tentativa
        if attempt < REDIS_RETRY_COUNT:
            delay = REDIS_RETRY_BASE_DELAY * (2 ** (attempt - 1))
            time.sleep(delay)

    # Todas tentativas falharam — graceful fallback
    logger.error(
        f"[lead_lock_graceful] FALHA TOTAL ao adquirir lock para {lead_id} "
        f"apos {REDIS_RETRY_COUNT} tentativas ({last_error}) "
        f"— processando SEM lock (dedup local ativo)"
    )
    yield None
