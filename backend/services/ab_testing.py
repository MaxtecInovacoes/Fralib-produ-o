"""Sistema de A/B testing + outcome tracking + aprendizado automatico.

Mede QUAL abordagem funciona melhor e re-engaja leads abandonados.

Conceitos:
- Outcome: lead respondeu, lead converteu, lead deu opt_out
- Por variant (A, B, C, D), mede: response_rate, conversion_rate
- Auto-genera lesson: 'variant X tem 2x mais conversao que Y, use mais'
- Re-engajamento: leads parados > 7 dias recebem followup personalizado
"""

from __future__ import annotations

import json
import os
import random  # usado por choose_variant (exploration)
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import text


# ════════════════════════════════════════════════════════════════════
# OUTCOME TRACKING
# ════════════════════════════════════════════════════════════════════

@dataclass
class VariantMetrics:
    """Metricas de uma variant de abordagem."""
    variant: str
    sent: int = 0
    responses: int = 0
    conversions: int = 0
    opt_outs: int = 0
    last_updated: str = ""

    @property
    def response_rate(self) -> float:
        return self.responses / max(1, self.sent)

    @property
    def conversion_rate(self) -> float:
        return self.conversions / max(1, self.sent)


# Cache em memoria (evita queries repetidas)
_variant_metrics: dict[str, VariantMetrics] = {}
_metrics_loaded_at: float = 0
_METRICS_TTL = 300  # 5 min


def _load_variant_metrics(user_id: int) -> dict[str, VariantMetrics]:
    """Carrega metricas de variants do banco."""
    global _metrics_loaded_at
    if time.time() - _metrics_loaded_at < _METRICS_TTL and _variant_metrics:
        return _variant_metrics

    # Lazy import pra nao quebrar modulo
    try:
        from backend.core.database import engine
        with engine.connect() as c:
            rows = c.execute(text("""
                SELECT
                    l.variant,
                    COUNT(DISTINCT CASE WHEN i.direcao = 'saida' THEN i.id END) as sent,
                    COUNT(DISTINCT CASE WHEN i.direcao = 'entrada' AND i.criado_em > first_sent.criado_em THEN i.id END) as responses,
                    COUNT(DISTINCT CASE WHEN l.deal_status = 'won' OR l.deal_status = 'fechado' THEN l.id END) as conversions,
                    COUNT(DISTINCT CASE WHEN l.deal_status = 'opt_out' OR l.deal_status = 'perdidos' THEN l.id END) as opt_outs
                FROM leads l
                LEFT JOIN interacoes i ON i.lead_id = l.id AND i.user_id = l.user_id
                LEFT JOIN (
                    SELECT lead_id, MIN(criado_em) as criado_em
                    FROM interacoes
                    WHERE direcao = 'saida' AND user_id = :uid
                    GROUP BY lead_id
                ) first_sent ON first_sent.lead_id = l.id
                WHERE l.user_id = :uid
                  AND l.variant IS NOT NULL
                  AND l.criado_em > NOW() - INTERVAL '30 days'
                GROUP BY l.variant
            """), {"uid": user_id}).fetchall()
    except Exception as e:
        print(f"[variant_metrics] DB query falhou: {e}")
        return _variant_metrics

    new_metrics = {}
    for row in rows:
        v = row[0] or "A"
        new_metrics[v] = VariantMetrics(
            variant=v,
            sent=row[1] or 0,
            responses=row[2] or 0,
            conversions=row[3] or 0,
            opt_outs=row[4] or 0,
            last_updated=datetime.now().isoformat(),
        )

    _variant_metrics.clear()
    _variant_metrics.update(new_metrics)
    _metrics_loaded_at = time.time()
    return _variant_metrics


def choose_variant(user_id: int) -> str:
    """Escolhe variant com melhor conversion_rate, com 10% exploration."""
    metrics = _load_variant_metrics(user_id)

    # Se tem metricas, escolhe a melhor (com 10% exploration)
    if metrics:
        if random.random() < 0.10:  # 10% exploration
            return random.choice(list(metrics.keys()))

        # Ordena por conversion_rate
        best = max(metrics.values(), key=lambda m: m.conversion_rate)
        if best.conversion_rate > 0:  # so escolhe melhor se converteu pelo menos 1
            return best.variant

    # Cold start: round-robin
    return random.choice(["A", "B", "C", "D"])


# ════════════════════════════════════════════════════════════════════
# RE-ENGAGEMENT: leads abandonados
# ════════════════════════════════════════════════════════════════════

