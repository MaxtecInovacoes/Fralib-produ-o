"""Sprint 1.3: safe_log_silent_failure — padroniza logs de silent failures.

Problema: 4+ pontos no sdr_langgraph/agent.py fazem `print(f"[SDR] ... falhou")`
ou `except Exception: pass`. Erro silencioso = operator nao sabe que quebrou.

Fix: helper que:
  1. Loga com logger.warning (estruturado) com contexto (lead_id, stage, op)
  2. Throttla: max 1 log/min por (lead_id, op) pra nao encher log
  3. Inclui stack trace via logger.exception
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Optional

logger = logging.getLogger("fralib.observability")

# Throttle: { (lead_id, op) -> last_logged_at }
_LAST_LOG: dict[tuple, float] = defaultdict(float)
THROTTLE_SECONDS = 60.0


def safe_log_silent_failure(
    exc: BaseException,
    *,
    op: str,
    lead_id: Optional[str] = None,
    stage: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """Loga falha silenciosa com throttling.

    Args:
        exc: Excecao capturada
        op: Nome da operacao (ex: "humanization", "quality_judge", "memory_load")
        lead_id: ID do lead (opcional, pra throttling)
        stage: Stage do Kanban (opcional)
        extra: Campos extras pra log estruturado

    Example:
        try:
            humanize(text)
        except Exception as e:
            safe_log_silent_failure(e, op="humanization", lead_id=lead_id, stage=stage)
    """
    key = (lead_id, op)
    now = time.time()
    if now - _LAST_LOG[key] < THROTTLE_SECONDS:
        return  # throttled

    _LAST_LOG[key] = now

    msg = f"[silent_failure] op={op}"
    if lead_id:
        msg += f" lead_id={lead_id}"
    if stage:
        msg += f" stage={stage}"
    msg += f" error={type(exc).__name__}: {exc}"
    if extra:
        msg += f" extra={extra}"

    # logger.warning com stack trace
    logger.warning(msg, exc_info=True)
