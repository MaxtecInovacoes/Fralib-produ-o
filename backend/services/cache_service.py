"""
Cache Service usando Redis para alta performance.

Suporta:
- Cache de respostas LLM (deduplicação)
- Cache de configurações de agentes
- Cache de templates de prompt
- Rate limiting distribuído

SEGURANÇA: Todas as chaves incluem tenant_id/user_id para isolamento multi-tenant.
Cache keys seguem o formato: fralib:{tenant_id}:{resource}:{hash}
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

# Prefixo global do namespace
CACHE_PREFIX = "fralib"


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


def _build_cache_key(tenant_id: Optional[int], resource: str, key_suffix: str) -> str:
    """
    Constrói chave de cache com isolamento por tenant.

    Args:
        tenant_id: ID do tenant (None para cache global)
        resource: Tipo de recurso (llm, agent, prompt, etc)
        key_suffix: Sufixo único (hash ou identificador)

    Returns:
        Chave no formato: fralib:{tenant_id}:{resource}:{key_suffix}
    """
    tenant_part = str(tenant_id) if tenant_id is not None else "global"
    return f"{CACHE_PREFIX}:{tenant_part}:{resource}:{key_suffix}"


class CacheService:
    """
    Cache service com fallback para memória quando Redis não disponível.

    SEGURANÇA: Todas as operações são isoladas por tenant via _build_cache_key.
    """

    def __init__(self, ttl_default: int = 300):
        self.ttl_default = ttl_default
        self._memory_cache: dict[str, tuple[Any, float]] = {}
        self._memory_lock = threading.Lock()

    def _key(self, tenant_id: Optional[int], resource: str, key_suffix: str) -> str:
        """Constrói chave isolada por tenant."""
        return _build_cache_key(tenant_id, resource, key_suffix)

    def get(self, tenant_id: Optional[int], resource: str, key_suffix: str) -> Optional[Any]:
        """
        Busca valor no cache com isolamento por tenant.

        Args:
            tenant_id: ID do tenant (None para cache global)
            resource: Tipo de recurso (llm, agent, etc)
            key_suffix: Sufixo único da chave
        """
        full_key = self._key(tenant_id, resource, key_suffix)

        # Tenta Redis primeiro
        redis = _get_redis()
        if redis:
            try:
                data = redis.get(full_key)
                if data:
                    return json.loads(data)
            except Exception:
                pass

        # Fallback para memória
        with self._memory_lock:
            if full_key in self._memory_cache:
                value, expiry = self._memory_cache[full_key]
                if time.time() < expiry:
                    return value
                del self._memory_cache[full_key]
        return None

    def set(self, tenant_id: Optional[int], resource: str, key_suffix: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Armazena valor no cache com isolamento por tenant.

        Args:
            tenant_id: ID do tenant (None para cache global)
            resource: Tipo de recurso
            key_suffix: Sufixo único da chave
            value: Valor a cachear
            ttl: Time-to-live em segundos
        """
        ttl = ttl or self.ttl_default
        expiry = time.time() + ttl
        full_key = self._key(tenant_id, resource, key_suffix)

        # Tenta Redis primeiro
        redis = _get_redis()
        if redis:
            try:
                redis.setex(full_key, ttl, json.dumps(value))
                return True
            except Exception:
                pass

        # Fallback para memória
        with self._memory_lock:
            self._memory_cache[full_key] = (value, expiry)
            # Limpa cache antigo
            self._cleanup_memory()
        return True

    def delete(self, tenant_id: Optional[int], resource: str, key_suffix: str) -> bool:
        """Remove valor do cache com isolamento por tenant."""
        full_key = self._key(tenant_id, resource, key_suffix)

        redis = _get_redis()
        if redis:
            try:
                redis.delete(full_key)
            except Exception:
                pass

        with self._memory_lock:
            self._memory_cache.pop(full_key, None)
        return True

    def _cleanup_memory(self):
        """Remove entradas expiradas do cache em memória."""
        now = time.time()
        expired = [k for k, (_, exp) in self._memory_cache.items() if now >= exp]
        for k in expired:
            del self._memory_cache[k]

    def clear_pattern(self, tenant_id: Optional[int], pattern: str) -> int:
        """
        Remove todas as chaves que matching um pattern (por tenant).

        Args:
            tenant_id: ID do tenant (None para todos os tenants)
            pattern: Pattern a remover (sem prefixo)
        """
        count = 0
        redis = _get_redis()

        # Construir pattern completo com tenant
        if tenant_id is not None:
            full_pattern = f"{CACHE_PREFIX}:{tenant_id}:{pattern}"
        else:
            full_pattern = f"{CACHE_PREFIX}:*:{pattern}"

        if redis:
            try:
                keys = redis.keys(full_pattern)
                if keys:
                    count = redis.delete(*keys)
            except Exception:
                pass

        with self._memory_lock:
            # Para memory cache, precisamos iterar
            if tenant_id is not None:
                prefix = f"{CACHE_PREFIX}:{tenant_id}:{pattern.replace('*', '')}"
                to_delete = [k for k in self._memory_cache if k.startswith(prefix)]
            else:
                suffix = pattern.replace('*', '')
                to_delete = [k for k in self._memory_cache if suffix in k]
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
    tenant_id_func: Optional[Callable] = None,
):
    """
    Decorator para cachear resultado de funções com isolamento por tenant.

    Args:
        key_prefix: Prefixo da chave no cache (resource type)
        ttl: Time-to-live em segundos
        key_func: Função para gerar chave customizada (default: hash dos args)
        tenant_id_func: Função para extrair tenant_id dos args (default: None = global)

    SEGURANÇA: Se tenant_id_func for fornecida, o cache é isolado por tenant.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extrair tenant_id se função fornecida
            tid = None
            if tenant_id_func:
                try:
                    tid = tenant_id_func(*args, **kwargs)
                except Exception:
                    pass

            # Gerar chave
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_data = json.dumps({"args": str(args), "kwargs": str(kwargs)}, sort_keys=True)
                cache_key = _simple_hash(key_data)

            # Tentar cache hit
            cached_value = cache.get(tid, key_prefix, cache_key)
            if cached_value is not None:
                return cached_value

            # Executar função e cachear
            result = func(*args, **kwargs)
            cache.set(tid, key_prefix, cache_key, result, ttl)
            return result
        return wrapper
    return decorator


def cached_llm_response(ttl: int = 3600, tenant_id_func: Optional[Callable] = None):
    """
    Decorator específico para cachear respostas LLM com isolamento por tenant.

    Args:
        ttl: Time-to-live em segundos
        tenant_id_func: Função para extrair tenant_id dos args
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(prompt: str, *args, tenant_id: Optional[int] = None, **kwargs):
            # Tentar extrair tenant_id da kwargs ou da função
            if tenant_id_func:
                try:
                    tenant_id = tenant_id_func(*args, **kwargs)
                except Exception:
                    tenant_id = None

            # Gerar chave baseado no prompt
            cache_key = f"llm:{_simple_hash(prompt)}"

            # Tentar cache hit
            cached_value = cache.get(tenant_id, "llm", cache_key)
            if cached_value is not None:
                return cached_value

            # Executar e cachear
            result = func(prompt, *args, tenant_id=tenant_id, **kwargs)
            cache.set(tenant_id, "llm", cache_key, result, ttl)
            return result
        return wrapper
    return decorator


# Funções utilitárias
def invalidate_llm_cache(tenant_id: Optional[int] = None):
    """Invalidate o cache LLM (por tenant se especificado)."""
    return cache.clear_pattern(tenant_id, "llm:*")


def invalidate_agent_cache(tenant_id: Optional[int] = None):
    """Invalidate o cache de agentes (por tenant se especificado)."""
    return cache.clear_pattern(tenant_id, "agent:*")


def invalidate_all_cache(tenant_id: Optional[int] = None):
    """Invalidate todo o cache (por tenant se especificado)."""
    return cache.clear_pattern(tenant_id, "*")
