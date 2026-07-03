"""Retry helper — 3 tentativas com backoff exponencial, sem fallback silencioso."""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import random
import time
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 10.0


def _log_attempt(
    *,
    fn_name: str,
    attempt: int,
    max_retries: int,
    exc: BaseException,
    delay: float | None = None,
    status: str = "retry",
) -> None:
    payload = {
        "event": "retry_attempt",
        "agent": fn_name,
        "attempt": attempt,
        "max_attempts": max_retries,
        "status": status,
        "error_type": type(exc).__name__,
        "error_message": str(exc)[:500],
    }
    if delay is not None:
        payload["delay_seconds"] = round(delay, 3)
    msg = json.dumps(payload, ensure_ascii=False)
    if status == "failed":
        logger.error(msg)
    elif status == "success":
        logger.info(msg)
    else:
        logger.warning(msg)


def retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: retry ate max_retries com backoff exponencial + jitter.

    NAO usa fallback. Se todas as tentativas falharem, relanca a ultima
    excecao. Caller fica sabendo via traceback completo + logs.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: BaseException | None = None
            for attempt in range(1, max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1 and last_exc is not None:
                        _log_attempt(
                            fn_name=func.__name__,
                            attempt=attempt,
                            max_retries=max_retries,
                            exc=last_exc,
                            status="success",
                        )
                    return result
                except retry_on as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        _log_attempt(
                            fn_name=func.__name__,
                            attempt=attempt,
                            max_retries=max_retries,
                            exc=exc,
                            status="failed",
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    delay *= 0.5 + random.random()
                    _log_attempt(
                        fn_name=func.__name__,
                        attempt=attempt,
                        max_retries=max_retries,
                        exc=exc,
                        delay=delay,
                        status="retry",
                    )
                    time.sleep(delay)
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


def async_retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Async version."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: BaseException | None = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        _log_attempt(
                            fn_name=func.__name__,
                            attempt=attempt,
                            max_retries=max_retries,
                            exc=exc,
                            status="failed",
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    delay *= 0.5 + random.random()
                    _log_attempt(
                        fn_name=func.__name__,
                        attempt=attempt,
                        max_retries=max_retries,
                        exc=exc,
                        delay=delay,
                        status="retry",
                    )
                    await asyncio.sleep(delay)
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


def tentar(
    fn: Callable[..., T],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[..., T]:
    """Alias semantico: retry_with_backoff aplicado a fn."""
    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_on=retry_on,
    )(fn)