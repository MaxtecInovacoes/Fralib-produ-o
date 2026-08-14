# ============================================================
# VALIDAÇÃO DE ENV + OBSERVABILIDADE (Sentry + Correlation ID)
# ============================================================
from backend.core.env_validator import check_and_fail
from backend.core.observability_setup import (
    logger as obs_logger,
    correlation_id_var,
    set_correlation_id,
    get_correlation_id,
    deep_health_check,
)
check_and_fail()

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import sys
import os

# Detectar ambiente: Docker (/app) vs systemd VPS (/root/fralib) vs legacy (/opt/fralib)
# Também suporta desenvolvimento local (Windows/Mac) com CWD-based detection
_BACKEND_ROOT = None
_FRONTEND_ROOT = None
for candidate in ['/app', '/opt/fralib', '/root/fralib', os.getcwd(), os.path.dirname(os.path.abspath(__file__))]:
    backend_dir = os.path.join(candidate, 'backend')
    if os.path.exists(backend_dir) and os.path.exists(os.path.join(backend_dir, 'core', 'database.py')):
        _BACKEND_ROOT = backend_dir
        _FRONTEND_ROOT = candidate
        break

if not _BACKEND_ROOT:
    raise RuntimeError(
        "Nenhum backend encontrado com core/database.py. "
        "Verifique /app/backend, /root/fralib/backend ou /opt/fralib/backend"
    )

# sys.path: insere APENAS a raiz do projeto e o backend.
# Qualquer import deve usar caminho absoluto (ex: from backend.core.database import X).
# Os inserts de subdiretórios (/core, /endpoints, /agents etc.) foram removidos
# para forçar imports absolutos — evita hacks de VPS como /root/fralib/backend.
sys.path.insert(0, _FRONTEND_ROOT)          # ex: /root/fralib ou /app
sys.path.insert(0, _BACKEND_ROOT)           # ex: /root/fralib/backend

# Aplicar migrations Alembic — fonte de verdade do schema
from alembic.config import Config as _AlembicConfig
from alembic import command as _alembic_command
# alembic.ini está em _FRONTEND_ROOT (raiz do projeto)
_ALEMBIC_INI = os.path.join(_FRONTEND_ROOT, "alembic.ini")
try:
    _alembic_command.upgrade(_AlembicConfig(_ALEMBIC_INI), "head")
    print("[Startup] Alembic migrations aplicadas")
except Exception as _e:
    print(f"[Startup] Alembic falhou ({_e}) — continuando com inicializar_database como fallback")

# Safety net: cria qualquer tabela que ainda nao esteja na Alembic
from backend.core.database import inicializar_database
inicializar_database()

# Rate Limiting (instancia compartilhada — definida em core/rate_limiter.py)
from backend.core.rate_limiter import limiter

from contextlib import asynccontextmanager

# Router registration
from core.router_setup import register_routers

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

    # 3.2 — Marcar jobs em_andamento como interrompido (PM2 reiniciou durante execucao)
    try:
        from sqlalchemy import text
        from database import engine
        with engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE pipeline_queue
                SET status='interrompido', concluido_em=NOW(),
                    erro='Processo reiniciado (PM2/servidor) durante execucao'
                WHERE status='em_andamento'
                RETURNING id
            """))
            interrompidos = result.fetchall()
            conn.commit()
        if interrompidos:
            ids = [str(r[0]) for r in interrompidos]
            print(f"[Server] {len(ids)} job(s) marcados como interrompido: {', '.join(ids)}")
        else:
            print("[Server] Nenhum job interrompido encontrado")
    except Exception as e:
        print(f"[Server] Aviso: nao foi possivel verificar pipeline_queue: {e}")

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

    # Migration: tabela leads_cache (cache global de leads entre tenants)
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS leads_cache (
                    id SERIAL PRIMARY KEY,
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
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_cache_nome_cidade
                ON leads_cache (lower(nome), lower(cidade))
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_leads_cache_segmento_cidade
                ON leads_cache (lower(segmento), lower(cidade))
            """))
            conn.commit()
        print("[Server] Migration: leads_cache OK")
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

    # Iniciar listener WhatsApp (recebe respostas dos leads e chama Franz)
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

