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
- RE TRY: Tenta 3x com backoff exponencial antes de falhar
- AUTO-RECOVERY: Health check tenta reconectar automaticamente
- FAIL-CLOSED: Se todas tentativas falharem, retorna erro
"""

import os
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from typing import Dict, Optional

import redis

# ============================================================
# Configuração
# ============================================================

REDIS_RETRY_COUNT = 3
REDIS_RETRY_BASE_DELAY = 0.5  # segundos (0.5, 1, 2 = backoff exponencial)
REDIS_RECOVERY_INTERVAL = 10  # segundos entre tentativas de recovery

# ============================================================
# Redis Client com auto-recovery
# ============================================================

_redis_client: Optional[redis.Redis] = None
_redis_lock = threading.Lock()
_redis_available: bool = False
_last_error: Optional[str] = None
_last_reconnectattempt: float = 0
_in_recovery_mode: bool = False


def _connect_redis() -> bool:
    """Tenta conectar ao Redis. Retorna True se berhasil."""
    global _redis_client, _redis_available, _last_error, _in_recovery_mode

    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        _last_error = "REDIS_URL nao configurado"
        return False

    try:
        import redis as redis_lib
        client = redis_lib.from_url(redis_url, decode_responses=True)
        client.ping()
        _redis_client = client
        _redis_available = True
        _in_recovery_mode = False
        _last_error = None
        print(f"[lead_lock] Redis conectado - lock distribuido ativo")
        return True
    except Exception as e:
        _last_error = str(e)
        _redis_available = False
        print(f"[lead_lock] Redis nao disponivel: {e}")
        return False


def get_redis_client() -> Optional[redis.Redis]:
    """
    Retorna cliente Redis. Se offline, tenta reconectar automaticamente.

    Returns:
        redis.Redis se disponível, None caso contrário
    """
    global _redis_client, _redis_available, _in_recovery_mode, _last_reconnectattempt

    # Se já tem cliente e está disponível, retorna
    if _redis_available and _redis_client:
        try:
            _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_available = False
            _in_recovery_mode = True

    # Está em recovery mode - não tenta reconectar muito rápido
    if _in_recovery_mode:
        now = time.time()
        if now - _last_reconnectattempt < REDIS_RECOVERY_INTERVAL:
            return None
        _last_reconnectattempt = now

    # Tenta reconectar
    if _connect_redis():
        return _redis_client

    _in_recovery_mode = True
    return None


def is_redis_available() -> bool:
    """Retorna status do Redis (sem tentar reconectar)."""
    return _redis_available


def get_redis_status() -> dict:
    """Retorna status detalhado do Redis para health check."""
    return {
        "available": _redis_available,
        "in_recovery_mode": _in_recovery_mode,
        "last_error": _last_error,
        "retry_count": REDIS_RETRY_COUNT,
        "retry_base_delay": REDIS_RETRY_BASE_DELAY,
    }


def force_redis_reconnect() -> bool:
    """Força tentativa de reconexão ao Redis."""
    global _redis_client, _redis_available, _in_recovery_mode, _last_reconnectattempt
    _redis_client = None
    _redis_available = False
    _in_recovery_mode = True
    _last_reconnectattempt = 0
    return _connect_redis()


# Inicializa conexão
_connect_redis()


# ============================================================
# Lock Guard com retry e fail-closed
# ============================================================

@contextmanager
def _lead_lock_guard(lead_id: str):
    """
    Garante que só 1 thread/processo por vez possa processar um lead.

    Estrategy:
    1. Tenta adquirir lock Redis com retry 3x (backoff exponencial)
    2. Se todas tentativas falharem, FAIL-CLOSED (lança exceção)

    Args:
        lead_id: Identificador único do lead

    Raises:
        RuntimeError: Se não conseguir lock após 3 tentativas
    """
    redis_client = get_redis_client()

    if not redis_client:
        raise RuntimeError(
            f"[lead_lock] Redis offline para lead {lead_id}. "
            f"Tentativas: 0/{REDIS_RETRY_COUNT}. "
            "Aguarde recovery automatico ou contate DevOps."
        )

    lock_key = f"fralib:lead_lock:{lead_id}"
    redis_lock = redis_client.lock(
        lock_key,
        timeout=60.0,
        blocking_timeout=60.0,
    )

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
                last_error = f"Timeout ao adquirir lock (tentativa {attempt}/{REDIS_RETRY_COUNT})"
        except Exception as e:
            last_error = str(e)
            # Tenta reconectar se perdeu conexão
            redis_client = get_redis_client()
            if redis_client:
                redis_lock = redis_client.lock(lock_key, timeout=60.0, blocking_timeout=60.0)
            else:
                redis_lock = None

        # Se não é última tentativa, espera com backoff
        if attempt < REDIS_RETRY_COUNT:
            delay = REDIS_RETRY_BASE_DELAY * (2 ** (attempt - 1))
            time.sleep(delay)

    # Todas tentativas falharam
    raise RuntimeError(
        f"[lead_lock] Falha ao adquirir lock para lead {lead_id} apos "
        f"{REDIS_RETRY_COUNT} tentativas. Ultimo erro: {last_error}. "
        "FAIL-CLOSED: mensagem nao processada para evitar duplicatas."
    )


# ============================================================
# Lock Cache (para uso futuro se necessário)
# ============================================================

_LEAD_LOCKS: Dict[str, threading.Lock] = {}
_LOCK_GUARD = threading.Lock()

# Cache de message_ids recentes (TTL 60s)
_MESSAGE_ID_CACHE: "OrderedDict[str, float]" = OrderedDict()
_CACHE_LOCK = threading.Lock()
_CACHE_MAX_SIZE = 10000


def _is_duplicate_message_id(msg_id: str, ttl_seconds: int = 60) -> bool:
    """Verifica se message_id já foi processado recentemente."""
    if not msg_id:
        return False

    now = time.time()

    with _CACHE_LOCK:
        cached_time = _MESSAGE_ID_CACHE.get(msg_id)
        if cached_time and (now - cached_time) < ttl_seconds:
            del _MESSAGE_ID_CACHE[msg_id]
            _MESSAGE_ID_CACHE[msg_id] = now
            return True

        _MESSAGE_ID_CACHE[msg_id] = now

        while len(_MESSAGE_ID_CACHE) > _CACHE_MAX_SIZE:
            _MESSAGE_ID_CACHE.popitem(last=False)

    return False


def _cleanup_old_cache(ttl_seconds: int = 60):
    """Limpa message_ids expirados do cache."""
    now = time.time()
    old_cutoff = now - ttl_seconds

    with _CACHE_LOCK:
        expired_ids = [
            msg_id for msg_id, cached_time in _MESSAGE_ID_CACHE.items()
            if cached_time < old_cutoff
        ]
        for msg_id in expired_ids:
            _MESSAGE_ID_CACHE.pop(msg_id, None)


def _start_cleanup_thread(interval_seconds: int = 300):
    """Inicia thread que limpa cache periodicamente."""
    def cleanup_worker():
        while True:
            time.sleep(interval_seconds)
            try:
                _cleanup_old_cache()
            except Exception:
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
    "is_redis_available",
    "get_redis_status",
    "force_redis_reconnect",
]
