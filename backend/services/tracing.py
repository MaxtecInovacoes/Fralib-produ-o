"""Tracing module para FraLib (Sprint 5 - v1.8).

Observabilidade dos 4 agentes (Nicho/Arquiteto/Builder/Validador) + Franz (SDR).

3 modos:
1. FRALIB_TRACING=0 (default) - tracing desabilitado (zero overhead)
2. FRALIB_TRACING=1 - tracing local (JSONL em logs/traces/)
3. FRALIB_TRACING=2 - tracing LangSmith (cloud, requer API key)

Estrutura de trace:
- run_id: UUID unico
- agent: nome do agente (nicho/arquiteto/builder/validador/franz)
- operation: nome da operacao (run/invoke/llm_call/tool_call)
- start/end timestamps
- inputs/outputs (truncated)
- latency_ms
- cost_usd (estimado)
- tokens (input/output)
- model (claude-haiku/sonnet/opus)
- success/error
- metadata: extra context

Uso:
    from backend.services.tracing import trace_run, trace_llm_call

    @trace_run(agent="nicho", operation="run")
    def run_nicho(lead_id, segmento):
        # Tudo automaticamente traceado
        result = llm_call(...)  # tambem traceado
        return result
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════

TRACING_ENABLED = os.getenv("FRALIB_TRACING", "0") in ("1", "2")
TRACES_DIR = Path(os.getenv("FRALIB_TRACES_DIR", "logs/traces"))
TRACES_DIR.mkdir(parents=True, exist_ok=True)

# LangSmith opcional
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "fralib-sdk")
LANGSMITH_TRACING_ENABLED = TRACING_ENABLED and os.getenv("FRALIB_TRACING") == "2" and LANGSMITH_API_KEY

# LangSmith client (lazy init)
_langsmith_client = None


def _get_langsmith_client():
    """Lazy init do LangSmith client."""
    global _langsmith_client
    if not LANGSMITH_TRACING_ENABLED:
        return None
    if _langsmith_client is None:
        try:
            from langsmith import Client
            _langsmith_client = Client(api_key=LANGSMITH_API_KEY)
        except ImportError:
            logger.warning("[tracing] langsmith nao instalado, modo 2 desabilitado")
            return None
        except Exception as e:
            logger.warning(f"[tracing] LangSmith init falhou: {e}")
            return None
    return _langsmith_client


# ════════════════════════════════════════════════════════════════════
# COST ESTIMATION (USD por 1k tokens)
# ════════════════════════════════════════════════════════════════════

COST_PER_1K_TOKENS = {
    "claude-haiku-4-5": {"input": 0.001, "output": 0.005},
    "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "claude-opus-4-8": {"input": 0.015, "output": 0.075},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estima custo USD dado modelo e tokens."""
    if model not in COST_PER_1K_TOKENS:
        return 0.0
    rates = COST_PER_1K_TOKENS[model]
    cost = (input_tokens / 1000 * rates["input"]) + (output_tokens / 1000 * rates["output"])
    return round(cost, 6)


# ════════════════════════════════════════════════════════════════════
# CORE TRACING
# ════════════════════════════════════════════════════════════════════

def _write_trace(trace: dict) -> None:
    """Escreve trace em JSONL append-only."""
    if not TRACING_ENABLED:
        return
    try:
        # File por dia (facil de processar)
        day = time.strftime("%Y-%m-%d")
        path = TRACES_DIR / f"traces_{day}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        logger.debug(f"[tracing] write falhou: {e}")


def _send_to_langsmith(trace: dict) -> None:
    """Envia trace para LangSmith (se habilitado)."""
    client = _get_langsmith_client()
    if client is None:
        return
    try:
        # Send como feedback/run
        client.create_run(
            name=trace.get("operation", "unknown"),
            run_type="chain",
            inputs=trace.get("inputs", {}),
            outputs=trace.get("outputs", {}),
            start_time=trace.get("start_ts"),
            end_time=trace.get("end_ts"),
            extra={
                "agent": trace.get("agent"),
                "model": trace.get("model"),
                "latency_ms": trace.get("latency_ms"),
                "cost_usd": trace.get("cost_usd"),
                "input_tokens": trace.get("input_tokens"),
                "output_tokens": trace.get("output_tokens"),
                "success": trace.get("success"),
            },
            error=trace.get("error"),
        )
    except Exception as e:
        logger.debug(f"[tracing] langsmith send falhou: {e}")


