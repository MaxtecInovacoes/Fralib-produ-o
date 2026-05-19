"""
Token Tracker — Rastreia custo LLM por pipeline run
PRD #4: Visibilidade de custo por site gerado
"""

import time
import json
from typing import Optional

# ══════════════════════════════════════════════════════════════
# PREÇOS POR MILHÃO DE TOKENS (Anthropic, maio 2025)
# ══════════════════════════════════════════════════════════════
PRECOS_POR_MILHAO = {
    "claude-opus-4-7": {"input": 15.0, "output": 75.0, "cache_write": 18.75, "cache_read": 1.50},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_write": 3.75, "cache_read": 0.30},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0, "cache_write": 1.0, "cache_read": 0.08},
}


def _calcular_custo(model: str, usage: dict) -> float:
    """Calcula custo em USD de uma chamada."""
    precos = PRECOS_POR_MILHAO.get(model, PRECOS_POR_MILHAO["claude-sonnet-4-6"])
    custo = (
        (usage.get("input_tokens", 0) / 1_000_000) * precos["input"] +
        (usage.get("output_tokens", 0) / 1_000_000) * precos["output"] +
        (usage.get("cache_creation", 0) / 1_000_000) * precos["cache_write"] +
        (usage.get("cache_read", 0) / 1_000_000) * precos["cache_read"]
    )
    return custo


class TokenTracker:
    """Acumula usage de todas as chamadas LLM de um pipeline run."""

    def __init__(self, run_id: str, lead_nome: str, nicho: str):
        self.run_id = run_id
        self.lead_nome = lead_nome
        self.nicho = nicho
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
    """Salva resumo no PostgreSQL. Silencioso se falhar."""
    try:
        from core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO pipeline_token_usage
                (run_id, lead_nome, nicho, duracao_s, total_input_tokens, total_output_tokens,
                 cache_hit_ratio, custo_total_usd, por_agente, created_at)
                VALUES (:run_id, :lead_nome, :nicho, :duracao_s, :total_input, :total_output,
                        :cache_hit, :custo, :por_agente, NOW())
                ON CONFLICT (run_id) DO NOTHING
            """), {
                "run_id": resumo["run_id"],
                "lead_nome": resumo["lead"],
                "nicho": resumo["nicho"],
                "duracao_s": resumo["duracao_s"],
                "total_input": resumo["total_input_tokens"],
                "total_output": resumo["total_output_tokens"],
                "cache_hit": resumo["cache_hit_ratio"],
                "custo": resumo["custo_total_usd"],
                "por_agente": json.dumps(resumo["por_agente"]),
            })
            conn.commit()
    except Exception as e:
        print(f"[TRACKING] Erro ao salvar no DB: {e}")


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
