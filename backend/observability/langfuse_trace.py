"""
Langfuse Tracing — FraLib
========================
Ponto único de instrumentação para todo o sistema.

Uso:
    from backend.observability.langfuse_trace import trace_span, trace_span_sync, flush

    # Síncrono (maioria dos agentes)
    resultado = trace_span_sync(
        nome="caio.qualificacao",
        input_data={"lead": lead.nome, "segmento": lead.segmento},
        metadata={"tenant_id": tenant_id, "lead_id": str(lead.id)},
    )(funcao_qualificar)(lead)

    # Decorator para funções síncronas
    @trace_llm_call("caio.qualificacao")
    def qualificar(lead): ...

    # Context manager (async ou sync)
    with trace_span("site.geracao") as span:
        span.input({"template": t})
        html = gerar_site(t)
        span.output({"size": len(html)})

Fallback graceful: se Langfuse não disponível, todas as funções são no-op.
"""

from __future__ import annotations

import os
import time
import hashlib
import logging
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Iterator, Optional

logger = logging.getLogger("fralib.langfuse")

# ============================================================
# 1. SINGLETON — lazy init, thread-safe
# ============================================================

_tracer = None
_enabled = None


def _check_enabled() -> bool:
    """Verifica uma vez se Langfuse está configurado."""
    global _enabled
    if _enabled is not None:
        return _enabled
    pub = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sec = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
    _enabled = bool(pub and sec)
    if _enabled:
        logger.info("[Langfuse] Habilitado — host={}".format(host))
    else:
        logger.debug("[Langfuse] Desabilitado (credenciais não configuradas)")
    return _enabled


def get_tracer():
    """Retorna instância singleton do Langfuse. None se desabilitado."""
    global _tracer
    if not _check_enabled():
        return None
    if _tracer is None:
        try:
            from langfuse import Langfuse
            host = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
            _tracer = Langfuse(
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
                secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
                host=host,
                flush_at=5,
                flush_interval=1.0,
            )
            logger.info("[Langfuse] Cliente inicializado")
        except Exception as e:
            logger.warning("[Langfuse] Falha ao inicializar: {}".format(e))
            _enabled = False
            return None
    return _tracer


def flush() -> None:
    """Força flush dos traces pendentes. Chamar no shutdown do worker."""
    t = get_tracer()
    if t:
        try:
            t.flush()
        except Exception:
            pass


# ============================================================
# 2. HELPERS
# ============================================================

def _truncate(value: Any, limit: int = 4000) -> Any:
    """Trunca strings longas para não estourar storage do Langfuse."""
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "...[truncado]"
    if isinstance(value, dict):
        return {k: _truncate(v, limit) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_truncate(v, limit) for v in value)
    return value


def _prompt_hash(prompt: str) -> str:
    """Hash curto do prompt para versionamento."""
    if not prompt:
        return ""
    return hashlib.md5(prompt.encode()).hexdigest()[:12]


def _safe_metadata(meta: dict | None) -> dict:
    """Remove None, sanitiza tamanho, garante tipos serializáveis."""
    if not meta:
        return {}
    result = {}
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            result[k] = v
        else:
            result[k] = str(v)
    return _truncate(result, 2000)


# ============================================================
# 3. SPAN SYNC — para chamadas síncronas (caso mais comum)
# ============================================================

@contextmanager
def trace_span(
    nome: str,
    input_data: Any = None,
    metadata: dict | None = None,
) -> Iterator[Any]:
    """Context manager para criar um span de trace.

    Uso:
        with trace_span("caio.qualificacao", input_data=dados, metadata={...}) as span:
            resultado = caio_qualificar(dados)
            span.output(resultado)
    """
    t = get_tracer()
    if t is None:
        yield _NoOpSpan()
        return

    start = time.time()
    span = t.start_as_current_span(name=nome)
    erro = None
    try:
        with span:
            wrapper = _SpanWrapper(span, input_data, metadata)
            yield wrapper
    except Exception as e:
        erro = e
        span.set_level("ERROR")
        span.set_status("ERROR", str(e)[:500])
        raise
    finally:
        latency_ms = round((time.time() - start) * 1000)
        try:
            span.set_attribute("latency_ms", latency_ms)
        except Exception:
            pass
        if erro:
            try:
                logger.debug("[Langfuse] Span erro: {} — {}ms".format(nome, latency_ms))
            except Exception:
                pass


