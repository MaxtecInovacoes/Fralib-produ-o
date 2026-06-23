"""Streaming de resposta (Feature 3 do roadmap 10/10).

Usa call_claude_stream do llm_direct.py pra gerar chunks incrementais.
Expõe via SSE (Server-Sent Events) pro Studio ver resposta sendo digitada.
WhatsApp real continua mandando mensagem unica (meowhats nao suporta typing).
"""

from __future__ import annotations

import logging
from typing import Generator

logger = logging.getLogger(__name__)


def stream_franz_reply(
    system: str,
    user: str,
    model: str = "sonnet",
    max_tokens: int = 800,
    temperature: float = 0.7,
    agent_name: str = "sdr_studio_stream",
) -> Generator[str, None, str]:
    """Generator que yields chunks da resposta do Franz e retorna o texto completo.

    Args:
        system: system prompt completo.
        user: user prompt.
        model: modelo Claude.
        max_tokens: limite de tokens.
        temperature: criatividade.
        agent_name: nome do agente (logs).

    Yields:
        str: chunks de texto (1-5 palavras por chunk tipicamente).

    Returns:
        str: texto completo acumulado.
    """
    accumulated: list[str] = []

    def _on_chunk(chunk: str):
        accumulated.append(chunk)

    try:
        from agents.llm_direct import call_claude_stream
        call_claude_stream(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            agent_name=agent_name,
            on_chunk=_on_chunk,
            enable_context=False,
        )
    except Exception as e:
        logger.warning(f"[stream] call_claude_stream falhou: {e}")
        # Fallback: call sem stream
        from agents.llm_direct import call_claude
        full = call_claude(
            system=system, user=user, model=model,
            max_tokens=max_tokens, temperature=temperature,
            agent_name=agent_name, enable_context=False,
        )
        accumulated.append(full)

    full_text = "".join(accumulated)

    # Yield em chunks semanticos (palavras com whitespace)
    words = full_text.split(" ")
    buffer: list[str] = []
    for i, w in enumerate(words):
        buffer.append(w)
        # Yield a cada 2-3 palavras ou final
        if len(buffer) >= 3 or i == len(words) - 1:
            chunk = " ".join(buffer) + (" " if i < len(words) - 1 else "")
            yield chunk
            buffer = []

    return full_text


def sse_format(chunk: str, event: str = "message") -> str:
    """Formata um chunk no protocolo SSE."""
    return f"event: {event}\ndata: {chunk}\n\n"