def find_abandoned_leads(user_id: int, days_idle: int = 7) -> list[dict]:
    """Encontra leads que pararam de responder.

    Args:
        user_id: tenant
        days_idle: dias sem interacao

    Returns:
        Lista de dicts {lead_id, nome, telefone, last_msg_days, segment}
    """
    try:
        from backend.core.database import engine
        with engine.connect() as c:
            rows = c.execute(text("""
                SELECT
                    l.id, l.nome, l.telefone, l.segmento, l.sdr_stage,
                    MAX(i.criado_em) as last_interaction,
                    EXTRACT(DAY FROM NOW() - MAX(i.criado_em))::int as days_idle,
                    (SELECT mensagem FROM interacoes
                     WHERE lead_id = l.id AND direcao = 'entrada'
                     ORDER BY criado_em DESC LIMIT 1) as last_lead_msg
                FROM leads l
                LEFT JOIN interacoes i ON i.lead_id = l.id AND i.user_id = l.user_id
                WHERE l.user_id = :uid
                  AND l.status = 'concluido'
                  AND l.deal_status NOT IN ('won', 'fechado', 'opt_out', 'perdidos')
                  AND l.sdr_stage IS NOT NULL
                  AND l.opt_out_pending = false
                GROUP BY l.id, l.nome, l.telefone, l.segmento, l.sdr_stage
                HAVING MAX(i.criado_em) < NOW() - (:days::int || ' days')::interval
                ORDER BY days_idle DESC
                LIMIT 50
            """), {"uid": user_id, "days": days_idle}).fetchall()

        return [
            {
                "lead_id": r[0],
                "nome": r[1] or "",
                "telefone": r[2] or "",
                "segmento": r[3] or "",
                "sdr_stage": r[4] or "",
                "last_interaction": r[5].isoformat() if r[5] else "",
                "days_idle": int(r[6] or 0),
                "last_lead_msg": r[7] or "",
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[find_abandoned_leads] falhou: {e}")
        return []


def generate_reengagement_message(lead: dict) -> str:
    """Gera mensagem de re-engajamento personalizada.

    NUNCA usa template fixo. Personaliza baseado em:
    - Nome do lead
    - Segmento
    - Tempo parado
    - Ultima msg do lead
    """
    nome = lead.get("nome", "").split()[0] if lead.get("nome") else "amigo"
    segmento = lead.get("segmento", "")
    days = lead.get("days_idle", 7)
    last_msg = lead.get("last_lead_msg", "")

    if days >= 30:
        abertura = f"{nome}, tudo bem? Faz um tempo que a gente conversou."
    elif days >= 14:
        abertura = f"{nome}, e ai? Sumiu!"
    else:
        abertura = f"{nome}, tudo bem?"

    if "atleta" in last_msg.lower() or "esporte" in last_msg.lower():
        contexto = "Vi que você mencionou sobre atletas antes, será que ainda é seu foco?"
    elif "preço" in last_msg.lower() or "valor" in last_msg.lower() or "custo" in last_msg.lower():
        contexto = "Tinha perguntado sobre valores. Conseguiu avaliar?"
    elif "horário" in last_msg.lower() or "horario" in last_msg.lower():
        contexto = "Sobre os horários que conversamos, mudou alguma coisa?"
    else:
        contexto = f"Deixa eu te fazer uma pergunta rápida sobre {segmento}?"

    return f"{abertura} {contexto} Posso te ajudar com algo hoje?"


def should_reengange(days_idle: int) -> bool:
    """Decide se vale re-engajar (evita spam)."""
    # 7+ dias = re-engajar
    # 3-7 dias = ainda ta fresco, nao
    # 30+ dias = frio, evita
    return 7 <= days_idle <= 30


# ════════════════════════════════════════════════════════════════════
# EXPORTAR METRICAS (pra mostrar no superadmin)
# ════════════════════════════════════════════════════════════════════

def get_variant_report(user_id: int) -> dict:
    """Retorna relatorio de variants pra dashboard."""
    metrics = _load_variant_metrics(user_id)
    report = {
        "variants": [],
        "best_variant": None,
        "total_sent": 0,
        "total_conversions": 0,
    }

    best_rate = 0
    for v in sorted(metrics.values(), key=lambda m: -m.conversion_rate):
        v_data = {
            "variant": v.variant,
            "sent": v.sent,
            "responses": v.responses,
            "conversions": v.conversions,
            "opt_outs": v.opt_outs,
            "response_rate": round(v.response_rate * 100, 1),
            "conversion_rate": round(v.conversion_rate * 100, 1),
        }
        report["variants"].append(v_data)
        report["total_sent"] += v.sent
        report["total_conversions"] += v.conversions
        if v.conversion_rate > best_rate and v.conversions > 0:
            best_rate = v.conversion_rate
            report["best_variant"] = v.variant

    report["total_conversion_rate"] = round(
        report["total_conversions"] / max(1, report["total_sent"]) * 100, 1
    )
    return report