@contextmanager
def trace_run(
    agent: str,
    operation: str,
    inputs: Optional[dict] = None,
    metadata: Optional[dict] = None,
):
    """Context manager para tracing de operacoes.

    Args:
        agent: nome do agente (nicho/arquiteto/builder/validador/franz).
        operation: nome da operacao (run/invoke/llm_call/tool_call).
        inputs: dict com inputs (truncated a 1000 chars).
        metadata: extra context.

    Usage:
        with trace_run("nicho", "run", inputs={"lead_id": 123}):
            result = do_work()
    """
    if not TRACING_ENABLED:
        yield
        return

    run_id = str(uuid.uuid4())
    start = time.time()
    start_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
    trace = {
        "run_id": run_id,
        "agent": agent,
        "operation": operation,
        "start_ts": start_iso,
        "start_unix": start,
        "inputs": _truncate(inputs),
        "metadata": metadata or {},
        "success": None,
    }

    try:
        yield trace
        trace["success"] = True
    except Exception as e:
        trace["success"] = False
        trace["error"] = str(e)[:500]
        raise
    finally:
        end = time.time()
        trace["end_ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        trace["end_unix"] = end
        trace["latency_ms"] = int((end - start) * 1000)
        _write_trace(trace)
        _send_to_langsmith(trace)


def _truncate(obj: Any, max_len: int = 1000) -> Any:
    """Trunca strings longas no trace (evita inchar JSONL)."""
    if isinstance(obj, str):
        return obj[:max_len] + ("..." if len(obj) > max_len else "")
    if isinstance(obj, dict):
        return {k: _truncate(v, max_len) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_truncate(v, max_len) for v in obj[:50]]
    return obj


# ════════════════════════════════════════════════════════════════════
# DECORATORS
# ════════════════════════════════════════════════════════════════════

def trace_agent(agent: str):
    """Decorator para tracejar um agente.run() inteiro.

    Usage:
        class NichoAgent:
            @trace_agent("nicho")
            def run(self, lead_id, segmento):
                pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            inputs = {"args": _truncate(args), "kwargs": _truncate(kwargs)}
            with trace_run(agent, func.__name__, inputs=inputs):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def trace_llm_call(agent: str, model: str = ""):
    """Decorator para tracejar uma chamada LLM especifica.

    Usage:
        @trace_llm_call("nicho", model="claude-sonnet-4-6")
        def call_llm(prompt):
            return llm.invoke(prompt)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            inputs = {"args": _truncate(args), "kwargs": _truncate(kwargs)}
            with trace_run(
                agent,
                f"llm_call:{func.__name__}",
                inputs=inputs,
                metadata={"model": model},
            ) as trace:
                result = func(*args, **kwargs)
                # Tenta extrair tokens/custo do result
                _extract_llm_metrics(result, trace, model)
                return result
        return wrapper
    return decorator


def _extract_llm_metrics(result: Any, trace: dict, model: str) -> None:
    """Extrai tokens e custo de um result LLM (se possivel)."""
    if not isinstance(result, dict):
        return
    usage = result.get("usage") or result.get("usage_metadata") or {}
    if usage:
        input_tokens = int(usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0) or usage.get("completion_tokens", 0))
        trace["input_tokens"] = input_tokens
        trace["output_tokens"] = output_tokens
        trace["model"] = model or result.get("model", "")
        trace["cost_usd"] = estimate_cost(trace["model"], input_tokens, output_tokens)


# ════════════════════════════════════════════════════════════════════
# ANALYTICS (queries simples sobre traces)
# ════════════════════════════════════════════════════════════════════

def get_stats(agent: str = None, days: int = 1) -> dict:
    """Estatisticas agregadas dos traces.

    Args:
        agent: filtra por agente (None = todos).
        days: ultimos N dias.

    Returns:
        Dict com {count, avg_latency_ms, total_cost_usd, success_rate}.
    """
    if not TRACING_ENABLED:
        return {"enabled": False}
    stats = {"count": 0, "errors": 0, "total_latency_ms": 0, "total_cost_usd": 0.0,
             "total_input_tokens": 0, "total_output_tokens": 0}
    try:
        for day_offset in range(days):
            day = time.strftime("%Y-%m-%d", time.localtime(time.time() - day_offset * 86400))
            path = TRACES_DIR / f"traces_{day}.jsonl"
            if not path.is_file():
                continue
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        t = json.loads(line)
                        if agent and t.get("agent") != agent:
                            continue
                        stats["count"] += 1
                        if not t.get("success"):
                            stats["errors"] += 1
                        stats["total_latency_ms"] += t.get("latency_ms", 0)
                        stats["total_cost_usd"] += t.get("cost_usd", 0.0)
                        stats["total_input_tokens"] += t.get("input_tokens", 0)
                        stats["total_output_tokens"] += t.get("output_tokens", 0)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.warning(f"[tracing] get_stats falhou: {e}")
    if stats["count"] > 0:
        stats["avg_latency_ms"] = stats["total_latency_ms"] // stats["count"]
        stats["success_rate"] = 1.0 - (stats["errors"] / stats["count"])
    else:
        stats["avg_latency_ms"] = 0
        stats["success_rate"] = 1.0
    return stats


def is_enabled() -> bool:
    """Verifica se tracing esta ativo."""
    return TRACING_ENABLED