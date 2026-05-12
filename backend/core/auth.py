from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os

security = HTTPBearer()

# ✅ CORREÇÃO CRÍTICA: SECRET_KEY agora vem do .env
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("❌ JWT_SECRET_KEY não configurado no .env")

ALGORITHM = "HS256"

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # DEBUG: Log do token recebido
    # print("[Auth Debug] Token recebido")
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")

        # Buscar role do banco para verificações de admin
        role = payload.get("role", "user")
        try:
            import os
            from sqlalchemy import create_engine, text as sa_text
            _engine = create_engine(os.getenv("DATABASE_URL", ""))
            with _engine.connect() as _c:
                _row = _c.execute(sa_text("SELECT role FROM users WHERE id=:id"), {"id": user_id}).fetchone()
                if _row and _row[0]:
                    role = _row[0]
        except Exception:
            pass

        # print(f"[Auth Debug] Token válido para usuário: {user_id}")
        return {"id": user_id, "email": email, "role": role}
    
    except jwt.ExpiredSignatureError:
        print(f"[Auth Debug] Token expirado")
        raise HTTPException(status_code=401, detail="Token expirado")
    
    except jwt.InvalidTokenError as e:
        print(f"[Auth Debug] Token inválido (JWT): {e}")
        raise HTTPException(status_code=401, detail="Token inválido ou malformado")
