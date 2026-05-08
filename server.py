from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import sys
import os
import secrets
import hmac
import hashlib

# Adicionar TODAS as pastas do backend ao path
sys.path.insert(0, '/root/fralib/backend')
sys.path.insert(0, '/root/fralib/backend/core')
sys.path.insert(0, '/root/fralib/backend/endpoints')
sys.path.insert(0, '/root/fralib/backend/services')
sys.path.insert(0, '/root/fralib/backend/agents')
sys.path.insert(0, '/root/fralib/backend/utils')

# Inicializar database
from database import inicializar_database
inicializar_database()

# Rate Limiting
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# CSRF Secret Key
CSRF_SECRET_KEY = os.getenv("CSRF_SECRET_KEY")

def generate_csrf_token():
    """Gera um token CSRF seguro"""
    return secrets.token_urlsafe(32)

def verify_csrf_token(token: str, expected_token: str) -> bool:
    """Verifica se o token CSRF e valido"""
    return hmac.compare_digest(token, expected_token)

# Importar routers
import auth_endpoints
import dashboard_endpoints
import pipeline_endpoints
import pipeline_edit_endpoints
import sse_endpoints
import credits_endpoints
import users_endpoints
import leads_endpoints
import beta_endpoints
import whatsapp_endpoints


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    try:
        from sqlalchemy import text
        from database import engine
        with engine.connect() as conn:
            conn.execute(text("UPDATE public.pipeline_state SET rodando=false, pausado=false"))
            conn.commit()
        print("[Server] Pipeline state resetado no startup")
    except Exception as e:
        print(f"[Server] Aviso: nao foi possivel resetar pipeline_state: {e}")
    yield

app = FastAPI(title="FraLib API", version="2.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="/root/fralib/frontend/static"), name="static")
app.mount("/css", StaticFiles(directory="/root/fralib/frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="/root/fralib/frontend/js"), name="js")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://187.77.37.72:8000",
        "http://localhost:8000",
        "https://seunegociofralib.site",
        "https://www.seunegociofralib.site"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_endpoints.router)
app.include_router(dashboard_endpoints.router)
app.include_router(pipeline_endpoints.router)
app.include_router(pipeline_edit_endpoints.router)
app.include_router(sse_endpoints.router)
app.include_router(credits_endpoints.router)
app.include_router(users_endpoints.router)
app.include_router(leads_endpoints.router)
app.include_router(beta_endpoints.router)
app.include_router(whatsapp_endpoints.router)

# Rate limiting especifico para login (implementacao simples em memoria)
import time as _time_srv
from collections import defaultdict as _dd_srv
_login_calls = _dd_srv(list)

@app.middleware("http")
async def rate_limit_login(request: Request, call_next):
    if request.url.path == "/api/auth/login" and request.method == "POST":
        ip = request.client.host if request.client else "unknown"
        now = _time_srv.time()
        calls = [t for t in _login_calls[ip] if now - t < 60]
        if len(calls) >= 5:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=429, content={"detail": "Rate limit: maximo 5 tentativas de login por minuto"})
        calls.append(now)
        _login_calls[ip] = calls
    response = await call_next(request)
    return response

# CSRF Middleware - desabilitado (JWT ja protege todos os endpoints)
@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    response = await call_next(request)
    return response

@app.middleware("http")
async def csp_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # Apenas adicionar CSP em respostas HTML
    if "text/html" in response.headers.get("content-type", ""):
        # CSP Policy - Permitir recursos do mesmo dominio + CDNs confiaveis
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.stripe.com; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
    
    return response
# Endpoint para obter CSRF token
@app.get("/api/csrf-token")
async def get_csrf_token():
    """Retorna um CSRF token para o cliente"""
    token = generate_csrf_token()
    response = JSONResponse(content={"csrf_token": token})
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=3600  # 1 hora
    )
    return response

# Servir frontend

@app.get("/health")
@limiter.exempt
async def health():
    return {"status": "ok", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
