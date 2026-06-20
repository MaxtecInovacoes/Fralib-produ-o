import os

MIN_JWT_SECRET_BYTES = 32
ALGORITHM = "HS256"


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "")
    if not secret:
        raise ValueError("JWT_SECRET_KEY nao configurado no .env")
    if len(secret.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
        raise ValueError(
            f"JWT_SECRET_KEY inseguro: minimo {MIN_JWT_SECRET_BYTES} bytes (atual={len(secret.encode('utf-8'))})"
        )
    return secret

