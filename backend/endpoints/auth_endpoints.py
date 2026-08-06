from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import jwt, secrets, os
from utils.password_utils import verify_password, hash_password
from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text
from auth import get_current_user
from rate_limiter import limiter
from core.config import SUPERADMIN_EMAILS

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


def _inicializar_tenant(db: Session, user_id: int, nome: str, email: str, now: str, trial_expires: str):
    """
    Inicializa todos os recursos necessários para um novo tenant:
    - Diretório de sites no disco
    - Licença trial na tabela licencas
    - Config pipeline padrão
    """
    import os, secrets, shutil, pwd, stat

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

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY nao configurado")
ALGORITHM = "HS256"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nome: str = ""
    name: str = ""
    telefone: str = ""

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(hours=24)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(text(
        "SELECT id, email, password_hash, status, email_confirmado FROM users WHERE LOWER(email) = LOWER(:email)"
    ), {"email": data.email}).fetchone()
    if not user or not verify_password(data.password, user[2]):
        raise HTTPException(status_code=401, detail="Email ou senha invalidos")
    if user[3] == "desativado":
        raise HTTPException(status_code=401, detail="Email ou senha invalidos")
    # Bloquear contas nao confirmadas. Codigo 403 + flag para o frontend mostrar botao de reenvio.
    if not user[4]:
        raise HTTPException(
            status_code=403,
            detail="Email nao confirmado. Verifique sua caixa de entrada ou solicite reenvio.",
            headers={"X-Require-Email-Confirmation": "1"},
        )
    token = create_access_token({"sub": str(user[0]), "email": user[1]})
    return TokenResponse(access_token=token)

@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
    from services.email_service import enviar_email_confirmacao
    if data.email.lower().strip() in SUPERADMIN_EMAILS:
        raise HTTPException(status_code=400, detail="Email nao disponivel")
    existing = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": data.email}).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Email ja cadastrado")

    # Anti-abuse: limitar trials por IP (max 2 contas trial por IP em 30 dias)
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or request.client.host
    if client_ip and client_ip not in ("127.0.0.1", "::1"):
        recent_from_ip = db.execute(text("""
            SELECT COUNT(*) FROM users
            WHERE registro_ip = :ip AND criado_em::timestamp > NOW() - INTERVAL '30 days'
        """), {"ip": client_ip}).fetchone()
        if recent_from_ip and recent_from_ip[0] >= 3:
            raise HTTPException(status_code=429, detail="Limite de cadastros atingido. Tente novamente mais tarde.")

    if len(data.password) < 12:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 12 caracteres")
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
              creditos, creditos_max, trial_expires_at, criado_em, email_confirmado, confirm_token, confirm_expires, registro_ip, telefone)
              VALUES (:email, :nome, :nome, :hash, :hash, 'trial', 'free', 'user', 'trial',
              1, 1, :trial_exp, :now, false, :ctoken, :cexp, :ip, :tel)"""
    db.execute(text(sql), {"email": data.email, "nome": nome, "hash": password_hash,
               "now": now, "trial_exp": trial_expires,
               "ctoken": confirm_token, "cexp": confirm_expires, "ip": client_ip, "tel": telefone})
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
async def confirmar_email(token: str, db: Session = Depends(get_db)):
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
    from services.email_service import enviar_email_confirmacao
    user = db.execute(text("SELECT id, nome, email_confirmado FROM users WHERE email = :email"), {"email": data.email}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="Email nao encontrado")
    if user[2]:
        return {"status": "ok", "mensagem": "Email ja confirmado"}
    confirm_token = secrets.token_urlsafe(32)
    confirm_expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    db.execute(text("UPDATE users SET confirm_token=:token, confirm_expires=:expires WHERE id=:id"),
               {"token": confirm_token, "expires": confirm_expires, "id": user[0]})
    db.commit()
    await enviar_email_confirmacao(data.email, user[1] or data.email, confirm_token)
    return {"status": "ok", "mensagem": "Email de confirmacao reenviado!"}

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
    if not any(c.isalpha() for c in data.password) or not any(c.isdigit() for c in data.password):
        raise HTTPException(status_code=400, detail="Senha deve conter letras e numeros")
    new_hash = hash_password(data.password)
    db.execute(text(
        "UPDATE users SET password_hash=:hash, senha_hash=:hash, reset_token=NULL, reset_expires=NULL WHERE id=:id"
    ), {"hash": new_hash, "id": user[0]})
    db.commit()
    return {"status": "ok", "mensagem": "Senha alterada com sucesso! Faca login com a nova senha."}

@router.get("/me")
async def get_me(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalido")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalido")
    row = db.execute(text("SELECT id, email, status FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    if not row or row[2] == "desativado":
        raise HTTPException(status_code=401, detail="Conta inativa")
    return {"email": row[1], "user_id": row[0]}

@router.get("/2fa/status")
async def twofa_status(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    row = db.execute(text("SELECT totp_enabled FROM users WHERE id=:id"), {"id": usuario["id"]}).fetchone()
    enabled = bool(row[0]) if row else False
    return {"enabled": enabled, "configured": enabled}

@router.post("/2fa/disable")
async def twofa_disable(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    db.execute(text("UPDATE users SET totp_enabled=false, totp_secret=NULL WHERE id=:id"), {"id": usuario["id"]})
    db.commit()
    return {"status": "ok", "mensagem": "2FA desativado"}
