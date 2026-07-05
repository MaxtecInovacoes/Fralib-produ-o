"""Log swallowed exceptions with consistent format.

Canônico para M15 do plano DRY (codex/dry-refactor).

Fornece log_swallowed() — substitui 258+ call sites que faziam
``logger.warning(f"[Tag] op falhou: {e}")`` em try/except handlers.

STATUS (M15): helper criado mas NÃO migrado em massa.
Call sites individuais têm decisões de design (qual tag, qual contexto,
qual nível, qual sufixo) que tornam mass-migration arriscada e propensa
a erro humano. Cada call site vale uma sessão dedicada de review.

Vantagens da canônica:
  - Formato único: `[Tag] op (contexto): exc_class: msg`
  - tag consistente (sempre com colchetes, sem duplicação)
  - nível de log parametrizado (warning/error/info)
  - contexto opcional (ex: 'user=42', 'no-bloqueante')
  - sufixo opcional (ex: '. Mensagem NAO enviada.')
  - logger obtido por parâmetro (sem globals)
"""
from __future__ import annotations

import logging
from typing import Optional


def log_swallowed(
    logger: logging.Logger,
    tag: str,
    op: str,
    exc: BaseException,
    *,
    level: str = "warning",
    context: Optional[str] = None,
    suffix: str = "",
) -> None:
    """Log a swallowed exception with consistent format.

    Args:
        logger: Logger instance (callers pass `logger = logging.getLogger(__name__)`).
        tag: Short tag for the caller (e.g. 'AgentMemory', 'WPP-Listener', 'SDR').
            Wrapped in brackets automatically.
        op: Human description of the operation that failed
            (e.g. 'Backup falhou', 'transparency check').
        exc: The swallowed exception.
        level: Log level — 'warning' (default), 'error', 'info', 'debug'.
        context: Optional context string (e.g. 'user=42', 'no-bloqueante').
        suffix: Optional trailing text (e.g. '. Mensagem NAO enviada.').

    Output format:
        ``[{tag}] {op}{context}: {exc_class}: {exc}{suffix}``
    Example:
        ``[WPP-Listener] transparency falhou (no-bloqueante): KeyError: 'foo'``
    """
    ctx = f" ({context})" if context else ""
    msg = f"[{tag}] {op}{ctx}: {type(exc).__name__}: {exc}{suffix}"
    log_fn = getattr(logger, level, logger.warning)
    log_fn(msg)


__all__ = ["log_swallowed"]