from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import base64, hashlib, hmac, jwt, os, secrets, struct, time
import bcrypt
from backend.utils.password_utils import verify_password, hash_password, BCRYPT_MAX_BYTES
from backend.core.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.core.auth import get_current_user, revoke_token
from rate_limiter import limiter
from backend.core.jwt_config import get_jwt_secret, ALGORITHM
from backend.core.config import SUPERADMIN_EMAILS, is_superadmin

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)
BLOCKED_USER_STATUSES = {"bloqueado", "suspenso", "cancelado", "inadimplente", "desativado"}
TRUSTED_PROXY_HOSTS = {"127.0.0.1", "::1", "localhost"}
TERMS_VERSION = "fralib-termos-v1-2026-06-08"
PRIVACY_VERSION = "fralib-privacidade-v1-2026-06-08"
COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24
GENERIC_CONFIRMATION_MESSAGE = (
    "Se a conta existir e ainda precisar de confirmacao, voce recebera um novo email."
)


def _client_ip(request: Request) -> str:
    """Resolve IP real confiando em X-Forwarded-For apenas vindo do proxy local."""
    direct_ip = request.client.host if request.client else ""
    if direct_ip in TRUSTED_PROXY_HOSTS:
        forwarded = request.headers.get("x-forwarded-for", "")
        parts = [part.strip() for part in forwarded.split(",") if part.strip()]
        if parts:
            return parts[-1]
    return direct_ip


def _inicializar_tenant(db: Session, user_id: int, nome: str, email: str, now: str, trial_expires: str):
    """
    Inicializa todos os recursos necessários para um novo tenant:
    - Diretório de sites no disco
    - Licença trial na tabela licencas
    - Config pipeline padrão
    """
    import os, secrets, pwd

    # 1. Criar diretório de sites do tenant (user_id forcado a int para evitar path injection)
    safe_uid = int(user_id)
    sites_dir = f"/var/www/fralib/sites/{safe_uid}"
    try:
        os.makedirs(sites_dir, exist_ok=True)
        try:
            www_data = pwd.getpwnam("www-data")
            for root, dirs, files in os.walk(sites_dir):
                os.chown(root, www_data.pw_uid, www_data.pw_gid)
                os.chmod(root, 0o755)
                for f in files:
                    fp = os.path.join(root, f)
                    os.chown(fp, www_data.pw_uid, www_data.pw_gid)
                    os.chmod(fp, 0o644)
        except KeyError:
            print("[Tenant Init] usuario www-data nao encontrado, pulando chown")
        print(f"[Tenant Init] Diretório criado: {sites_dir}")
    except Exception as e:
        print(f"[Tenant Init] Erro ao criar diretório: {e}")

    # 2. Criar licença trial (se não existir)
    try:
        existing_lic = db.execute(
            text("SELECT id FROM licencas WHERE email = :email"),
            {"email": email}
        ).fetchone()
        if not existing_lic:
            lic_id = secrets.token_hex(8)
            lic_chave = secrets.token_urlsafe(16)
            db.execute(text("""
                INSERT INTO licencas (id, cliente, email, plano, valor, chave, status, data, expira)
                VALUES (:id, :cliente, :email, :plano, :valor, :chave, :status, :data, :expira)
            """), {
                "id": lic_id,
                "cliente": nome,
                "email": email,
                "plano": "trial",
                "valor": 0,
                "chave": lic_chave,
                "status": "ativa",
                "data": now,
                "expira": trial_expires,
            })
            db.commit()
            print(f"[Tenant Init] Licença trial criada para user_id={user_id}")
    except Exception as e:
        print(f"[Tenant Init] Erro ao criar licença: {e}")

    # 3. Criar config_pipeline padrão (se não existir)
    try:
        existing_cfg = db.execute(
            text("SELECT id FROM config_pipeline WHERE user_id = :uid"),
            {"uid": user_id}
        ).fetchone()
        if not existing_cfg:
            db.execute(text("""
                INSERT INTO config_pipeline (user_id, nicho, cidade, pipeline_status, volume_leads_target)
                VALUES (:uid, '', '', 'parado', 10)
            """), {"uid": user_id})
            db.commit()
            print(f"[Tenant Init] Config pipeline criada para user_id={user_id}")
    except Exception as e:
        print(f"[Tenant Init] Erro ao criar config_pipeline: {e}")

