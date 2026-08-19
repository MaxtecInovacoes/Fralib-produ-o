"""Observability — Trace + salvar_trace.

Fallback defensivo: se Langfuse não estiver configurado,
Trace é um stub funcional (interface mínima exigida pelo
worker) e salvar_trace persiste em pipeline_traces (best-effort).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("fralib.observability")


# ── Span ──────────────────────────────────────────────


class _Span:
    """Span interno — interface mínima exigida pelo worker."""

    def __init__(self, nome: str, tipo: str, parent_id: str) -> None:
        self.nome = nome
        self.tipo = tipo
        self.parent_id = parent_id
        self.status_final: str = "ok"

    def finalizar(self, status: str) -> None:
        self.status_final = status


# ── Trace ─────────────────────────────────────────────


class Trace:
    """Stub funcional — não depende de Langfuse.

    Aceita os mesmos kwargs que o worker passa
    (``run_id``, ``lead_nome``, ``nicho``) e expõe a interface
    mínima usada em ``worker.py``.
    """

    def __init__(
        self,
        *,
        run_id: str,
        lead_nome: str,
        nicho: str,
        **_kwargs: Any,
    ) -> None:
        self.run_id = run_id
        self.lead_nome = (lead_nome or "")[:100]
        self.nicho = nicho or ""
        self.duracao_total_ms: int = 0
        self.status: str = "unknown"
        self.complexidade: str = ""
        self._spans: list[_Span] = []
        self._current: _Span | None = None

    def iniciar_span(self, nome: str, tipo: str, parent_id: str) -> _Span:
        span = _Span(nome, tipo, parent_id)
        self._spans.append(span)
        self._current = span
        return span

    def span_atual(self) -> _Span:
        if self._current is None:
            self._current = _Span("fallback", "worker", "")
        return self._current


# ── Persistência ──────────────────────────────────────


def salvar_trace(trace: Trace) -> None:
    """Persiste em ``pipeline_traces`` (best-effort).

    O worker já envolve esta chamada em ``try/except``; esta
    defesa extra cobre usos diretos fora do worker.
    """
    try:
        from sqlalchemy import text

        from backend.core.database import SessionLocal

        db = SessionLocal()
        db.execute(
            text(
                """
                INSERT INTO pipeline_traces
                    (trace_id, run_id, tenant_id, lead_nome, nicho, tier,
                     complexidade, duracao_total_ms, status,
                     total_input_tokens, total_output_tokens, total_cache_hit,
                     custo_total_usd, total_chamadas_llm, spans_json, created_at)
                VALUES
                    (:trace_id, :run_id, :tenant_id, :lead_nome, :nicho, :tier,
                     :complexidade, :duracao, :status,
                     :in_tok, :out_tok, :cache_hit,
                     :custo, :chamadas, :spans, NOW())
                """
            ),
            {
                "trace_id": trace.run_id,
                "run_id": trace.run_id,
                "tenant_id": 0,
                "lead_nome": trace.lead_nome,
                "nicho": trace.nicho,
                "tier": "",
                "complexidade": trace.complexidade or "",
                "duracao": trace.duracao_total_ms,
                "status": trace.status,
                "in_tok": 0,
                "out_tok": 0,
                "cache_hit": 0,
                "custo": 0,
                "chamadas": 0,
                "spans": [],
            },
        )
        db.commit()
        db.close()
    except Exception as exc:
        logger.warning("[OBS] Falha ao salvar trace: %s", exc)


__all__ = ["Trace", "salvar_trace"]
