"""
Health Check Endpoints - Verificação de saúde do sistema.
Inclui verificação de DATABASE_URL, JWT_SECRET_KEY, FERNET_KEY e conectividade.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from sqlalchemy import text
import os
import time
from urllib.request import Request, urlopen

router = APIRouter(prefix="/api", tags=["health"])


class HealthCheck(BaseModel):
    status: str # "healthy" | "degraded" | "unhealthy"
    checks: Dict[str, Any]


def _check_database() -> Dict[str, Any]:
    """Verifica conexão com banco de dados."""
    try:
        from backend.core.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Conectado"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _check_env_vars() -> Dict[str, Any]:
    """Verifica variáveis de ambiente obrigatórias."""
    required = ["DATABASE_URL", "JWT_SECRET_KEY"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        return {"status": "error", "message": f"Faltando: {', '.join(missing)}"}
    return {"status": "ok", "message": "Todas configuradas"}


def _check_fernet_key() -> Dict[str, Any]:
    """Verifica se FERNET_KEY está configurada."""
    key = os.getenv("FERNET_KEY", "").strip()
    if not key:
        env = os.getenv("FRALIB_ENV", "dev")
        if env == "prod":
            return {"status": "error", "message": "FERNET_KEY obrigatória em produção"}
        return {"status": "warning", "message": "Usando chave volátil (dev)"}
    return {"status": "ok", "message": "Configurada"}


def _check_llm_providers() -> Dict[str, Any]:
    """Verifica conectividade com providers LLM."""
    # Verifica se pelo menos um provider está configurado
    providers = {
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
 }
    configured = [k for k, v in providers.items() if v]
    if not configured:
        return {"status": "warning", "message": "Nenhum provider LLM configurado"}
    return {"status": "ok", "message": f"Providers: {', '.join(configured)}"}


def _http_probe(url: str, timeout_s: float = 1.5, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    try:
        start = time.monotonic()
        request = Request(url, headers=headers or {})
        with urlopen(request, timeout=timeout_s) as response:
            return {
                "status": "ok" if 200 <= response.status < 500 else "error",
                "code": response.status,
                "latency_ms": round((time.monotonic() - start) * 1000),
            }
    except Exception as exc:
        return {"status": "error", "message": str(exc)[:300]}


def _check_worker_queue() -> Dict[str, Any]:
    try:
        from backend.core.database import engine
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE status='pending') AS pending,
                    COUNT(*) FILTER (WHERE status='running') AS running,
                    COUNT(*) FILTER (
                        WHERE status='running'
                          AND worker_heartbeat < NOW() - INTERVAL '5 minutes'
                    ) AS stale_running,
                    COUNT(*) FILTER (
                        WHERE status='failed_permanent'
                          AND concluido_em > NOW() - INTERVAL '24 hours'
                    ) AS failed_24h
                FROM jobs
            """)).mappings().first()
        return {
            "status": "ok",
            "pending": int(row.get("pending") or 0),
            "running": int(row.get("running") or 0),
            "stale_running": int(row.get("stale_running") or 0),
            "failed_24h": int(row.get("failed_24h") or 0),
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)[:300]}


def _check_litellm() -> Dict[str, Any]:
    base_url = (os.getenv("ANTHROPIC_BASE_URL") or "").strip()
    if not base_url:
        return {"status": "skipped", "message": "API URL nao configurada"}
    headers = {}
    api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    url = base_url.rstrip("/")
    return _http_probe(f"{url}/models", timeout_s=5.0, headers=headers)


def _check_meowhats() -> Dict[str, Any]:
    base_url = (os.getenv("MEOWHATS_URL") or "http://127.0.0.1:3001").rstrip("/")
    headers = {}
    api_key = os.getenv("MEOWHATS_KEY", "").strip()
    if api_key:
        headers["X-API-Key"] = api_key
    return _http_probe(f"{base_url}/health", headers=headers)


def _overall_status(checks: Dict[str, Any]) -> str:
    statuses = [str(c.get("status", "")) for c in checks.values() if isinstance(c, dict)]
    if "error" in statuses:
        return "unhealthy"
    if any(s in {"warning", "degraded", "skipped"} for s in statuses):
        return "degraded"
    return "ok"


def health_payload(build_info: Dict[str, Any] | None = None) -> Dict[str, Any]:
    build = build_info or {}
    checks = {
        "db": _check_database(),
        "worker_queue": _check_worker_queue(),
        "meowhats": _check_meowhats(),
        "litellm": _check_litellm(),
    }
    return {
        "status": _overall_status(checks),
        "version": build.get("version", "2.0.0"),
        "commit": build.get("commit", "unknown"),
        "branch": build.get("branch", "unknown"),
        **checks,
    }


def _check_redis() -> Dict[str, Any]:
    """Verifica conexão Redis (se configurado)."""
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return {"status": "skipped", "message": "Redis não configurado"}
    try:
        import redis
        r = redis.from_url(redis_url)
        r.ping()
        return {"status": "ok", "message": "Conectado"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/health", response_model=HealthCheck)
def health_check():
    """
    Verificação completa de saúde do sistema.
    Retorna status geral e detalhes de cada componente.
    """
    checks = {
        "database": _check_database(),
        "env_vars": _check_env_vars(),
        "fernet_key": _check_fernet_key(),
        "llm_providers": _check_llm_providers(),
        "redis": _check_redis(),
    }

    # Determina status geral
    overall = _overall_status(checks)
    if overall == "ok":
        overall = "healthy"

    return HealthCheck(status=overall, checks=checks)


@router.get("/health/live")
def liveness():
    """Simple liveness probe - o container está rodando?"""
    return {"status": "alive"}


@router.get("/health/ready")
def readiness():
    """
    Readiness probe - o sistema está pronto para receber tráfego?
    Verifica apenas DB e variáveis de ambiente críticas.
    """
    db_check = _check_database()
    env_check = _check_env_vars()

    if db_check["status"] == "error":
        raise HTTPException(status_code=503, detail="Database não disponível")
    if env_check["status"] == "error":
        raise HTTPException(status_code=503, detail="Variáveis de ambiente faltando")

    return {"status": "ready"}
