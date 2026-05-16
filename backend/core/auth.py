from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
from sqlalchemy import text as sa_text

security = HTTPBearer()

# ✅ CORREÇÃO CRÍTICA: SECRET_KEY agora vem do .env
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("❌ JWT_SECRET_KEY não configurado no .env")

ALGORITHM = "HS256"

# Engine compartilhado — importado uma vez, reutilizado em todas as requests
from database import engine as _shared_engine

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")

        # Buscar role do banco (engine compartilhado, sem criar novo)
        role = payload.get("role", "user")
        try:
            with _shared_engine.connect() as _c:
                _row = _c.execute(sa_text("SELECT role FROM users WHERE id=:id"), {"id": user_id}).fetchone()
                if _row and _row[0]:
                    role = _row[0]
        except Exception:
            pass

        return {"id": user_id, "email": email, "role": role}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")

    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Token inválido ou malformado")