SECRET_KEY = get_jwt_secret()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str = ""

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nome: str = ""
    name: str = ""
    telefone: str = ""
    accept_terms: bool = False
    accept_privacy: bool = False
    terms_version: str = TERMS_VERSION
    privacy_version: str = PRIVACY_VERSION

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(hours=24)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _cookie_secure(request: Request) -> bool:
    override = (os.getenv("FRALIB_COOKIE_SECURE") or "").strip().lower()
    if override in {"1", "true", "yes", "on"}:
        return True
    if override in {"0", "false", "no", "off"}:
        return False
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return proto == "https" or (os.getenv("FRALIB_ENV") or "").lower() == "prod"


def _set_auth_cookies(response: Response, request: Request, token: str) -> str:
    csrf_token = secrets.token_urlsafe(32)
    secure = _cookie_secure(request)
    response.set_cookie(
        "fralib_session",
        token,
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "fralib_csrf",
        csrf_token,
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )
    return csrf_token


def _normalize_totp_secret(secret_value: str) -> bytes:
    cleaned = "".join(ch for ch in (secret_value or "").strip().replace(" ", "") if ch.isalnum()).upper()
    if not cleaned:
        raise ValueError("TOTP secret vazio")
    padding = "=" * ((8 - len(cleaned) % 8) % 8)
    return base64.b32decode((cleaned + padding).encode("ascii"), casefold=True)


def _totp_code(secret_value: str, counter: int, digits: int = 6) -> str:
    key = _normalize_totp_secret(secret_value)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** digits)).zfill(digits)


