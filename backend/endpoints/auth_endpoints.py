from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import jwt, secrets, os
from utils.password_utils import verify_password, hash_password
from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text
from auth import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


def _inicializar_tenant(db: Session, user_id: int, nome: str, email: str, now: str, trial_expires: str):
    """
    Inicializa todos os recursos necessários para um novo tenant:
    - Diretório de sites no disco
    - Licença trial na tabela licencas
    - Config pipeline padrão
    """
    import os, secrets

    # 1. Criar diretório de sites do tenant
    sites_dir = f"/var/www/fralib/sites/{user_id}"
    try:
        os.makedirs(sites_dir, exist_ok=True)
        os.system(f"chown -R www-data:www-data {sites_dir}")
        os.system(f"chmod -R 755 {sites_dir}")
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

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(hours=24)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login", response_model=TokenResponse)
async def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(text("SELECT id, email, password_hash, email_confirmado FROM users WHERE email = :email"), {"email": data.email}).fetchone()
    if not user or not verify_password(data.password, user[2]):
        raise HTTPException(status_code=401, detail="Email ou senha invalidos")
    email_confirmado = user[3]
    if email_confirmado is False:
        raise HTTPException(status_code=403, detail="Confirme seu email antes de entrar. Verifique sua caixa de entrada.")
    token = create_access_token({"sub": str(user[0]), "email": user[1]})
    return TokenResponse(access_token=token)

@router.post("/register")
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    from services.email_service import enviar_email_confirmacao
    existing = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": data.email}).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Email ja cadastrado")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 6 caracteres")
    password_hash = hash_password(data.password)
    now = datetime.utcnow().isoformat()
    nome = data.nome or data.name or data.email.split("@")[0]
    trial_expires = (datetime.utcnow() + timedelta(days=7)).isoformat()
    confirm_token = secrets.token_urlsafe(32)
    confirm_expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    sql = """INSERT INTO users (email, nome, name, password_hash, senha_hash, plano, plan, role, status,
              creditos, creditos_max, trial_expires_at, criado_em, email_confirmado, confirm_token, confirm_expires)
              VALUES (:email, :nome, :nome, :hash, :hash, 'trial', 'free', 'user', 'trial',
              1, 1, :trial_exp, :now, true, NULL, NULL)"""
    db.execute(text(sql), {"email": data.email, "nome": nome, "hash": password_hash,
               "now": now, "trial_exp": trial_expires})
    db.commit()

    # Inicializar tenant: buscar user_id recém criado
    new_user = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": data.email}).fetchone()
    if new_user:
        user_id = new_user[0]
        _inicializar_tenant(db, user_id, nome, data.email, now, trial_expires)

    return {"status": "ok", "mensagem": "Cadastro realizado! Ja pode fazer login."}

@router.get("/confirmar-email")
async def confirmar_email(token: str, db: Session = Depends(get_db)):
    user = db.execute(text("SELECT id, confirm_expires FROM users WHERE confirm_token = :token"), {"token": token}).fetchone()
    if not user:
        raise HTTPException(status_code=400, detail="Token invalido ou ja utilizado")
    if datetime.utcnow().isoformat() > user[1]:
        raise HTTPException(status_code=400, detail="Token expirado. Solicite um novo email de confirmacao.")
    db.execute(text("UPDATE users SET email_confirmado=true, confirm_token=NULL, confirm_expires=NULL WHERE id=:id"), {"id": user[0]})
    db.commit()
    return {"status": "ok", "mensagem": "Email confirmado com sucesso! Voce ja pode fazer login."}

@router.post("/reenviar-confirmacao")
async def reenviar_confirmacao(data: LoginRequest, db: Session = Depends(get_db)):
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

@router.get("/me")
async def get_me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return {"email": payload.get("email"), "user_id": payload.get("sub")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalido")

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
