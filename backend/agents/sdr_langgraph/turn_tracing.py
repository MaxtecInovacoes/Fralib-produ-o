"""SDR Turn Tracing.

Cria 1 trace + 3 spans por turno do Franz:
- span 1: intent_classifier (regex + Haiku fallback)
- span 2: orchestrator_decision (FSM transition)
- span 3: llm_call (Claude response)

Feature #4 do roadmap 10/10.
"""

from __future__ import annotations

import logging
import time
import uuid

logger = logging.getLogger(__name__)


class SDRTurnTrace:
    """Wrapper do Trace nativo do observability.py pra uso no fluxo SDR.

    Uso:
        trace = SDRTurnTrace(lead_id="abc", lead_nome="Academia X")
        s = trace.start_span("intent_classifier")
        ... fazer trabalho ...
        trace.end_span(s, input_tokens=10, cost_usd=0.0001)

        s2 = trace.start_span("llm_call", modelo="sonnet")
        ...
        trace.end_span(s2, output_tokens=200, cost_usd=0.01)

        trace.persist()  # chama salvar_trace() do observability.py
    """

    def __init__(self, lead_id: str, lead_nome: str = "", nicho: str = ""):
        self.trace_id = f"sdr-{uuid.uuid4().hex[:12]}"
        self.lead_id = lead_id
        self.lead_nome = lead_nome or lead_id
        self.nicho = nicho or "sdr_whatsapp"
        self.t0 = time.time()
        self.spans: list[dict] = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.custo_total_usd = 0.0
        self.status = "running"
        self.error: str | None = None

    def start_span(self, nome: str, **metadata) -> dict:
        """Inicia um span. Retorna handle pra fechar depois."""
        span = {
            "nome": nome,
            "inicio": time.time(),
            "fim": None,
            "duracao_ms": 0,
            "metadata": metadata,
        }
        self.spans.append(span)
        return span

    def end_span(self, span: dict, status: str = "completed", **metadata):
        """Fecha um span aberto."""
        span["fim"] = time.time()
        span["duracao_ms"] = int((span["fim"] - span["inicio"]) * 1000)
        span["status"] = status
        # Merge metadata adicional
        span["metadata"].update(metadata)
        # Acumular tokens/custo se vierem
        if "input_tokens" in metadata:
            self.total_input_tokens += int(metadata["input_tokens"])
        if "output_tokens" in metadata:
            self.total_output_tokens += int(metadata["output_tokens"])
        if "cost_usd" in metadata:
            self.custo_total_usd += float(metadata["cost_usd"])

    def persist(self):
        """Persiste o trace em pipeline_traces."""
        try:
            from backend.observability import salvar_trace, Trace, Span
            # Converter dicts -> objetos Span
            span_objects = []
            for s in self.spans:
                span_obj = Span(
                    nome=s["nome"],
                    agente=s["metadata"].get("agente", "franz"),
                    modelo=s["metadata"].get("modelo", ""),
                )
                span_obj.fim = s.get("fim") or time.time()
                span_obj.duracao_ms = s.get("duracao_ms", 0)
                span_obj.status = s.get("status", "completed")
                span_obj.metadata = s.get("metadata", {})
                span_objects.append(span_obj)

            t = Trace(
                trace_id=self.trace_id,
                run_id=f"sdr-{self.lead_id}",
                lead_nome=self.lead_nome,
                nicho=self.nicho,
                tier="sdr",
                complexidade="chat_turn",
                status=self.status,
                total_input_tokens=self.total_input_tokens,
                total_output_tokens=self.total_output_tokens,
                total_cache_hit=0,
                custo_total_usd=self.custo_total_usd,
                total_chamadas_llm=sum(1 for s in self.spans if s["nome"] == "llm_call"),
                spans=span_objects,
            )
            t.fim = time.time()
            t.duracao_total_ms = int((t.fim - self.t0) * 1000)
            salvar_trace(t)
            logger.info(
                f"[sdr_trace] {self.trace_id} lead={self.lead_id} "
                f"duracao={t.duracao_total_ms}ms "
                f"tokens={self.total_input_tokens}+{self.total_output_tokens} "
                f"custo=${self.custo_total_usd:.4f} status={self.status}"
            )
        except Exception as e:
            logger.warning(f"[sdr_trace] persist falhou: {e}")