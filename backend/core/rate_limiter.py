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


# Instancia unica compartilhada por server.py e todos os endpoints
limiter = Limiter(key_func=_user_or_ip, default_limits=["100/minute"])
