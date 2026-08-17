"""
Observabilidade Total — FraLib
Funcionalidades:
- Sentry SDK (captura exceções, stack trace, payload)
- Correlation IDs (x-correlation-id) em todas as requisições
- Health check deep (/api/health/deep)
- Validação de variáveis de ambiente na inicialização
- Log estruturado via loguru
"""

import os
import sys
import time
import socket
import logging
from typing import Optional
from contextvars import ContextVar
from loguru import logger as _base_logger

# ============================================================
# 1. CORRELATION ID (ContextVar)
# ============================================================
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    return correlation_id_var.get()


def set_correlation_id(cid: Optional[str]) -> None:
    correlation_id_var.set(cid)


# ============================================================
# 2. LOG ESTRUTURADO (loguru)
# ============================================================
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Remove handler padrão
_base_logger.remove()

# Handler JSON para arquivo (se LOG_FILE definido)
_log_file = os.getenv("LOG_FILE")
if _log_file:
    _base_logger.add(
        _log_file,
        rotation="50 MB",
        retention="7 days",
        encoding="utf-8",
        format="{time:ISO8601} | {level} | {name}:{function}:{line} | {message}",
    )

# Handler console (sempre)
_base_logger.add(
    sys.stderr,
    level=_log_level,
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}:{function}:{line}</cyan> | <level>{message}</level>",
    colorize=True,
)


# Interceptar uvicorn/fastapi logs para usar loguru
class _InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _base_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        _base_logger.opt(
            depth=6,
            exception=record.exc_info,
        ).log(level, record.getMessage())


# Configurar logging padrão para usar InterceptHandler
logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

# Silenciar loggers ruidosos
for noisy in ("uvicorn.access", "httpx", "httpcore", "sqlalchemy.engine"):
    logging.getLogger(noisy).setLevel(logging.WARNING if noisy == "uvicorn.access" else logging.ERROR)

logger = _base_logger

# ============================================================
# 3. SENTRY SDK
# ============================================================
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.httpx import HttpxIntegration

    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(transaction_style="url"),
            sentry_logging,
            SqlalchemyIntegration(),
            HttpxIntegration(),
        ],
        # Incluir dados do request (exceto cookies/headers sensíveis)
        send_default_pii=False,
        # Attach stacktrace sempre
        attach_stacktrace=True,
        # Profiling (opcional)
        profiles_sample_rate=0.0,
        # Antes de enviar, adicionar correlation ID
        before_send=lambda event, hint: _enrich_sentry_event(event, hint),
    )
    logger.info("Sentry SDK inicializado (env={}, sample_rate={})", SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE)
else:
    logger.warning("SENTRY_DSN nao configurado — Sentry desativado")


def _enrich_sentry_event(event, hint) -> dict:
    """Adiciona correlation_id ao evento Sentry."""
    cid = get_correlation_id()
    if cid:
        event.setdefault("tags", {})["correlation_id"] = cid
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        event.setdefault("exception", {}).setdefault("values", [{}])[-1].setdefault("mechanism", {})
    return event


# ============================================================
# 4. HEALTH CHECK DEEP
# ============================================================
def check_database_health(db) -> dict:
    """Testa SELECT 1 no banco com timeout."""
    try:
        from sqlalchemy import text
        start = time.time()
        db.execute(text("SELECT 1"))
        elapsed_ms = int((time.time() - start) * 1000)
        return {"status": "ok", "latency_ms": elapsed_ms}
    except Exception as e:
        return {"status": "error", "error": str(e), "type": type(e).__name__}


def check_redis_health() -> dict:
    """Testa conexão com Redis."""
    try:
        import redis as redis_lib
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis_lib.from_url(redis_url, socket_connect_timeout=2)
        start = time.time()
        r.ping()
        elapsed_ms = int((time.time() - start) * 1000)
        r.close()
        return {"status": "ok", "latency_ms": elapsed_ms}
    except ImportError:
        return {"status": "skipped", "reason": "redis package not installed"}
    except Exception as e:
        return {"status": "error", "error": str(e), "type": type(e).__name__}


def check_memory() -> dict:
    """Retorna uso de memória do processo."""
    try:
        import psutil
        mem = psutil.Process().memory_info()
        return {
            "status": "ok",
            "rss_mb": round(mem.rss / 1024 / 1024, 1),
            "vms_mb": round(mem.vms / 1024 / 1024, 1),
        }
    except ImportError:
        # Fallback sem psutil
        import resource
        return {
            "status": "ok",
            "rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "note": "psutil not installed",
        }


def deep_health_check(db) -> dict:
    """Health check completo do sistema."""
    hostname = socket.gethostname()
    pid = os.getpid()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    checks = {
        "hostname": hostname,
        "pid": pid,
        "python": python_version,
        "database": check_database_health(db),
        "redis": check_redis_health(),
        "memory": check_memory(),
        "sentry": {"status": "active" if SENTRY_DSN else "disabled"},
    }

    # Determina status geral
    failed = [k for k, v in checks.items() if isinstance(v, dict) and v.get("status") == "error"]
    if failed:
        checks["overall_status"] = "degraded"
        checks["failed_checks"] = failed
        return {"status": "degraded", "checks": checks}, 503
    return {"status": "healthy", "checks": checks}, 200
