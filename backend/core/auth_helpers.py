"""
Helpers de autenticacao e URLs — shared entre endpoints de checkout e créditos.

Extraído de credits_endpoints.py para quebrar dependencia circular.
"""
import os

from fastapi import HTTPException, Request
from sqlalchemy import text as _text


def _app_url() -> str:
    return (
        os.getenv("APP_URL")
        or os.getenv("FRALIB_PUBLIC_URL")
        or "https://fralib.com"
    ).rstrip("/")


def _notification_url() -> str | None:
    app_url = _app_url()
    if "localhost" in app_url or "127.0.0.1" in app_url:
        return None
    return f"{app_url}/api/credits/webhook/cakto"


def _extrair_usuario_request(request: Request) -> dict:
    """Extrai usuario do cookie fralib_session OU Authorization Bearer token.
    Levanta HTTPException 401 se nao autenticado.
    """
    from backend.core.database import engine
    from backend.core.auth import _token_from_request, _verify_cookie_csrf
    from backend.core.jwt_config import ALGORITHM
    from backend.core.auth import SECRET_KEY as _SECRET_KEY
    import jwt as _jwt

    auth = request.headers.get("Authorization", "")
    credentials = None
    if auth.startswith("Bearer "):
        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=auth[7:])

    try:
        token, used_cookie = _token_from_request(credentials, request)
    except HTTPException:
        raise HTTPException(401, "Autenticacao necessaria para checkout.")

    if used_cookie:
        try:
            _verify_cookie_csrf(request, used_cookie)
        except HTTPException:
            raise HTTPException(401, "CSRF token invalido")

    try:
        payload = _jwt.decode(token, _SECRET_KEY, algorithms=[ALGORITHM])
    except Exception as exc:
        raise HTTPException(401, f"Token invalido: {exc}")
    user_id_raw = payload.get("sub")
    try:
        user_id = int(user_id_raw) if user_id_raw is not None else None
    except (TypeError, ValueError):
        user_id = None
    email = payload.get("email")
    if not user_id:
        raise HTTPException(401, "Token sem user_id")

    try:
        user_dict = None
        try:
            with engine.connect() as _c1:
                _row1 = _c1.execute(
                    _text("SELECT id, email, plano, status, creditos, creditos_max, role, tenant_id, access, trial_ends_at, current_plan_id FROM users WHERE id=:id"),
                    {"id": int(user_id)},
                ).fetchone()
                if _row1:
                    user_dict = {
                        "id": int(_row1[0]),
                        "email": _row1[1],
                        "plano": _row1[2],
                        "status": _row1[3],
                        "creditos": _row1[4],
                        "creditos_max": _row1[5],
                        "role": _row1[6],
                        "tenant_id": _row1[7],
                        "access": _row1[8] or "released",
                        "trial_ends_at": _row1[9],
                        "current_plan_id": _row1[10],
                    }
        except Exception:
            pass
        if not user_dict:
            try:
                with engine.connect() as _c2:
                    _row2 = _c2.execute(
                        _text("SELECT id, email, plano, status, creditos, creditos_max, role, access, trial_ends_at, current_plan_id FROM users WHERE id=:id"),
                        {"id": int(user_id)},
                    ).fetchone()
                    if _row2:
                        user_dict = {
                            "id": int(_row2[0]),
                            "email": _row2[1],
                            "plano": _row2[2],
                            "status": _row2[3],
                            "creditos": _row2[4],
                            "creditos_max": _row2[5],
                            "role": _row2[6],
                            "tenant_id": None,
                            "access": _row2[7] or "released",
                            "trial_ends_at": _row2[8],
                            "current_plan_id": _row2[9],
                        }
            except Exception:
                pass
        if not user_dict:
            raise HTTPException(401, "Usuario nao encontrado")
        return {
            "id": int(user_dict.get("id")),
            "email": user_dict.get("email") or email,
            "plano": user_dict.get("plano") or "trial",
            "status": user_dict.get("status") or "ativo",
            "creditos": user_dict.get("creditos") or 0,
            "creditos_max": user_dict.get("creditos_max") or 5,
            "role": user_dict.get("role") or "user",
            "tenant_id": user_dict.get("tenant_id"),
            "access": user_dict.get("access") or "released",
            "trial_ends_at": user_dict.get("trial_ends_at"),
            "current_plan_id": user_dict.get("current_plan_id"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(401, f"Erro ao carregar usuario: {exc}")
