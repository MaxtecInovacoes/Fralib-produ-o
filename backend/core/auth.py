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
    print("[Auth Debug] Token recebido: [REDACTED]")
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        print(f"[Auth Debug] Token válido para usuário: {user_id}")
        return {"id": user_id, "email": email}
    
    except jwt.ExpiredSignatureError:
        print(f"[Auth Debug] Token expirado")
        raise HTTPException(status_code=401, detail="Token expirado")
    
    except jwt.InvalidTokenError as e:
        print(f"[Auth Debug] Token inválido (JWT): {e}")
        raise HTTPException(status_code=401, detail="Token inválido ou malformado")