def _verify_totp_code(secret_value: str, code: str, now: int | None = None, window: int = 1) -> bool:
    candidate = "".join(ch for ch in (code or "") if ch.isdigit())
    if len(candidate) != 6:
        return False
    current = int((now if now is not None else time.time()) // 30)
    for drift in range(-window, window + 1):
        if hmac.compare_digest(_totp_code(secret_value, current + drift), candidate):
            return True
    return False


def _requires_2fa_setup(role: str, email: str) -> bool:
    if (os.getenv("FRALIB_REQUIRE_2FA") or "").strip().lower() not in {"1", "true", "yes", "on"}:
        return False
    configured = {
        item.strip().lower()
        for item in (os.getenv("FRALIB_REQUIRE_2FA_ROLES") or "superadmin").split(",")
        if item.strip()
    }
    normalized_role = (role or "user").lower()
    return normalized_role in configured or is_superadmin(email)

@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(text(
        """
        SELECT id, email, password_hash, status, email_confirmado, totp_enabled, totp_secret, role
        FROM users
        WHERE email = :email
        """
    ), {"email": data.email}).fetchone()
    if not user or not verify_password(data.password, user[2]):
        raise HTTPException(status_code=401, detail="Email ou senha invalidos")
    if (user[3] or "").lower() in BLOCKED_USER_STATUSES:
        raise HTTPException(status_code=401, detail="Email ou senha invalidos")
    # Bloquear contas nao confirmadas. Codigo 403 + flag para o frontend mostrar botao de reenvio.
    if not user[4]:
        raise HTTPException(
            status_code=403,
            detail="Email nao confirmado. Verifique sua caixa de entrada ou solicite reenvio.",
            headers={"X-Require-Email-Confirmation": "1"},
        )
    if bool(user[5]):
        if not _verify_totp_code(user[6] or "", data.totp_code):
            raise HTTPException(
                status_code=401,
                detail="Codigo 2FA invalido ou ausente",
                headers={"X-Require-2FA": "1"},
            )
    elif _requires_2fa_setup(user[7] or "user", user[1] or ""):
        raise HTTPException(
            status_code=403,
            detail="2FA obrigatorio para esta conta. Configure um autenticador antes de continuar.",
            headers={"X-Require-2FA-Setup": "1"},
        )
    token = create_access_token({"sub": str(user[0]), "email": user[1]})
    response = JSONResponse(content={"access_token": token, "token_type": "bearer"})
    _set_auth_cookies(response, request, token)
    return response

@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
    from services.email_service import enviar_email_confirmacao
    if not data.accept_terms or not data.accept_privacy:
        raise HTTPException(status_code=400, detail="Voce precisa aceitar os Termos de Uso e a Politica de Privacidade/LGPD.")
    if data.email.lower().strip() in SUPERADMIN_EMAILS:
        raise HTTPException(status_code=400, detail="Email nao disponivel")
    existing = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": data.email}).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Email ja cadastrado")

    # Anti-abuse: limitar trials por IP (max 2 contas trial por IP em 30 dias)
    client_ip = _client_ip(request)
    if client_ip and client_ip not in ("127.0.0.1", "::1"):
        recent_from_ip = db.execute(text("""
            SELECT COUNT(*) FROM users
            WHERE registro_ip = :ip AND criado_em::timestamp > NOW() - INTERVAL '30 days'
        """), {"ip": client_ip}).fetchone()
        if recent_from_ip and recent_from_ip[0] >= 3:
            raise HTTPException(status_code=429, detail="Limite de cadastros atingido. Tente novamente mais tarde.")

    if len(data.password) < 12:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 12 caracteres")
    if len(data.password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Senha deve ter no maximo 72 bytes")
    if not any(c.isalpha() for c in data.password) or not any(c.isdigit() for c in data.password):
        raise HTTPException(status_code=400, detail="Senha deve conter letras e numeros")
    password_hash = hash_password(data.password)
    now = datetime.utcnow().isoformat()
    nome = data.nome or data.name or data.email.split("@")[0]
    trial_expires = (datetime.utcnow() + timedelta(days=7)).isoformat()
    confirm_token = secrets.token_urlsafe(32)
    confirm_expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    # email_confirmado=false ate o usuario clicar no link recebido por email
    telefone = (data.telefone or "").strip()
    sql = """INSERT INTO users (email, nome, name, password_hash, senha_hash, plano, plan, role, status,
              creditos, creditos_max, trial_expires_at, criado_em, email_confirmado, confirm_token, confirm_expires,
              registro_ip, telefone, terms_accepted_at, terms_version, privacy_accepted_at, privacy_version,
              legal_acceptance_ip)
              VALUES (:email, :nome, :nome, :hash, :hash, 'trial', 'free', 'user', 'trial',
              1, 1, :trial_exp, :now, false, :ctoken, :cexp,
              :ip, :tel, :now, :terms_version, :now, :privacy_version, :ip)"""
    db.execute(text(sql), {"email": data.email, "nome": nome, "hash": password_hash,
               "now": now, "trial_exp": trial_expires,
               "ctoken": confirm_token, "cexp": confirm_expires, "ip": client_ip, "tel": telefone,
               "terms_version": data.terms_version or TERMS_VERSION,
               "privacy_version": data.privacy_version or PRIVACY_VERSION})
    db.commit()

    # Inicializar tenant: buscar user_id recém criado
    new_user = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": data.email}).fetchone()
    if new_user:
        user_id = new_user[0]
        _inicializar_tenant(db, user_id, nome, data.email, now, trial_expires)

    # Enviar email de confirmacao. Se Resend falhar, o usuario pode pedir reenvio.
    email_enviado = await enviar_email_confirmacao(data.email, nome, confirm_token)

    return {
        "status": "ok",
        "mensagem": "Cadastro realizado! Verifique seu email para ativar a conta.",
        "email_enviado": email_enviado,
        "email": data.email,
    }

def _pagina_confirmacao(titulo: str, mensagem: str, sucesso: bool) -> HTMLResponse:
    cor = "#10b981" if sucesso else "#ef4444"
    icone = "&#10004;" if sucesso else "&#10006;"
    cta = '<a href="/login" style="display:inline-block;margin-top:24px;background:#7c3aed;color:#fff;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:700">IR PARA LOGIN</a>' if sucesso else ''
    html = f"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><title>{titulo} - FraLib</title><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:system-ui,sans-serif;background:#0f0f12;color:#e5e7eb;margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px">
  <div style="max-width:480px;background:#1a1a1f;border:1px solid #2a2a30;border-radius:16px;padding:48px 32px;text-align:center">
    <div style="font-size:64px;color:{cor};line-height:1;margin-bottom:16px">{icone}</div>
    <h1 style="margin:0 0 12px 0;font-size:24px">{titulo}</h1>
    <p style="margin:0;color:#9ca3af;line-height:1.5">{mensagem}</p>
    {cta}
  </div>
</body></html>"""
    return HTMLResponse(content=html, status_code=200 if sucesso else 400)


@router.get("/confirmar-email")
@limiter.limit("10/minute")
async def confirmar_email(request: Request, token: str, db: Session = Depends(get_db)):
    user = db.execute(text("SELECT id, confirm_expires FROM users WHERE confirm_token = :token"), {"token": token}).fetchone()
    if not user:
        return _pagina_confirmacao("Link invalido", "Este link de confirmacao ja foi usado ou nao existe.", sucesso=False)
    if user[1]:
        expires = user[1] if isinstance(user[1], datetime) else datetime.fromisoformat(user[1])
        now = datetime.utcnow()
        if expires.tzinfo: expires = expires.replace(tzinfo=None)
        if now > expires:
            return _pagina_confirmacao("Link expirado", "Este link expirou. Faca login para solicitar um novo email de confirmacao.", sucesso=False)
    db.execute(text("UPDATE users SET email_confirmado=true, confirm_token=NULL, confirm_expires=NULL WHERE id=:id"), {"id": user[0]})
    db.commit()
    return _pagina_confirmacao("Email confirmado!", "Sua conta foi ativada. Agora voce pode fazer login.", sucesso=True)

@router.post("/reenviar-confirmacao")
@limiter.limit("3/minute")
async def reenviar_confirmacao(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    """
    Reenvia email de confirmação.
    SECURITY: Todos os caminhos de erro tomam tempo igual para previnir timing attacks.
    """
    from services.email_service import enviar_email_confirmacao

    # Sempre executa verify_password com hash real ou dummy para timing constant
    dummy_hash = bcrypt.hashpw(b"dummy_password_does_not_match", bcrypt.gensalt())
    user = db.execute(
        text("SELECT id, nome, email_confirmado, password_hash, status FROM users WHERE email = :email"),
        {"email": data.email},
    ).fetchone()

    # Usa sempre o hash do usuário (ou dummy se não existir) para timing constant
    actual_hash = user[3] if user else dummy_hash
    verify_password(data.password, actual_hash)  # Tempo constante

    # Verificações de status após verify_password (nunca retornamos cedo)
    user_exists_and_eligible = (
        user
        and user[3]  # tem senha
        and (user[4] or "").lower() not in BLOCKED_USER_STATUSES
        and not user[2]  # email não confirmado
        and verify_password(data.password, user[3])  # senha correta
    )

    if user_exists_and_eligible:
        confirm_token = secrets.token_urlsafe(32)
        confirm_expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        db.execute(text("UPDATE users SET confirm_token=:token, confirm_expires=:expires WHERE id=:id"),
                   {"token": confirm_token, "expires": confirm_expires, "id": user[0]})
        db.commit()
        try:
            await enviar_email_confirmacao(data.email, user[1] or data.email, confirm_token)
        except Exception:
            pass  # Não revela se email foi enviado ou não

    # Sempre retorna a mesma mensagem (timing attack prevention)
    return {"status": "ok", "mensagem": GENERIC_CONFIRMATION_MESSAGE}

class EsqueciSenhaRequest(BaseModel):
    email: EmailStr

class ResetarSenhaRequest(BaseModel):
    token: str
    password: str

@router.post("/esqueci-senha")
@limiter.limit("3/minute")
async def esqueci_senha(request: Request, data: EsqueciSenhaRequest, db: Session = Depends(get_db)):
    from services.email_service import enviar_email_recuperacao
    user = db.execute(text(
        "SELECT id, nome FROM users WHERE lower(email) = lower(:email) AND status != 'desativado'"
    ), {"email": data.email}).fetchone()
    # Sempre retorna sucesso para não vazar se o email existe
    if not user:
        return {"status": "ok", "mensagem": "Se o email estiver cadastrado, voce recebera um link de recuperacao."}
    reset_token = secrets.token_urlsafe(32)
    reset_expires = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    db.execute(text(
        "UPDATE users SET reset_token=:token, reset_expires=:expires WHERE id=:id"
    ), {"token": reset_token, "expires": reset_expires, "id": user[0]})
    db.commit()
    try:
        result = await enviar_email_recuperacao(data.email, user[1] or data.email, reset_token)
        print(f"[Auth] Email recuperacao para {data.email}: {'ENVIADO' if result else 'FALHOU'}")
    except Exception as e:
        print(f"[Auth] Erro ao enviar email recuperacao: {e}")
    return {"status": "ok", "mensagem": "Se o email estiver cadastrado, voce recebera um link de recuperacao."}

@router.post("/resetar-senha")
@limiter.limit("5/minute")
async def resetar_senha(request: Request, data: ResetarSenhaRequest, db: Session = Depends(get_db)):
    user = db.execute(text(
        "SELECT id, reset_expires FROM users WHERE reset_token = :token"
    ), {"token": data.token}).fetchone()
    if not user:
        raise HTTPException(status_code=400, detail="Link invalido ou ja utilizado.")
    if user[1]:
        expires = user[1] if isinstance(user[1], datetime) else datetime.fromisoformat(user[1])
        now = datetime.utcnow()
        if expires.tzinfo: expires = expires.replace(tzinfo=None)
        if now > expires:
            raise HTTPException(status_code=400, detail="Link expirado. Solicite um novo.")
    if len(data.password) < 12:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 12 caracteres")
    if len(data.password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Senha deve ter no maximo 72 bytes")
    if not any(c.isalpha() for c in data.password) or not any(c.isdigit() for c in data.password):
        raise HTTPException(status_code=400, detail="Senha deve conter letras e numeros")
    new_hash = hash_password(data.password)
    db.execute(text(
        "UPDATE users SET password_hash=:hash, senha_hash=:hash, reset_token=NULL, reset_expires=NULL WHERE id=:id"
    ), {"hash": new_hash, "id": user[0]})
    db.commit()
    return {"status": "ok", "mensagem": "Senha alterada com sucesso! Faca login com a nova senha."}

@router.get("/me")
async def get_me(usuario: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = usuario.get("id")
    row = db.execute(text("SELECT id, email, status, role FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    if not row or (row[2] or "").lower() in BLOCKED_USER_STATUSES:
        raise HTTPException(status_code=401, detail="Conta inativa")
    email = row[1] or ""
    role = row[3] or "user"
    return {"email": email, "user_id": row[0], "role": role, "is_superadmin": is_superadmin(email)}


@router.post("/logout")
async def logout(request: Request, response: Response, usuario: dict = Depends(get_current_user)):
    # Extrair token para revogar
    token = request.cookies.get("fralib_session") or ""
    if token:
        revoke_token(token)
    secure = _cookie_secure(request)
    for cookie_name in ("fralib_session", "fralib_csrf"):
        response.delete_cookie(cookie_name, path="/", secure=secure, samesite="lax")
    return {"status": "ok"}

@router.get("/2fa/status")
@limiter.limit("30/minute")
async def twofa_status(request: Request, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    row = db.execute(text("SELECT totp_enabled FROM users WHERE id=:id"), {"id": usuario["id"]}).fetchone()
    enabled = bool(row[0]) if row else False
    return {"enabled": enabled, "configured": enabled}

@router.post("/2fa/disable")
@limiter.limit("5/minute")
async def twofa_disable(request: Request, data: dict, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Desabilitar 2FA requer senha atual para prevenir desativação por atacante."""
    current_password = data.get("current_password")
    if not current_password:
        raise HTTPException(status_code=400, detail="Senha atual obrigatória")

    # Verifica senha atual
    row = db.execute(text("SELECT password_hash FROM users WHERE id=:id"), {"id": usuario["id"]}).fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=400, detail="Conta sem senha configurada")
    if not verify_password(current_password, row[0]):
        raise HTTPException(status_code=401, detail="Senha incorreta")

    db.execute(text("UPDATE users SET totp_enabled=false, totp_secret=NULL WHERE id=:id"), {"id": usuario["id"]})
    db.commit()
    return {"status": "ok", "mensagem": "2FA desativado"}


