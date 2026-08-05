"""
Cache Service usando Redis para alta performance.

Suporta:
- Cache de respostas LLM (deduplicação)
- Cache de configurações de agentes
- Cache de templates de prompt
- Rate limiting distribuído
"""
import os
import json
import hashlib
import time
from typing import Any, Optional, Callable
from functools import wraps
import threading

# Redis client (lazy initialization)
_redis_client = None
_redis_lock = threading.Lock()


def _get_redis():
    """Retorna cliente Redis (lazy initialization)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return None

    with _redis_lock:
        if _redis_client is None:
            try:
                import redis
                _redis_client = redis.from_url(redis_url, decode_responses=True)
                _redis_client.ping()
                print("[CacheService] Redis conectado")
            except Exception as e:
                print(f"[CacheService] Redis não disponível: {e}")
                _redis_client = None
        return _redis_client


def _simple_hash(data: str) -> str:
    """Gera hash simples para cache keys."""
    return hashlib.sha256(data.encode()).hexdigest()[:32]


class CacheService:
    """
    Cache service com fallback para memória quando Redis não disponível.
    """

    def __init__(self, ttl_default: int = 300):
        self.ttl_default = ttl_default
        self._memory_cache: dict[str, tuple[Any, float]] = {}
        self._memory_lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Busca valor no cache."""
        # Tenta Redis primeiro
        redis = _get_redis()
        if redis:
            try:
                data = redis.get(f"fralib:{key}")
                if data:
                    return json.loads(data)
            except Exception:
                pass

        # Fallback para memória
        with self._memory_lock:
            if key in self._memory_cache:
                value, expiry = self._memory_cache[key]
                if time.time() < expiry:
                    return value
                del self._memory_cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Armazena valor no cache."""
        ttl = ttl or self.ttl_default
        expiry = time.time() + ttl

        # Tenta Redis primeiro
        redis = _get_redis()
        if redis:
            try:
                redis.setex(f"fralib:{key}", ttl, json.dumps(value))
                return True
            except Exception:
                pass

        # Fallback para memória
        with self._memory_lock:
            self._memory_cache[key] = (value, expiry)
            # Limpa cache antigo
            self._cleanup_memory()
        return True

    def delete(self, key: str) -> bool:
        """Remove valor do cache."""
        redis = _get_redis()
        if redis:
            try:
                redis.delete(f"fralib:{key}")
            except Exception:
                pass

        with self._memory_lock:
            self._memory_cache.pop(key, None)
        return True

    def _cleanup_memory(self):
        """Remove entradas expiradas do cache em memória."""
        now = time.time()
        expired = [k for k, (_, exp) in self._memory_cache.items() if now >= exp]
        for k in expired:
            del self._memory_cache[k]

    def clear_pattern(self, pattern: str) -> int:
        """Remove todas as chaves que matching um pattern."""
        count = 0
        redis = _get_redis()
        if redis:
            try:
                keys = redis.keys(f"fralib:{pattern}")
                if keys:
                    count = redis.delete(*keys)
            except Exception:
                pass

        with self._memory_lock:
            to_delete = [k for k in self._memory_cache if pattern in k]
            for k in to_delete:
                del self._memory_cache[k]
                count += 1
        return count


# Instância global
cache = CacheService()


def cached(
    key_prefix: str,
    ttl: int = 300,
    key_func: Optional[Callable] = None,
):
    """
    Decorator para cachear resultado de funções.

    Args:
        key_prefix: Prefixo da chave no cache
        ttl: Time-to-live em segundos
        key_func: Função para gerar chave customizada (default: hash dos args)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gerar chave
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_data = json.dumps({"args": str(args), "kwargs": str(kwargs)}, sort_keys=True)
                cache_key = f"{key_prefix}:{_simple_hash(key_data)}"

            # Tentar cache hit
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Executar função e cachear
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


def cached_llm_response(ttl: int = 3600):
    """
    Decorator específico para cachear respostas LLM.
    Usa hash do prompt como chave.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(prompt: str, *args, **kwargs):
            # Gerar chave baseado no prompt
            cache_key = f"llm:{_simple_hash(prompt)}"

            # Tentar cache hit
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Executar e cachear
            result = func(prompt, *args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


# Funções utilitárias
def invalidate_llm_cache():
    """Invalidate todo o cache LLM."""
    return cache.clear_pattern("llm:*")


def invalidate_agent_cache():
    """Invalidate todo o cache de agentes."""
    return cache.clear_pattern("agent:*")
