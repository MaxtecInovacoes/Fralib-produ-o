from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hashlib
import jwt
import os
import time
from enum import Enum
from typing import Optional
from sqlalchemy import text as sa_text
from sqlalchemy.exc import ProgrammingError
from backend.core.jwt_config import get_jwt_secret, ALGORITHM, decode_jwt
try:
    from backend.core.config import is_superadmin
except Exception:
    def is_superadmin(_email: str) -> bool:
        return False


def _get_redis():
    """Retorna cliente Redis para blacklist de tokens."""
    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "").strip()
        if not redis_url:
            return None
        return redis.from_url(redis_url, decode_responses=True)
    except Exception:
        return None


def _is_token_revoked(token: str) -> bool:
    """Verifica se token está na blacklist."""
    redis = _get_redis()
    if not redis:
        return False
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return redis.exists(f"revoked_token:{token_hash}")


def revoke_token(token: str) -> None:
    """Adiciona token à blacklist até expiração.
    ATENÇÃO: Se Redis estiver indisponível, token NÃO é revogado.
    Em produção crítica, considere falhar de forma segura (raise exception).
    """
    redis = _get_redis()
    if not redis:
        # FIX: Falhar de forma SEGURA em vez de falhar silenciosamente
        # Em produção: log erro crítico e considera logout como "pendente"
        import logging
        logging.getLogger("uvicorn").critical(
            "[AUTH] CRÍTICO: Redis indisponível - token NÃO pode ser revogado! "
            f"Token hash: {hashlib.sha256(token.encode()).hexdigest()[:16]}..."
        )
        # Opção 1: Raise exception (mais seguro, mas quebra UX)
        # raise RuntimeError("Redis indisponível - token não pode ser revogado")
        # Opção 2: Retornar false para caller decidir (menos agressivo)
        return False
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        exp = payload.get("exp", 0)
    except Exception:
        exp = int(time.time()) + 86400  # Default 24h
    ttl = max(1, exp - int(time.time()))
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    redis.setex(f"revoked_token:{token_hash}", ttl, "1")
    return True

security = HTTPBearer(auto_error=False)
BLOCKED_USER_STATUSES = {"bloqueado", "suspenso", "cancelado", "inadimplente", "desativado"}
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


ROLE_HIERARCHY = {
    Role.USER: 0,
    Role.ADMIN: 1,
    Role.SUPERADMIN: 2,
}

# ✅ CORREÇÃO CRÍTICA: SECRET_KEY agora vem do .env
SECRET_KEY = get_jwt_secret()

# Engine compartilhado — importado uma vez, reutilizado em todas as requests
from backend.core.database import engine as _shared_engine

def _token_from_request(
    credentials: Optional[HTTPAuthorizationCredentials],
    request: Optional[Request],
) -> tuple[str, bool]:
    if credentials and credentials.credentials:
        return credentials.credentials, False
    if request is not None:
        token = request.cookies.get("fralib_session")
        if token:
            return token, True
    raise HTTPException(status_code=403, detail="Not authenticated")


def _verify_cookie_csrf(request: Optional[Request], used_cookie: bool) -> None:
    if not used_cookie or request is None or request.method.upper() not in UNSAFE_METHODS:
        return
    csrf_cookie = request.cookies.get("fralib_csrf") or ""
    csrf_header = request.headers.get("x-csrf-token") or request.headers.get("x-xsrf-token") or ""
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(status_code=403, detail="CSRF token invalido")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None,
):
    try:
        token, used_cookie = _token_from_request(credentials, request)
        _verify_cookie_csrf(request, used_cookie)

        # Verificar blacklist de tokens
        if _is_token_revoked(token):
            raise HTTPException(status_code=401, detail="Token revogado")

        payload = decode_jwt(token)
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")

        # Buscar role/status do banco (engine compartilhado, sem criar novo)
        role = payload.get("role", "user")
        status = ""
        tenant_id = None
        try:
            with _shared_engine.connect() as _c:
                _row = _c.execute(
                    sa_text("SELECT role, status, tenant_id FROM users WHERE id=:id"),
                    {"id": user_id},
                ).fetchone()
        except ProgrammingError as exc:
            if "tenant_id" not in str(exc).lower():
                raise
            with _shared_engine.connect() as _c:
                _row = _c.execute(
                    sa_text("SELECT role, status, id AS tenant_id FROM users WHERE id=:id"),
                    {"id": user_id},
                ).fetchone()
            if not _row:
                raise HTTPException(status_code=401, detail="Usuário não encontrado")
            if _row[0]:
                role = _row[0]
            status = (_row[1] or "").lower()
            tenant_id = _row[2]

        if not _row:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        if _row[0]:
            role = _row[0]
        status = (_row[1] or "").lower()
        tenant_id = _row[2]

        if email and is_superadmin(email):
            role = Role.SUPERADMIN.value

        if status in BLOCKED_USER_STATUSES:
            raise HTTPException(
                status_code=403,
                detail={
                    "reason": "account_blocked",
                    "message": "Conta sem permissão ativa para acessar a FraLib.",
                    "status": status,
                    "upgrade_url": "/planos",
                },
            )

        return {"id": user_id, "email": email, "role": role, "tenant_id": tenant_id or user_id}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido ou malformado")


def require_role(required_role: Role):
    async def _dependency(user: dict = Depends(get_current_user)):
        try:
            current_role = Role(user.get("role") or Role.USER)
        except ValueError:
            current_role = Role.USER
        if ROLE_HIERARCHY.get(current_role, 0) < ROLE_HIERARCHY[required_role]:
            raise HTTPException(status_code=403, detail="Acesso negado")
        return user

    return _dependency