# ============================================================
# Google OAuth SSO
# ============================================================

@router.get("/oauth/google")
@limiter.limit("10/minute")
async def google_oauth_redirect(request: Request):
    """
    Redireciona para Google OAuth.
    Configure GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no .env.
    Usa 'state' parameter para previnir CSRF.
    """
    import os

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise HTTPException(503, "Google OAuth não configurado. Configure GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no .env")

    # CSRF protection: state parameter com valor único
    state = secrets.token_urlsafe(32)

    # URL de autorização Google
    from urllib.parse import urlencode
    params = {
        "client_id": client_id,
        "redirect_uri": os.getenv("FRALIB_PUBLIC_URL", "https://seunegociofralib.site") + "/api/auth/oauth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": state,  # CSRF protection
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    return {"redirect_url": auth_url, "state": state}  # Frontend deve usar este state

    return {"redirect_url": auth_url}


@router.get("/oauth/google/callback")
@limiter.limit("10/minute")
async def google_oauth_callback(request: Request, code: str, state: str = None, db: Session = Depends(get_db)):
    """
    Callback do Google OAuth.
    Troca code por tokens e cria/busca usuário.
    Valida 'state' parameter para previnir CSRF.
    """
    import os
    import requests

    # CSRF validation: state é obrigatório
    if not state:
        raise HTTPException(400, "State parameter obrigatório para previnir CSRF")

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    public_url = os.getenv("FRALIB_PUBLIC_URL", "https://seunegociofralib.site")

    if not client_id or not client_secret:
        raise HTTPException(503, "Google OAuth não configurado")

    # Troca code por tokens
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": public_url + "/api/auth/oauth/google/callback",
        "grant_type": "authorization_code",
    }

    try:
        token_response = requests.post(token_url, data=token_data, timeout=10)
        token_response.raise_for_status()
        tokens = token_response.json()
    except Exception as e:
        raise HTTPException(400, f"Erro ao trocar código: {e}")

    access_token = tokens.get("access_token")

    # Busca informações do usuário
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_response = requests.get(userinfo_url, headers=headers, timeout=10)
    user_response.raise_for_status()
    user_info = user_response.json()

    email = user_info.get("email")
    name = user_info.get("name", "")
    google_id = user_info.get("id")

    if not email:
        raise HTTPException(400, "Email não retornado pelo Google")

    # Verifica se usuário existe
    existing = db.execute(
        text("SELECT id, status FROM users WHERE email = :email"),
        {"email": email}
    ).fetchone()

    if existing:
        user_id = existing[0]
        status = existing[1] or ""
        if status.lower() in BLOCKED_USER_STATUSES:
            raise HTTPException(403, "Conta inativa")
    else:
        # Cria novo usuário via Google OAuth
        now = datetime.utcnow()
        trial_expires = (now + timedelta(days=7)).isoformat()
        confirm_token = secrets.token_urlsafe(32)
        confirm_expires = (now + timedelta(hours=24)).isoformat()

        user_id = db.execute(
            text("""
                INSERT INTO users (email, nome, status, plano, data_cadastro, trial_expira, google_id, email_confirmado, confirm_token, confirm_expires)
                VALUES (:email, :nome, 'pendente', 'trial', :now, :trial_expires, :google_id, false, :confirm_token, :confirm_expires)
                RETURNING id
            """),
            {
                "email": email,
                "nome": name,
                "now": now,
                "trial_expires": trial_expires,
                "google_id": google_id,
                "confirm_token": confirm_token,
                "confirm_expires": confirm_expires,
            }
        ).fetchone()[0]
        db.commit()

        # Envia email de confirmação
        try:
            from services.email_service import enviar_email_confirmacao
            await enviar_email_confirmacao(email, name or email, confirm_token)
        except Exception as e:
            print(f"[OAuth] Erro ao enviar email confirmação: {e}")

    # Verifica se email foi confirmado
    row = db.execute(text("SELECT email_confirmado, status FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    if row and (not row[0] or row[1].lower() == 'pendente'):
        return {
            "status": "email_confirmation_required",
            "message": "Email não confirmado. Verifique sua caixa de entrada.",
            "user_id": user_id,
            "auth_method": "google",
        }

    # Gera JWT
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    jwt_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "email": email,
        "user_id": user_id,
        "auth_method": "google",
    }


@router.get("/oauth/google/config")
async def google_oauth_config_status():
    """Retorna status da configuração Google OAuth."""
    import os
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    return {
        "enabled": bool(client_id),
        "configured": bool(client_id and os.getenv("GOOGLE_CLIENT_SECRET")),
        "message": "Google OAuth configurado" if client_id else "Configure GOOGLE_CLIENT_ID no .env",
    }
