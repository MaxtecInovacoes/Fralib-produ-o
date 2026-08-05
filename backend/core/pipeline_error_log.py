"""
pipeline_error_log.py — Log estruturado de erro por step da pipeline.

O manager/agent.py já importa log_step_error() desta module.
Tabela pipeline_error_log existe em database.py (CREATE TABLE IF NOT EXISTS).
"""

import traceback as tb_mod
from typing import Optional

from backend.core.database import SessionLocal
from sqlalchemy import text

_CATEGORIA_PADRAO = "UNKNOWN"


def log_step_error(
    lead_id: str,
    tenant_id: int,
    step_name: str,
    exc: Exception,
    categoria: Optional[str] = None,
) -> None:
    """Persiste erro de step no banco (best-effort — falha nunca quebra pipeline)."""
    try:
        exc_type = type(exc).__name__
        tb_text = "".join(tb_mod.format_exception(type(exc), exc, exc.__traceback__))
        msg = str(exc)[:2000]
        cat = _categorizar(exc_type, step_name)

        with SessionLocal() as db:
            db.execute(text("""
                INSERT INTO pipeline_error_log
                    (lead_id, tenant_id, step, exception_type, message,
                     traceback, fase_origem)
                VALUES (:lid, :tid, :sn, :et, :msg, :tb, :cat)
            """), {
                "lid": str(lead_id),
                "tid": int(tenant_id),
                "sn": step_name,
                "et": exc_type,
                "msg": msg,
                "tb": tb_text[:8000],
                "cat": cat,
            })
            db.commit()
    except Exception as log_err:
        # Logging best-effort: nao propagamos, mas nunca silenciamos
        print(f"[pipeline_error_log][WARN] Falha ao registrar erro: {log_err}")


def _categorizar(exc_type: str, step_name: str) -> str:
    """Classifica erro em categoria para triagem no dashboard."""
    tipo = exc_type.lower()
    if any(k in tipo for k in ("timeout", "readtimeout", "connection")):
        return "TIMEOUT"
    if any(k in tipo for k in ("ratelimit", "apierror", "overloaded")):
        return "LLM_ERROR"
    if any(k in tipo for k in ("operational", "disconnected", "interface")):
        return "DB_ERROR"
    if any(k in tipo for k in ("validation", "decode", "json")):
        return "HTML_ERROR"
    if step_name in ("Builder", "Liz"):
        return "HTML_ERROR"
    if step_name in ("Arquiteto", "Theo", "Designer"):
        return "LLM_ERROR"
    return "UNKNOWN"
