"""
Observability — Traces completos por pipeline run (PRD #10)
Padrão: Distributed Tracing (LangSmith/Braintrust inspired)
Cada run = trace, cada fase = span, cada chamada LLM = evento.
"""

import time
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Span:
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    nome: str = ""
    agente: str = ""
    modelo: str = ""
    inicio: float = field(default_factory=time.time)
    fim: Optional[float] = None
    duracao_ms: Optional[int] = None
    status: str = "running"
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hit_tokens: int = 0
    custo_usd: float = 0.0
    erro: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    eventos: list = field(default_factory=list)

    def finalizar(self, status: str, erro: str = None):
        self.fim = time.time()
        self.duracao_ms = int((self.fim - self.inicio) * 1000)
        self.status = status
        self.erro = erro

    def adicionar_evento(self, tipo: str, dados: dict):
        self.eventos.append({
            "timestamp": time.time(),
            "tipo": tipo,
            "dados": dados,
        })


@dataclass
class Trace:
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    run_id: str = ""
    lead_nome: str = ""
    nicho: str = ""
    tier: str = ""
    complexidade: str = ""
    inicio: float = field(default_factory=time.time)
    fim: Optional[float] = None
    duracao_total_ms: Optional[int] = None
    status: str = "running"
    spans: list = field(default_factory=list)

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_hit: int = 0
    custo_total_usd: float = 0.0
    total_chamadas_llm: int = 0

    def iniciar_span(self, nome: str, agente: str, modelo: str = "") -> Span:
        span = Span(nome=nome, agente=agente, modelo=modelo)
        self.spans.append(span)
        return span

    def span_atual(self) -> Optional[Span]:
        for s in reversed(self.spans):
            if s.status == "running":
                return s
        return None

    def finalizar(self, status: str):
        self.fim = time.time()
        self.duracao_total_ms = int((self.fim - self.inicio) * 1000)
        self.status = status
        self._agregar_metricas()

    def _agregar_metricas(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_hit = 0
        self.custo_total_usd = 0.0
        self.total_chamadas_llm = 0
        for span in self.spans:
            self.total_input_tokens += span.input_tokens
            self.total_output_tokens += span.output_tokens
            self.total_cache_hit += span.cache_hit_tokens
            self.custo_total_usd += span.custo_usd
            self.total_chamadas_llm += len(span.eventos)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "lead_nome": self.lead_nome,
            "nicho": self.nicho,
            "tier": self.tier,
            "complexidade": self.complexidade,
            "inicio": self.inicio,
            "fim": self.fim,
            "duracao_total_ms": self.duracao_total_ms,
            "status": self.status,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cache_hit": self.total_cache_hit,
            "custo_total_usd": round(self.custo_total_usd, 4),
            "total_chamadas_llm": self.total_chamadas_llm,
            "spans": [
                {
                    "span_id": s.span_id,
                    "nome": s.nome,
                    "agente": s.agente,
                    "modelo": s.modelo,
                    "duracao_ms": s.duracao_ms,
                    "status": s.status,
                    "input_tokens": s.input_tokens,
                    "output_tokens": s.output_tokens,
                    "cache_hit_tokens": s.cache_hit_tokens,
                    "custo_usd": round(s.custo_usd, 4),
                    "erro": s.erro,
                    "eventos_count": len(s.eventos),
                }
                for s in self.spans
            ],
        }


def salvar_trace(trace: Trace):
    try:
        from backend.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO pipeline_traces
                (trace_id, run_id, lead_nome, nicho, tier, complexidade,
                 duracao_total_ms, status, total_input_tokens, total_output_tokens,
                 total_cache_hit, custo_total_usd, total_chamadas_llm, spans_json, created_at)
                VALUES (:trace_id, :run_id, :lead_nome, :nicho, :tier, :complexidade,
                        :duracao_ms, :status, :input_t, :output_t,
                        :cache_hit, :custo, :chamadas, :spans, NOW())
                ON CONFLICT (trace_id) DO UPDATE SET
                    spans_json = EXCLUDED.spans_json,
                    status = EXCLUDED.status,
                    duracao_total_ms = EXCLUDED.duracao_total_ms,
                    total_input_tokens = EXCLUDED.total_input_tokens,
                    total_output_tokens = EXCLUDED.total_output_tokens,
                    total_cache_hit = EXCLUDED.total_cache_hit,
                    custo_total_usd = EXCLUDED.custo_total_usd,
                    total_chamadas_llm = EXCLUDED.total_chamadas_llm
            """), {
                "trace_id": trace.trace_id,
                "run_id": trace.run_id,
                "lead_nome": trace.lead_nome,
                "nicho": trace.nicho,
                "tier": trace.tier,
                "complexidade": trace.complexidade,
                "duracao_ms": trace.duracao_total_ms,
                "status": trace.status,
                "input_t": trace.total_input_tokens,
                "output_t": trace.total_output_tokens,
                "cache_hit": trace.total_cache_hit,
                "custo": round(trace.custo_total_usd, 4),
                "chamadas": trace.total_chamadas_llm,
                "spans": json.dumps(trace.to_dict()["spans"], ensure_ascii=False),
            })
            conn.commit()
    except Exception as e:
        print(f"[TRACE][WARN] Falha ao salvar: {e}")


def formatar_trace_log(trace: Trace) -> str:
    linhas = [
        "═" * 60,
        f"[TRACE] {trace.trace_id} | {trace.lead_nome} | {trace.nicho} | {trace.status.upper()}",
        f"[TRACE] Duração: {(trace.duracao_total_ms or 0)/1000:.1f}s | Chamadas: {trace.total_chamadas_llm} | Custo: ${trace.custo_total_usd:.3f}",
    ]
    if trace.total_input_tokens:
        pct = trace.total_cache_hit / max(trace.total_input_tokens, 1) * 100
        linhas.append(f"[TRACE] Cache hit: {trace.total_cache_hit}/{trace.total_input_tokens} ({pct:.0f}%)")
    linhas.append("[TRACE] Spans:")
    for s in trace.spans:
        icon = "✓" if s.status == "success" else "✗" if s.status == "error" else "⊘"
        dur = f"{s.duracao_ms:>6}ms" if s.duracao_ms else "     -"
        linhas.append(f"  {icon} {s.nome:12} | {dur} | {s.modelo or '-':8} | ${s.custo_usd:.3f} | {s.erro or 'ok'}")
    linhas.append("═" * 60)
    return "\n".join(linhas)
