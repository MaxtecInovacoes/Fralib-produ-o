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
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_BUILD_INFO_CACHE = None


def _git_value(*args):
    try:
        return subprocess.check_output(
            ["git", "-C", BASE_DIR, *args],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).strip()
    except Exception:
        return ""


def _build_info():
    global _BUILD_INFO_CACHE
    if _BUILD_INFO_CACHE is not None:
        return dict(_BUILD_INFO_CACHE)
    commit = os.getenv("FRALIB_GIT_COMMIT") or _git_value("rev-parse", "--short", "HEAD") or "unknown"
    branch = os.getenv("FRALIB_GIT_BRANCH") or _git_value("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    if branch == "HEAD":
        branch = os.getenv("FRALIB_DEPLOY_BRANCH") or "detached"
    _BUILD_INFO_CACHE = {"version": "2.0.0", "commit": commit, "branch": branch}
    return dict(_BUILD_INFO_CACHE)

# Adicionar TODAS as pastas do backend ao path usando a raiz real do checkout.
for _rel in ("backend", "backend/core", "backend/endpoints", "backend/services", "backend/agents", "backend/utils"):
    sys.path.insert(0, os.path.join(BASE_DIR, _rel))

# Aplicar migrations Alembic — fonte de verdade do schema
from alembic.config import Config as _AlembicConfig
from alembic import command as _alembic_command
_ALEMBIC_INI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alembic.ini")
try:
    _alembic_command.upgrade(_AlembicConfig(_ALEMBIC_INI), "head")
    print("[Startup] Alembic migrations aplicadas")
except Exception as _e:
    print(f"[Startup] Alembic falhou ({_e}) — continuando com inicializar_database como fallback")

# Safety net DESABILITADO temporariamente: loop infinito em lock contention
# (coluna valor_venda ja existe no banco como real, mas codigo tenta NUMERIC(10,2))
# from database import inicializar_database
# try:
#     _db_ready = inicializar_database()
#     if _db_ready is False:
#         print("[Startup] inicializar_database skipped/timeout — seguindo sem bloquear")
# except Exception as _e:
#     print(f"[Startup] inicializar_database falhou ({_e}) — seguindo sem bloquear")
print("[Startup] inicializar_database DESABILITADO — schema ja existe, alembic eh fonte de verdade")

# Rate Limiting (instancia compartilhada — definida em core/rate_limiter.py)
from rate_limiter import limiter

# Importar routers
import auth_endpoints
import dashboard_endpoints
import pipeline_endpoints
import pipeline_control_endpoints
import pipeline_status_endpoints
import pipeline_reprocess_endpoints
import pipeline_analytics_endpoints
import pipeline_start_endpoints
import pipeline_edit_endpoints
import sse_endpoints
import credits_endpoints
import users_endpoints
import leads_endpoints
import beta_endpoints
import whatsapp_endpoints
import llm_endpoints
import api_usage_endpoints
import superadmin_endpoints
import provider_keys_endpoints
import provider_alerts_endpoints
import agent_config_endpoints
import falhas_endpoints
import site_editor_endpoints
import tracking_endpoints
import lead_supply_endpoints
import health_endpoints
import tenant_api_keys
import metrics_endpoints
import hermes_endpoints
import pipeline_tempo_endpoints


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    """Lifespan desabilitado temporariamente - causa lock no valor_venda.
    Para reabilitar, remover o ALTER TABLE que trava."""
    yield

    # PR15: tracking de visitas + colunas ROI na tabela leads
    try:
        from sqlalchemy import text
        from database import engine
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS site_visitas (
                    id SERIAL PRIMARY KEY,
                    lead_id VARCHAR(100) NOT NULL,
                    evento VARCHAR(20) NOT NULL,
                    ip_hash VARCHAR(32),
                    ua_hash VARCHAR(32),
                    criado_em TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_site_visitas_lead ON site_visitas(lead_id, criado_em)"))
            conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS valor_venda NUMERIC(10,2)"))
            conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS data_conversao TIMESTAMP"))
            conn.commit()
        print("[Server] Migration PR15 OK (site_visitas + colunas ROI)")
    except Exception as e:
        print(f"[Server] Aviso: migration PR15 falhou: {e}")

    # Migration Custom Tracker: Tabela para monitorar a própria landing page do Fralib OS
    try:
        from sqlalchemy import text
        from database import engine
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.landing_analytics (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(50) NOT NULL,
                    evento VARCHAR(50) NOT NULL,
                    valor_extra VARCHAR(255),
                    ip_hash VARCHAR(32),
                    ua_hash VARCHAR(32),
                    criado_em TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_landing_analytics_event ON public.landing_analytics(evento, criado_em)"))
            conn.commit()
        print("[Server] Migration landing_analytics OK")
    except Exception as e:
        print(f"[Server] Aviso: migration landing_analytics falhou: {e}")

    # Migration: coluna registro_ip para anti-abuse de trials
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS registro_ip VARCHAR(45)"))
            conn.commit()
        print("[Server] Migration: registro_ip OK")
    except Exception as e:
        print(f"[Server] Aviso: migration registro_ip falhou: {e}")

    # Migration: créditos diários (duplo cadeado)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS sites_hoje INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS sites_hoje_date DATE"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS ultimo_deploy_at TIMESTAMP WITH TIME ZONE"))
            conn.commit()
        print("[Server] Migration: creditos diarios OK")
    except Exception as e:
        print(f"[Server] Aviso: migration creditos diarios falhou: {e}")

    # Limpar checkpoints expirados (>24h) no startup
    try:
        from agents.pipeline_checkpoint import limpar_checkpoints_expirados
        limpar_checkpoints_expirados(max_age_hours=24)
        print("[Server] Checkpoints expirados limpos")
    except Exception as e:
        print(f"[Server] Aviso: limpeza checkpoints falhou: {e}")

    # Migration: tabela leads_cache (ISOLADO POR USER_ID para evitar envenenamento entre tenants)
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS leads_cache (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,  -- FIX: isola cache por tenant
                    nome VARCHAR(255) NOT NULL,
                    cidade VARCHAR(100) NOT NULL,
                    segmento VARCHAR(100),
                    telefone VARCHAR(30),
                    rating NUMERIC(3,1),
                    total_avaliacoes INTEGER DEFAULT 0,
                    website VARCHAR(500),
                    endereco VARCHAR(500),
                    maps_url VARCHAR(500),
                    fotos TEXT,
                    servicos TEXT,
                    horarios TEXT,
                    logo_url VARCHAR(500),
                    atributos TEXT,
                    faixa_preco VARCHAR(50),
                    reviews_json TEXT,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_em TIMESTAMP DEFAULT NOW()
                )
            """))
            # Adicionar user_id se não existir (para migração de dados existentes)
            try:
                conn.execute(text("ALTER TABLE leads_cache ADD COLUMN IF NOT EXISTS user_id INTEGER NOT NULL DEFAULT 0"))
            except:
                pass  # Coluna já existe
            # FIX: adicionar coluna estado (VARCHAR(2) = UF) para dedup cidade+UF
            # evita conflito tipo "Campina Grande, PB" vs "Campina Grande do Sul, PR"
            try:
                conn.execute(text("ALTER TABLE leads_cache ADD COLUMN IF NOT EXISTS estado VARCHAR(2)"))
            except:
                pass
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_cache_user_nome_cidade
                ON leads_cache (user_id, lower(nome), lower(cidade))
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_leads_cache_user_segmento_cidade
                ON leads_cache (user_id, lower(segmento), lower(cidade))
            """))
            conn.commit()
        print("[Server] Migration: leads_cache OK (com user_id)")
    except Exception as e:
        print(f"[Server] Aviso: migration leads_cache falhou: {e}")

    # Migration: coluna sdr_horario_config para config de horário do SDR por tenant
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS sdr_horario_config TEXT"))
            conn.commit()
        print("[Server] Migration: sdr_horario_config OK")
    except Exception as e:
        print(f"[Server] Aviso: migration sdr_horario_config falhou: {e}")

    # Iniciar listener WhatsApp (recebe respostas dos leads e chama Bryan)
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
        from whatsapp_listener import start_background_listener
        start_background_listener()
        print("[Server] WhatsApp listener iniciado")
    except Exception as e:
        print(f"[Server] Aviso: WhatsApp listener nao iniciado: {e}")

    yield

    # Shutdown: fechar conexões SSE e pg_notify
    print("[Server] Shutdown: fechando conexões...")
    try:
        from sse_endpoints import _shutdown_sse
        _shutdown_sse()
    except Exception as e:
        print(f"[Server] Aviso shutdown SSE: {e}")

app = FastAPI(title="FraLib API", version="2.0.0")  # lifespan=lifespan desabilitado temporariamente
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def _attach_user_id_for_rate_limit(request, call_next):
    """Decodifica JWT do header Authorization (best-effort) e popula request.state.user_id.

    Nao falha quando o token esta ausente ou invalido — apenas deixa user_id em None,
    fazendo o rate limiter cair no fallback por IP. NAO substitui get_current_user.
    """
    request.state.user_id = None
    try:
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            import jwt as _jwt
            _secret = os.getenv("JWT_SECRET_KEY", "")
            if _secret:
                try:
                    _payload = _jwt.decode(auth.split(" ", 1)[1], _secret, algorithms=["HS256"])
                    _sub = _payload.get("sub")
                    if _sub:
                        request.state.user_id = int(_sub)
                except Exception:
                    pass
    except Exception:
        pass
    return await call_next(request)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend", "static")), name="static")
app.mount("/css", StaticFiles(directory=os.path.join(BASE_DIR, "frontend", "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(BASE_DIR, "frontend", "js")), name="js")

# CORS — origins configurados via env var (IP da VPS não deve estar no código)
_cors_origins = os.getenv("FRALIB_CORS_ORIGINS", "http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept", "X-CSRF-Token", "X-XSRF-Token"],
)

# Security headers (CSP + clickjacking + MIME sniffing + referrer)
# CSP permissivo o suficiente para o dashboard atual (Chart.js, socket.io, inline styles
# gerados pelo renderer) mas bloqueia <script> injetado por XSS de campos do banco.
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    # Sites gerados ficam em /var/www/fralib/sites e sao servidos pelo nginx,
    # nao por este app — CSP aqui nao os afeta.
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self' https: wss: ws:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response

@app.get("/api/csrf-token")
async def csrf_token(request: Request):
    import secrets
    token = request.cookies.get("fralib_csrf") or secrets.token_urlsafe(32)
    secure_override = (os.getenv("FRALIB_COOKIE_SECURE") or "").strip().lower()
    if secure_override in {"1", "true", "yes", "on"}:
        secure = True
    elif secure_override in {"0", "false", "no", "off"}:
        secure = False
    else:
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        secure = proto == "https" or (os.getenv("FRALIB_ENV") or "").lower() == "prod"
    response = JSONResponse({"csrf_token": token})
    response.set_cookie(
        "fralib_csrf",
        token,
        max_age=60 * 60 * 24,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )
    return response

# Routers
app.include_router(auth_endpoints.router)
app.include_router(dashboard_endpoints.router)
app.include_router(pipeline_endpoints.router)
app.include_router(pipeline_control_endpoints.router)
app.include_router(pipeline_status_endpoints.router)
app.include_router(pipeline_reprocess_endpoints.router)
app.include_router(pipeline_analytics_endpoints.router)
app.include_router(pipeline_start_endpoints.router)
app.include_router(pipeline_edit_endpoints.router)
app.include_router(sse_endpoints.router)
app.include_router(credits_endpoints.router)
app.include_router(users_endpoints.router)
app.include_router(leads_endpoints.router)
app.include_router(beta_endpoints.router)
app.include_router(whatsapp_endpoints.router)
app.include_router(llm_endpoints.router)
app.include_router(api_usage_endpoints.router)
app.include_router(superadmin_endpoints.router)
app.include_router(provider_keys_endpoints.router)
app.include_router(provider_alerts_endpoints.router)
app.include_router(agent_config_endpoints.router)
app.include_router(falhas_endpoints.router)
app.include_router(pipeline_tempo_endpoints.router)
app.include_router(site_editor_endpoints.router)
app.include_router(tracking_endpoints.router)
import clarity_api_endpoints
app.include_router(clarity_api_endpoints.router)
app.include_router(lead_supply_endpoints.router)
import cron_endpoints
app.include_router(cron_endpoints.router)
import blog_endpoints
app.include_router(blog_endpoints.router)
import obs_endpoints
app.include_router(obs_endpoints.router)
import queue_endpoints
app.include_router(queue_endpoints.router)
app.include_router(health_endpoints.router)
# Plano Mestre SDR (b8214fe)
import closer_endpoints
app.include_router(closer_endpoints.router)
app.include_router(tenant_api_keys.router)
app.include_router(metrics_endpoints.router)
app.include_router(hermes_endpoints.router)
try:
    import admin_services_endpoints
    app.include_router(admin_services_endpoints.router)
    print("[Server] admin_services_endpoints registrado")
except ImportError as e:
    print(f"[Server] admin_services_endpoints nao disponivel: {e}")

try:
    import admin_tracing_endpoints
    app.include_router(admin_tracing_endpoints.router)
    print("[Server] admin_tracing_endpoints registrado")
except ImportError as e:
    print(f"[Server] admin_tracing_endpoints nao disponivel: {e}")

try:
    import admin_pipeline_control_endpoints
    app.include_router(admin_pipeline_control_endpoints.router)
    print("[Server] admin_pipeline_control_endpoints registrado")
except ImportError as e:
    print(f"[Server] admin_pipeline_control_endpoints nao disponivel: {e}")

try:
    import admin_outreach_endpoints
    app.include_router(admin_outreach_endpoints.router)
    print("[Server] admin_outreach_endpoints registrado (Sprint 14.3)")
except ImportError as e:
    print(f"[Server] admin_outreach_endpoints nao disponivel: {e}")

try:
    import cron_outreach_endpoints
    app.include_router(cron_outreach_endpoints.router)
    print("[Server] cron_outreach_endpoints registrado (Sprint 14.4)")
except ImportError as e:
    print(f"[Server] cron_outreach_endpoints nao disponivel: {e}")

try:
    import diagnostico_endpoints
    app.include_router(diagnostico_endpoints.router)
    print("[Server] diagnostico_endpoints registrado")
except ImportError as e:
    print(f"[Server] diagnostico_endpoints nao disponivel: {e}")

# Rate limit do login agora vem via @limiter.limit em auth_endpoints.py (slowapi).
# CSP+security headers vem via security_headers middleware acima (linha ~125).

# Servir frontend

@app.get("/api/version")
@limiter.exempt
async def api_version():
    return {"status": "ok", **_build_info()}


@app.get("/health")
@limiter.exempt
async def root_health():
    return health_endpoints.health_payload(_build_info())


@app.get("/llms.txt")
@limiter.exempt
async def llms_txt():
    path = os.path.join(BASE_DIR, "frontend", "llms.txt")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="llms.txt not found")
    return FileResponse(path, media_type="text/plain; charset=utf-8")


@app.get("/termos")
@app.get("/termos.html")
@app.get("/termos-de-uso")
@limiter.exempt
async def termos_de_uso():
    path = os.path.join(BASE_DIR, "frontend", "termos.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="termos.html not found")
    return FileResponse(path, media_type="text/html; charset=utf-8")


@app.get("/privacidade")
@app.get("/privacidade.html")
@app.get("/politica-de-privacidade")
@limiter.exempt
async def politica_privacidade():
    path = os.path.join(BASE_DIR, "frontend", "privacidade.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="privacidade.html not found")
    return FileResponse(path, media_type="text/html; charset=utf-8")

# Filtro para mascarar tokens sensíveis nos logs de acesso do uvicorn
import logging
import re as _re_log

class _TokenMaskFilter(logging.Filter):
    # Máscara: token=valor, Bearer token, access_token=, jwt=, session=, code=
    _patterns = [
        _re_log.compile(r'(token=)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(Bearer\s+)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(access_token=)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(jwt=)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(session=)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(code=)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(refresh_token=)[A-Za-z0-9\-_\.+=/]+'),
        # JWT tokens completos (eyJ...格式)
        _re_log.compile(r'(eyJ[A-Za-z0-9\-_\.+=/]{10,})'),
    ]

    def filter(self, record):
        if record.args:
            try:
                def mask(s):
                    for pat in self._patterns:
                        s = pat.sub(r'\1[REDACTED]', s)
                    return s
                record.args = tuple(
                    mask(a) if isinstance(a, str) else a
                    for a in record.args
                )
            except Exception:
                pass
        return True

_uvicorn_access = logging.getLogger("uvicorn.access")
_uvicorn_access.addFilter(_TokenMaskFilter())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
