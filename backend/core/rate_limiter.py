import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def _user_or_ip(request):
    """Chave hibrida: user:<id> se autenticado (request.state.user_id), senao IP.

    O middleware em server.py popula request.state.user_id a partir do JWT
    (sem falhar quando ausente). Permite limites justos para usuarios reais
    e mantem o fallback por IP para rotas publicas.
    """
    uid = getattr(getattr(request, "state", None), "user_id", None) if hasattr(request, "state") else None
    if uid:
        return f"user:{uid}"
    return get_remote_address(request)


def _storage_uri() -> str | None:
    uri = (
        os.getenv("FRALIB_RATE_LIMIT_STORAGE_URI")
        or os.getenv("REDIS_URL")
        or ""
    ).strip()
    return uri or None


_LIMITS = ["100/minute"]
_limiter_kwargs = {
    "key_func": _user_or_ip,
    "default_limits": _LIMITS,
    # SlowAPI header injection is fragile with FastAPI response_model/cookie
    # responses and caused auth 500s in production. Keep enforcement active,
    # but do not mutate responses just to emit X-RateLimit headers.
    "headers_enabled": False,
}

_uri = _storage_uri()
if _uri:
    _limiter_kwargs.update(
        storage_uri=_uri,
        in_memory_fallback=_LIMITS,
        in_memory_fallback_enabled=True,
    )


def _create_limiter() -> Limiter:
    """Cria Limiter com fallback gracioso.

    Se o storage_uri estiver configurado mas a biblioteca ``limits`` nao
    conseguir inicializar o backend (ex.: versao do redis-py < 3.0),
    cai para armazenamento em memoria sem crashar a aplicacao.
    """
    try:
        return Limiter(**_limiter_kwargs)
    except Exception as exc:
        # Falha esperada quando o storage_uri aponta para Redis com versao
        # incompativel ou quando a lib ``limits`` nao consegue importar o
        # driver. Cai para modo memoria — funcional, so nao escala entre
        # replicas/containers.
        import warnings

        warnings.warn(
            f"[rate_limiter] Redis indisponivel ({exc}); "
            "usando armazenamento em memoria (sem compartilhamento entre processos)."
        )
        return Limiter(key_func=_user_or_ip, default_limits=_LIMITS, headers_enabled=False)


# Instancia unica compartilhada por server.py e todos os endpoints.
# Quando REDIS_URL existe, os limites deixam de ser por-processo e passam a
# funcionar entre replicas/containers. Sem Redis ou com Redis indisponivel,
# o comportamento cai para memoria sem crashar a aplicacao.
limiter = _create_limiter()
