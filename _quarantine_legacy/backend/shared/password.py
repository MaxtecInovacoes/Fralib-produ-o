"""Password utilities — auth helpers compartilhados.

Absorvido de backend/utils/password_utils.py (removido).
"""

import hashlib
import hmac
import secrets

import bcrypt

BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Hash bcrypt seguro."""
    pw_bytes = password.encode("utf-8")[:BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verifica senha contra hash bcrypt."""
    try:
        pw_bytes = password.encode("utf-8")[:BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


def make_token() -> str:
    """Token aleatório seguro (para sessões curtas, API keys, etc)."""
    return secrets.token_urlsafe(32)


def sha256_hex(value: str) -> str:
    """SHA-256 hex digest."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hmac_sha256(secret: str, message: str) -> str:
    """HMAC-SHA256 hex."""
    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
