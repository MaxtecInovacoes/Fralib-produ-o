import os

MIN_JWT_SECRET_BYTES = 32
ALGORITHM = "HS256"
# Leeway em segundos para tolerar clock skew entre servidores (default: 5 minutos)
JWT_LEEWAY_SECONDS = 300


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "")
    if not secret:
        raise ValueError("JWT_SECRET_KEY nao configurado no .env")
    if len(secret.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
        raise ValueError(
            f"JWT_SECRET_KEY inseguro: minimo {MIN_JWT_SECRET_BYTES} bytes (atual={len(secret.encode('utf-8'))})"
        )
    return secret


def decode_jwt(token: str) -> dict:
    """Decode JWT with leeway for clock skew."""
    import jwt as pyjwt
    secret = get_jwt_secret()
    return pyjwt.decode(
        token,
        secret,
        algorithms=[ALGORITHM],
        leeway=JWT_LEEWAY_SECONDS,
    )