class _SpanWrapper:
    """Helper para alimentar input/output do span dentro do context manager."""

    def __init__(self, span, input_data, metadata):
        self._span = span
        if input_data is not None:
            try:
                self._span.set_attribute("input", _truncate(input_data))
            except Exception:
                pass
        if metadata:
            try:
                for k, v in _safe_metadata(metadata).items():
                    self._span.set_attribute(k, v)
            except Exception:
                pass

    def output(self, data: Any) -> None:
        try:
            self._span.set_attribute("output", _truncate(data))
        except Exception:
            pass

    def input(self, data: Any) -> None:
        try:
            self._span.set_attribute("input", _truncate(data))
        except Exception:
            pass


class _NoOpSpan:
    """Fallback quando Langfuse está desabilitado."""

    def output(self, data): pass
    def input(self, data): pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ============================================================
# 4. SPAN SYNC WRAPPER — para envolver chamadas existentes
# ============================================================

def trace_span_sync(
    nome: str,
    input_data: Any = None,
    metadata: dict | None = None,
) -> Callable:
    """Retorna um decorator que envolve uma chamada síncrona com trace.

    Uso:
        resultado = trace_span_sync(
            nome="caio.qualificacao",
            input_data={"lead_id": "123"},
            metadata={"tenant_id": 2},
        )(caio_qualificar)(lead)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Monta input do span a partir dos args se não fornecido
            span_input = input_data
            if span_input is None and args:
                span_input = {"args": [str(a) for a in args[:3]]}

            with trace_span(nome, input_data=span_input, metadata=metadata) as span:
                resultado = func(*args, **kwargs)
                span.output(resultado)
                return resultado
        return wrapper
    return decorator


# ============================================================
# 5. DECORATOR — para funções LLM
# ============================================================

def trace_llm_call(nome: str):
    """Decorator para funções de LLM. Captura input, output, tokens, erro.

    Uso:
        @trace_llm_call("caio.qualificacao")
        def qualificar_lead(lead, prompt):
            return client.call(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            t = get_tracer()
            if t is None:
                return func(*args, **kwargs)

            start = time.time()
            # Tenta extrair metadata dos kwargs
            meta = _safe_metadata(kwargs.get("metadata"))
            # Adiciona info do modelo se disponível nos args
            if len(args) > 0 and isinstance(args[0], str):
                meta.setdefault("model_id", args[0])
            if len(args) > 1 and isinstance(args[1], str):
                prompt_hash = _prompt_hash(args[1])
                meta.setdefault("prompt_version", prompt_hash)

            span_input = {
                "model_id": args[0] if args else kwargs.get("model_id", ""),
                "prompt_len": len(args[1]) if len(args) > 1 else 0,
                "max_tokens": kwargs.get("max_tokens", args[3] if len(args) > 3 else 0),
            }

            erro = None
            try:
                with trace_span(nome, input_data=span_input, metadata=meta) as span:
                    resultado = func(*args, **kwargs)
                    # Extrai tokens do retorno (tuple: texto, usage)
                    if isinstance(resultado, tuple) and len(resultado) == 2:
                        texto, usage = resultado
                        if isinstance(usage, dict):
                            try:
                                for k in ("input_tokens", "output_tokens", "cache_read", "cache_created"):
                                    if k in usage:
                                        t.get_current_span().set_attribute(k, usage[k])
                            except Exception:
                                pass
                        span.output({"text_len": len(texto) if texto else 0})
                    return resultado
            except Exception as e:
                erro = e
                raise
            finally:
                latency_ms = round((time.time() - start) * 1000)
                try:
                    logger.debug("[Langfuse] {} — {}ms erro={}".format(nome, latency_ms, bool(erro)))
                except Exception:
                    pass
        return wrapper
    return decorator