app = FastAPI(title="FraLib API", version="2.0.0", lifespan=lifespan)
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

app.mount("/static", StaticFiles(directory=os.path.join(_FRONTEND_ROOT, "frontend/static")), name="static")
app.mount("/css", StaticFiles(directory=os.path.join(_FRONTEND_ROOT, "frontend/css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(_FRONTEND_ROOT, "frontend/js")), name="js")

# CORS — metodos e headers explicitos em vez de wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://104.243.41.166:8001",
        "http://187.77.37.72:8000",
        "http://localhost:8000",
        "https://seunegociofralib.site",
        "https://www.seunegociofralib.site",
        "https://app.seunegociofralib.site"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept"],
)

# Correlation ID middleware — rastreamento ponta a ponta
@app.middleware("http")
async def correlation_id_middleware(request, call_next):
    import uuid
    # Usar header existente ou gerar novo
    cid = request.headers.get("x-correlation-id") or str(uuid.uuid4())[:12]
    set_correlation_id(cid)
    response = await call_next(request)
    response.headers["x-correlation-id"] = cid
    return response

# Security headers (CSP + clickjacking + MIME sniffing + referrer)
# CSP permissivo o suficiente para o dashboard atual (Chart.js, socket.io, inline styles
# gerados pelo Liam) mas bloqueia <script> injetado por XSS de campos do banco.
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    # Sites gerados pelo Liam ficam em /var/www/fralib/sites e sao servidos pelo nginx,
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

# CSRF stub — autenticacao real e via JWT no header Authorization.
# Este endpoint existe so para o frontend (csrf-helper.js) nao receber 404.
# TODO: remover quando o csrf-helper.js for desligado no frontend.
@app.get("/api/csrf-token")
async def csrf_token():
    import secrets
    return {"csrf_token": secrets.token_hex(32)}

# Routers
register_routers(app)


# Rate limit do login agora vem via @limiter.limit em auth_endpoints.py (slowapi).
# CSP+security headers vem via security_headers middleware acima (linha ~125).

# Servir frontend

@app.get("/health")
@limiter.exempt
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/api/health/deep")
@limiter.exempt
async def health_deep(request: Request, db = None):
    """Health check profundo: database, redis, memória."""
    from backend.core.observability_setup import deep_health_check
    try:
        from database import get_db
        db_gen = get_db()
        db = next(db_gen)
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": f"Falha ao conectar ao banco: {e}"},
        )
    try:
        result, status_code = deep_health_check(db)
        return JSONResponse(status_code=status_code, content=result)
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": str(e)},
        )


# Filtro para mascarar JWT token nos logs de acesso do uvicorn
import logging
import re as _re_log

class _TokenMaskFilter(logging.Filter):
    _pat = _re_log.compile(r'(token=)[A-Za-z0-9\-_\.]+')
    def filter(self, record):
        if record.args:
            try:
                record.args = tuple(
                    self._pat.sub(r'\1[REDACTED]', a) if isinstance(a, str) else a
                    for a in record.args
                )
            except Exception:
                pass
        return True

_uvicorn_access = logging.getLogger("uvicorn.access")
_uvicorn_access.addFilter(_TokenMaskFilter())

# Redirecionar legacy /dashboard e /dashboard.html para /admin.html
@app.get("/dashboard")
@app.get("/dashboard.html")
async def redirect_legacy_dashboard():
    return RedirectResponse(url="/admin.html", status_code=301)

# Servir arquivos estáticos do frontend na raiz
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# Middleware: no-cache headers para HTML (evita browser cache em deploy)
@app.middleware("http")
async def no_cache_html(request: Request, call_next):
    response = await call_next(request)
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
