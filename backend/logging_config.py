"""
Logger estruturado com structlog para observabilidade.

Usa JSON para logs em produção e texto colorido em desenvolvimento.
Inclui:
- trace_id para correlação de requisições
- tenant_id para isolamento
- timestamps ISO8601
- estruturação automática de contexto
"""
import logging
import sys
import json
import uuid
from contextvars import ContextVar
from typing import Any, Optional

# Context vars para threading seguro
_tenant_id: ContextVar[Optional[int]] = ContextVar("tenant_id", default=None)
_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def set_tenant_id(tenant_id: Optional[int]) -> None:
    """Define tenant_id para o contexto atual."""
    _tenant_id.set(tenant_id)


def get_tenant_id() -> Optional[int]:
    """Obtém tenant_id do contexto atual."""
    return _tenant_id.get()


def set_trace_id(trace_id: Optional[str] = None) -> str:
    """Define trace_id para o contexto atual. Gera UUID se não fornecido."""
    tid = trace_id or str(uuid.uuid4())[:16]
    _trace_id.set(tid)
    return tid


def get_trace_id() -> Optional[str]:
    """Obtém trace_id do contexto atual."""
    return _trace_id.get()


def generate_request_id() -> str:
    """Gera e define request_id único."""
    rid = str(uuid.uuid4())[:16]
    _request_id.set(rid)
    return rid


class JSONFormatter(logging.Formatter):
    """Formatter que emite JSON estruturado em produção."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt or "%Y-%m-%dT%H:%M:%S.000Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Adicionar contexto
        trace_id = _trace_id.get()
        if trace_id:
            log_data["trace_id"] = trace_id

        tenant_id = _tenant_id.get()
        if tenant_id:
            log_data["tenant_id"] = tenant_id

        request_id = _request_id.get()
        if request_id:
            log_data["request_id"] = request_id

        # Adicionar extras
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Adicionar exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """Formatter colorido para desenvolvimento."""

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        trace = ""
        if _trace_id.get():
            trace = f" [{_trace_id.get()}]"

        tenant = ""
        if _tenant_id.get():
            tenant = f" [tenant:{_tenant_id.get()}]"

        return (
            f"{color}[{self.formatTime(record, self.datefmt or '%H:%M:%S')}]"
            f"{trace}{tenant} {record.levelname:8s}{reset} "
            f"{record.getMessage()}"
        )


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """
    Configura logging global.

    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Se True, usa JSON (produção). Se False, texto colorido (dev).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remover handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Criar handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ColoredFormatter())

    root_logger.addHandler(handler)

    # Configurar loggers específicos
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


# Logger便捷 para uso direto
def get_logger(name: str) -> logging.Logger:
    """Retorna logger configurado."""
    return logging.getLogger(name)


# Exemplo de uso:
# from backend.logging_config import get_logger, set_tenant_id, set_trace_id
#
# logger = get_logger(__name__)
# set_tenant_id(123)
# set_trace_id()
# logger.info("Usuário criou lead", extra={"lead_id": "abc123"})
