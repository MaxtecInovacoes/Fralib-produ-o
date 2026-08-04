"""
logging_setup.py — Structured JSON logging para todo o processo.

Uso:
    from backend.core.logging_setup import setup_json_logging
    setup_json_logging()

Depois, usar logger padrao:
    import logging
    log = logging.getLogger("fralib")
    log.info("msg", extra={"key": "value"})
"""

import logging
import sys
import json
import traceback
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formata cada log record como JSON para ingestao por ELK/Datadog."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Campos extras (extra={...}) entram direto no JSON.
        reserved = {
            "name", "msg", "args", "created", "relativeCreated",
            "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "pathname", "filename", "module", "levelno", "levelname",
            "msecs", "thread", "threadName", "process", "processName",
            "taskName", "message",
        }
        extras = {k: v for k, v in record.__dict__.items()
                  if not k.startswith("_") and k not in reserved}
        if extras:
            payload["extra"] = extras

        if record.exc_info and record.exc_info[0]:
            payload["exception"] = "".join(
                traceback.format_exception(*record.exc_info)
            ).strip()

        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_json_logging(level: str = "INFO") -> None:
    """Substitui handler padrao por JSON. Chamar UMA vez na inicializacao."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.handlers = [handler]

    # Silenciar bibliotecas verbosas.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
