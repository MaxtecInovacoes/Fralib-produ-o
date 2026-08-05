"""
Token Tracker — Rastreia custo LLM por pipeline run
PRD #4: Visibilidade de custo por site gerado
"""

import time
from typing import Optional

from backend.domain.llm_pricing import estimate_llm_cost_usd


def _calcular_custo(model: str, usage: dict) -> float:
    """Calcula custo em USD de uma chamada."""
    return estimate_llm_cost_usd(model, usage)


class TokenTracker:
    """Acumula usage de todas as chamadas LLM de um pipeline run."""

    def __init__(self, run_id: str, lead_nome: str, nicho: str, tenant_id=None, job_id=None):
        self.run_id = run_id
        self.lead_nome = lead_nome
        self.nicho = nicho
        self.tenant_id = tenant_id
        self.job_id = job_id
        self.inicio = time.time()
        self.chamadas = []

    def registrar(self, agente: str, model: str, usage: dict):
        """Registra uma chamada LLM."""
        self.chamadas.append({
            "agente": agente or "unknown",
            "model": model,
            "timestamp": time.time(),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cache_creation": usage.get("cache_creation_input_tokens", 0),
            "cache_read": usage.get("cache_read_input_tokens", 0),
        })

    def resumo(self) -> dict:
        """Retorna resumo consolidado do run."""
        por_agente = {}
        total_input = 0
        total_output = 0
        total_cache_hit = 0
        total_custo = 0.0

        for c in self.chamadas:
            agente = c["agente"]
            if agente not in por_agente:
                por_agente[agente] = {"chamadas": 0, "input": 0, "output": 0, "cache_hit": 0, "custo": 0.0}

            custo = _calcular_custo(c["model"], c)
            por_agente[agente]["chamadas"] += 1
            por_agente[agente]["input"] += c["input_tokens"]
            por_agente[agente]["output"] += c["output_tokens"]
            por_agente[agente]["cache_hit"] += c["cache_read"]
            por_agente[agente]["custo"] += round(custo, 6)

            total_input += c["input_tokens"]
            total_output += c["output_tokens"]
            total_cache_hit += c["cache_read"]
            total_custo += custo

        return {
            "run_id": self.run_id,
            "tenant_id": self.tenant_id,
            "job_id": self.job_id,
            "lead": self.lead_nome,
            "nicho": self.nicho,
            "duracao_s": round(time.time() - self.inicio, 1),
            "total_chamadas": len(self.chamadas),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cache_hit_tokens": total_cache_hit,
            "cache_hit_ratio": round(total_cache_hit / max(total_input, 1) * 100, 1),
            "custo_total_usd": round(total_custo, 4),
            "por_agente": por_agente,
            "agente_mais_caro": max(por_agente, key=lambda k: por_agente[k]["custo"]) if por_agente else None,
        }


def log_tracking(resumo: dict):
    """Imprime resumo formatado no stdout (capturado pelo SSE)."""
    resumo = _with_ledger_totals(resumo)
    print("═" * 55)
    print(f"[TRACKING] Run {resumo['run_id']} | Lead: {resumo['lead']} | Nicho: {resumo['nicho']}")
    print(f"[TRACKING] Duração: {resumo['duracao_s']}s | Chamadas LLM: {resumo['total_chamadas']}")
    _in_k = resumo['total_input_tokens'] / 1000
    _out_k = resumo['total_output_tokens'] / 1000
    _cache_k = resumo['total_cache_hit_tokens'] / 1000
    print(f"[TRACKING] Tokens: input={_in_k:.1f}k output={_out_k:.1f}k cache_hit={_cache_k:.1f}k ({resumo['cache_hit_ratio']}%)")
    print(f"[TRACKING] Custo total: ${resumo['custo_total_usd']:.4f}")
    if resumo['por_agente']:
        print("[TRACKING] Por agente:")
        total = resumo['custo_total_usd'] or 0.0001
        for ag, dados in sorted(resumo['por_agente'].items(), key=lambda x: x[1]['custo'], reverse=True):
            pct = round(dados['custo'] / total * 100)
            print(f"  - {ag:12s} ${dados['custo']:.4f} ({pct:2d}%) | {dados['chamadas']} chamadas | {dados['input']/1000:.1f}k input")
    if resumo['agente_mais_caro']:
        print(f"[TRACKING] Agente mais caro: {resumo['agente_mais_caro']}")
    print("═" * 55)
def salvar_tracking(resumo: dict):
    """Salva resumo de tracking. Agora e no-op — a escrita canonica e em llm_budget_ledger.
    Historico: escrevia em pipeline_token_usage ate 2026-06. Essa tabela agora
    e legado; o ledger canonico e llm_budget_ledger (populado por call_claude).
    A funcao permanece aqui como API compat para nao quebrar chamadas existentes.
    """
    # Canonical LLM cost/tokens agora vao para llm_budget_ledger via llm_direct.py
    # e para jobs.llm_tokens_used/jobs.llm_cost_estimate via job_queue.mark_success()
    pass
def _with_ledger_totals(resumo: dict) -> dict:
    """Prefer the canonical LLM ledger when it has rows for this run/job."""
    run_id = resumo.get("run_id")
    job_id = resumo.get("job_id")
    if not run_id and not job_id:
        return resumo
    try:
        from core.database import engine
        from sqlalchemy import text
        clauses = []
        params = {}
        if run_id:
            clauses.append("run_id = :run_id")
            params["run_id"] = run_id
        if job_id:
            clauses.append("job_id = :job_id")
            params["job_id"] = job_id
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    f"""
                    SELECT
                        COUNT(*) AS total_calls,
                        COALESCE(SUM(input_tokens), 0) AS input_tokens,
                        COALESCE(SUM(output_tokens), 0) AS output_tokens,
                        COALESCE(SUM(cache_read_tokens), 0) AS cache_read_tokens,
                        COALESCE(SUM(cost_usd), 0) AS cost_usd
                    FROM llm_budget_ledger
                    WHERE {' OR '.join(clauses)}
                    """
                ),
                params,
            ).mappings().first()
        if not row or int(row.get("total_calls") or 0) <= 0:
            return resumo
        merged = dict(resumo)
        merged["total_chamadas"] = max(int(merged.get("total_chamadas") or 0), int(row["total_calls"] or 0))
        merged["total_input_tokens"] = int(row["input_tokens"] or 0)
        merged["total_output_tokens"] = int(row["output_tokens"] or 0)
        merged["total_cache_hit_tokens"] = int(row["cache_read_tokens"] or 0)
        merged["cache_hit_ratio"] = round(
            merged["total_cache_hit_tokens"] / max(merged["total_input_tokens"], 1) * 100,
            1,
        )
        merged["custo_total_usd"] = round(float(row["cost_usd"] or 0), 4)
        merged["ledger_source"] = "llm_budget_ledger"
        return merged
    except Exception as exc:
        print(f"[TRACKING] Aviso: falha ao agregar ledger canonico: {exc}")
        return resumo


# ══════════════════════════════════════════════════════════════
# THREAD-LOCAL TRACKER — permite que call_claude registre automaticamente
# ══════════════════════════════════════════════════════════════
import threading
_thread_local = threading.local()


def set_tracker(tracker: Optional['TokenTracker']):
    """Define o tracker ativo pro thread atual."""
    _thread_local.tracker = tracker


def get_tracker() -> Optional['TokenTracker']:
    """Retorna o tracker ativo pro thread atual."""
    return getattr(_thread_local, 'tracker', None)
