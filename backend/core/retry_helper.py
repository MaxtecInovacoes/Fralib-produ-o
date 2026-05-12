"""
Retry helper para fases do pipeline.

Filosofia: distinguir falha transiente (rate limit, timeout, 5xx) de falha
permanente (input invalido, sem creditos, ValueError). So a transiente vale
retry; o resto sobe direto e o operador trata.

Uso decorador (em funcoes novas):

    @com_retry(fase="liam", max_attempts=3, base_delay=2)
    def gerar_html_componentizado(prd):
        ...

Uso imperativo (em chamadas existentes, menos invasivo):

    state.html_final = tentar(
        lambda: gerar_html_componentizado(state.prd_arquiteto),
        fase="liam", max_attempts=3, base_delay=2,
    )

Backoff: base_delay * 2^(attempt-1) com jitter de +/-20%. Ex base_delay=2:
attempt 1=2s, 2=4s, 3=8s.
"""
import asyncio
import logging
import random
import time
from functools import wraps
from typing import Awaitable, Callable, Optional, TypeVar

log = logging.getLogger("fralib.retry")

T = TypeVar("T")


# Classes de erro que NAO devem retry: bug em codigo proprio, input invalido,
# autenticacao errada. Repetir nao ajuda.
_NAO_RETRIAVEL = (
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    NotImplementedError,
    AssertionError,
)


# Padroes em mensagens de erro que indicam falha permanente do provider.
_PADROES_PERMANENTES = (
    "insufficient_quota",
    "invalid_api_key",
    "authentication",
    "billing",
    "permission_denied",
    "context_length_exceeded",
    "credit",
    "saldo insuficiente",
)


def _eh_retriavel(exc: BaseException) -> bool:
    if isinstance(exc, _NAO_RETRIAVEL):
        return False
    msg = str(exc).lower()
    return not any(p in msg for p in _PADROES_PERMANENTES)


def _calcular_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    raw = base_delay * (2 ** (attempt - 1))
    jitter = raw * random.uniform(-0.2, 0.2)
    return min(raw + jitter, max_delay)


def tentar(
    fn: Callable[[], T],
    fase: str,
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    log_fn: Optional[Callable[[str, str], None]] = None,
) -> T:
    """
    Executa fn() ate max_attempts vezes com backoff exponencial. Se a ultima
    tentativa falhar, propaga a excecao. So tenta de novo em erros transientes.

    log_fn: callable opcional (mensagem, tipo) — costuma ser o adicionar_log
    do pipeline pra mensagens chegarem no SSE do cliente.
    """
    ultimo_erro: Optional[BaseException] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except BaseException as e:
            ultimo_erro = e
            if not _eh_retriavel(e):
                log.warning(f"[retry/{fase}] erro NAO-retriavel: {e}")
                raise
            if attempt >= max_attempts:
                log.warning(f"[retry/{fase}] esgotou {max_attempts} tentativas: {e}")
                raise
            delay = _calcular_delay(attempt, base_delay, max_delay)
            msg = f"[retry/{fase}] tentativa {attempt}/{max_attempts} falhou ({str(e)[:80]}), tentando de novo em {delay:.1f}s"
            log.warning(msg)
            if log_fn:
                try:
                    log_fn(f"  Tentando novamente em {delay:.0f}s (tentativa {attempt}/{max_attempts})", "warning")
                except Exception:
                    pass
            time.sleep(delay)
    if ultimo_erro:
        raise ultimo_erro
    raise RuntimeError(f"tentar({fase}) terminou sem resultado nem excecao")


async def tentar_async(
    fn: Callable[[], Awaitable[T]],
    fase: str,
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    log_fn: Optional[Callable[[str, str], None]] = None,
) -> T:
    """Versao async de tentar(). Use com corrotinas."""
    ultimo_erro: Optional[BaseException] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except BaseException as e:
            ultimo_erro = e
            if not _eh_retriavel(e):
                log.warning(f"[retry/{fase}] erro NAO-retriavel: {e}")
                raise
            if attempt >= max_attempts:
                log.warning(f"[retry/{fase}] esgotou {max_attempts} tentativas: {e}")
                raise
            delay = _calcular_delay(attempt, base_delay, max_delay)
            log.warning(f"[retry/{fase}] tentativa {attempt}/{max_attempts} falhou ({str(e)[:80]}), tentando de novo em {delay:.1f}s")
            if log_fn:
                try:
                    log_fn(f"  Tentando novamente em {delay:.0f}s (tentativa {attempt}/{max_attempts})", "warning")
                except Exception:
                    pass
            await asyncio.sleep(delay)
    if ultimo_erro:
        raise ultimo_erro
    raise RuntimeError(f"tentar_async({fase}) terminou sem resultado nem excecao")


def com_retry(fase: str, max_attempts: int = 3, base_delay: float = 2.0, max_delay: float = 30.0):
    """
    Decorator. Suporta funcoes sync e async automaticamente.

        @com_retry(fase="liam", max_attempts=3)
        def gerar_html_componentizado(prd):
            ...
    """
    def deco(fn):
        if asyncio.iscoroutinefunction(fn):
            @wraps(fn)
            async def wrapper_async(*args, **kwargs):
                return await tentar_async(
                    lambda: fn(*args, **kwargs),
                    fase=fase, max_attempts=max_attempts,
                    base_delay=base_delay, max_delay=max_delay,
                )
            return wrapper_async

        @wraps(fn)
        def wrapper(*args, **kwargs):
            return tentar(
                lambda: fn(*args, **kwargs),
                fase=fase, max_attempts=max_attempts,
                base_delay=base_delay, max_delay=max_delay,
            )
        return wrapper
    return deco
