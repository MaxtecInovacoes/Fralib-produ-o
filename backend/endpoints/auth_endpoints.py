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
