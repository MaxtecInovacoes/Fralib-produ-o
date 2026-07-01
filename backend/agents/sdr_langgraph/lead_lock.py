"""
Lock global por lead para prevenir race condition no Franz SDR.

Resolve o bug onde Franz responde 3x à mesma mensagem devido a:
- Múltiplas threads/processos chamando responder_lead() simultaneamente
- Concorrência não controlada na memória compartilhada Redis
- Deduplicação ineficiente entre workers e listener

Uso:
    from .lead_lock import _lead_lock_guard

    def responder_lead(...):
        with _lead_lock_guard(lead_id):
            # Toda a função dentro do lock
            ...

SDR 10/10 - ITEM 5: Lock distribuido via Redis
- Lock principal: Redis (distribuído entre processos)
- FALLBACK TÉCNICO: threading.Lock local se Redis offline
  ⚠️ RISCO: Lock local não funciona em ambientes distribuídos multi-worker
  Justificativa: Lock local é melhor que nada para deduplicação
  Não afeta resposta do bot, só previne duplicatas no mesmo processo
"""

import os
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from typing import Dict, Optional
from functools import lru_cache

import redis

# ============================================================
# Redis Client (lazy initialization com fallback)
# ============================================================

_redis_client: Optional[redis.Redis] = None
_redis_lock = threading.Lock()
_use_redis: bool = False


def get_redis_client() -> Optional[redis.Redis]:
    """
    Retorna cliente Redis com lazy initialization.

   SDR 10/10 - ITEM 5: Funcao centralizada para obter Redis.
    Usa REDIS_URL do .env com fallback para None.

    Returns:
        redis.Redis se configurado e disponivel, None caso contrario
    """
    global _redis_client, _use_redis

    if _redis_client is not None:
        return _redis_client if _use_redis else None

    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return None

    with _redis_lock:
        if _redis_client is None:
            try:
                import redis as redis_lib
                _redis_client = redis_lib.from_url(redis_url, decode_responses=True)
                _redis_client.ping()
                _use_redis = True
                print("[lead_lock] Redis conectado - lock distribuido ativo")
            except Exception as e:
                print(f"[lead_lock] Redis nao disponivel: {e} - usando fallback threading.Lock")
                _redis_client = None
                _use_redis = False
        return _redis_client if _use_redis else None


# ============================================================
# Lock Cache (mantido para fallback threading.Lock)
# ============================================================

# Cache global de locks por lead_id
# Usamos dict thread-safe com lock externo
_LEAD_LOCKS: Dict[str, threading.Lock] = {}
_LOCK_GUARD = threading.Lock()

# Cache de message_ids recentes (TTL 60s)
# Usa OrderedDict para evict-oldest sem invalidar TUDO de uma vez
_MESSAGE_ID_CACHE: "OrderedDict[str, float]" = OrderedDict()
_CACHE_LOCK = threading.Lock()
_CACHE_MAX_SIZE = 10000


# ============================================================
# Lock Guard com Redis Distributed Lock
# ============================================================

@contextmanager
def _lead_lock_guard(lead_id: str):
    """
    Garante que só 1 thread/processo por vez possa processar um lead.

    SDR 10/10 - ITEM 5: Agora usa Redis lock distribuido quando disponivel.
    Fallback para threading.Lock se Redis offline.

    Args:
        lead_id: Identificador único do lead (telefone ou lead_id do banco)

    Yields:
        Lock para o lead_id
    """
    redis_client = get_redis_client()

    if redis_client:
        # Modo distribuido: Redis lock
        lock_key = f"fralib:lead_lock:{lead_id}"
        redis_lock = redis_client.lock(
            lock_key,
            timeout=30.0,
            blocking_timeout=30.0,
        )
        acquired = False
        try:
            acquired = redis_lock.acquire(blocking=True, blocking_timeout=30.0)
            if not acquired:
                raise TimeoutError(f"Nao conseguiu lock Redis para lead {lead_id} em 30s")
            yield redis_lock
        finally:
            if acquired:
                try:
                    redis_lock.release()
                except Exception:
                    pass
    else:
        # Fallback: threading.Lock in-memory (comportamento original)
        with _LOCK_GUARD:
            if lead_id not in _LEAD_LOCKS:
                _LEAD_LOCKS[lead_id] = threading.Lock()
            lock = _LEAD_LOCKS[lead_id]

        try:
            # Adquirir lock com timeout para evitar deadlocks
            acquired = lock.acquire(timeout=30.0)
            if not acquired:
                raise TimeoutError(f"Nao conseguiu lock para lead {lead_id} em 30s")

            yield lock

        finally:
            lock.release()


def _is_duplicate_message_id(msg_id: str, ttl_seconds: int = 60) -> bool:
    """
    Verifica se message_id já foi processado recentemente.

    Args:
        msg_id: ID da mensagem do WhatsApp
        ttl_seconds: Tempo de vida do cache

    Returns:
        True se já foi processado, False se é novo
    """
    if not msg_id:
        return False

    now = time.time()

    with _CACHE_LOCK:
        cached_time = _MESSAGE_ID_CACHE.get(msg_id)
        if cached_time and (now - cached_time) < ttl_seconds:
            # Atualizar timestamp para evitar evict prematuro
            del _MESSAGE_ID_CACHE[msg_id]
            _MESSAGE_ID_CACHE[msg_id] = now
            return True

        # Adicionar/atualizar cache
        _MESSAGE_ID_CACHE[msg_id] = now

        # Limpar cache antigo usando evict-oldest (não clear() que invalida tudo)
        while len(_MESSAGE_ID_CACHE) > _CACHE_MAX_SIZE:
            _MESSAGE_ID_CACHE.popitem(last=False)  # Remove o mais antigo

    return False


def _cleanup_old_cache(ttl_seconds: int = 60):
    """
    Limpa message_ids expirados do cache.

    Chamado periodicamente por thread separada.
    """
    now = time.time()
    old_cutoff = now - ttl_seconds

    with _CACHE_LOCK:
        # Remover entradas antigas
        expired_ids = [msg_id for msg_id, cached_time in _MESSAGE_ID_CACHE.items()
                      if cached_time < old_cutoff]
        for msg_id in expired_ids:
            _MESSAGE_ID_CACHE.pop(msg_id, None)


# Thread de limpeza automática (opcional)
def _start_cleanup_thread(interval_seconds: int = 300):
    """
    Inicia thread que limpa cache periodicamente.

    Args:
        interval_seconds: Intervalo entre limpezas
    """
    def cleanup_worker():
        while True:
            time.sleep(interval_seconds)
            try:
                _cleanup_old_cache()
            except Exception:
                # Não quebrar thread por erro de limpeza
                pass

    cleanup_thread = threading.Thread(
        target=cleanup_worker,
        daemon=True,
        name="lead_lock_cache_cleanup"
    )
    cleanup_thread.start()


# Iniciar limpeza automática ao importar
_start_cleanup_thread()


# Exportar funções principais
__all__ = [
    "_lead_lock_guard",
    "_is_duplicate_message_id",
    "_cleanup_old_cache"
]