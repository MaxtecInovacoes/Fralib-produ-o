"""Retargeting de leads frios - re-engaja leads lost/opt_out com cadencia 30/60/90/120d.

Job diario (cron 9h BRT):
- Procura leads com sdr_stage in ('lost', 'opt_out') + last_interaction > 30d
- Envia msg com angulo diferente conforme dias passados
- 30d: pergunta simples
- 60d: caso de sucesso
- 90d: oferta especial
- 120d: archive (nao contata mais)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

log = logging.getLogger("retargeting")


@dataclass(frozen=True)
class RetargetDecision:
    cadence_days: int  # 30, 60, 90, 120
    angle: str  # "check_in", "case_study", "special_offer", "archive"
    message_template: str
    next_run_at: Optional[datetime]


RETARGET_TEMPLATES = {
    "check_in": (
        "Oi {nome}, tudo certo?\n"
        "Passando pra avisar que preparei o exemplo do site pro {segmento}.\n"
        "Se quiser dar uma olhada: {link_site}\n"
        "Sem compromisso, só curiosidade."
    ),
    "case_study": (
        "Oi {nome}, lembra da gente?\n"
        "Um cliente do {segmento} na sua regiao triplicou os contatos em 60 dias.\n"
        "Posso te mandar o exemplo? {link_site}"
    ),
    "special_offer": (
        "Oi {nome}, oferta especial essa semana pra voce:\n"
        "Site premium pro {segmento} com condicao especial.\n"
        "Quer ver? {link_site}"
    ),
    "archive": "",  # nao envia msg
}


def decide_retarget(
    *,
    days_since_last: int,
    stage: str,
    opt_out_count: int = 0,
    won_before: bool = False,
) -> RetargetDecision:
    """Decide se e quando retargetar lead frio."""
    # Won antes: NAO retargetar (ja e cliente)
    if won_before:
        return RetargetDecision(0, "archive", "", None)

    # Opt-out explicito: respeitar
    if stage == "opt_out" and opt_out_count > 0:
        return RetargetDecision(0, "archive", "", None)

    # Cadencia progressiva
    if 30 <= days_since_last < 60:
        return RetargetDecision(
            30, "check_in",
            RETARGET_TEMPLATES["check_in"],
            None,
        )
    if 60 <= days_since_last < 90:
        return RetargetDecision(
            60, "case_study",
            RETARGET_TEMPLATES["case_study"],
            None,
        )
    if 90 <= days_since_last < 120:
        return RetargetDecision(
            90, "special_offer",
            RETARGET_TEMPLATES["special_offer"],
            None,
        )
    if days_since_last >= 120:
        return RetargetDecision(120, "archive", "", None)

    # < 30 dias: nao retargetar ainda
    return RetargetDecision(0, "archive", "", None)


def run_retargeting(
    db_engine,
    *,
    apply: bool = False,
    send_callback=None,
) -> dict[str, int]:
    """Job diario: processa leads com cadencia de retargeting.

    Args:
        db_engine: SQLAlchemy engine
        apply: se True, executa UPDATE e envia msgs; se False, dry-run
        send_callback: funcao async/wrapper que envia msg no WhatsApp
    Returns:
        Stats {matched, queued_30, queued_60, queued_90, archived, sent}
    """
    from sqlalchemy import text

    stats = {
        "matched": 0,
        "queued_30": 0,
        "queued_60": 0,
        "queued_90": 0,
        "archived": 0,
        "sent": 0,
    }
    try:
        with db_engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, user_id, telefone, nome_contato, segmento,
                       sdr_stage, deal_status,
                       EXTRACT(DAY FROM NOW() - COALESCE(last_interaction_at, created_at))::int AS days_since
                FROM leads
                WHERE sdr_stage IN ('lost', 'opt_out')
                  AND deal_status NOT IN ('won')
                  AND EXTRACT(DAY FROM NOW() - COALESCE(last_interaction_at, created_at)) >= 30
                ORDER BY days_since DESC
                LIMIT 200
            """)).fetchall()
        stats["matched"] = len(rows)
        for r in rows:
            lead_id, user_id, telefone, nome, segmento, stage, deal_status, days_since = r
            decision = decide_retarget(
                days_since_last=days_since,
                stage=stage,
                won_before=(deal_status == "won"),
            )
            if decision.angle == "check_in":
                stats["queued_30"] += 1
            elif decision.angle == "case_study":
                stats["queued_60"] += 1
            elif decision.angle == "special_offer":
                stats["queued_90"] += 1
            else:
                stats["archived"] += 1
                continue
            if apply and send_callback:
                # Personaliza template
                msg = decision.message_template.format(
                    nome=(nome or "tudo bem").split()[0] if nome else "tudo bem",
                    segmento=segmento or "seu negocio",
                    link_site=f"https://fralib.app/p/{lead_id}",
                )
                try:
                    send_callback(telefone, msg)
                    stats["sent"] += 1
                    log.info(f"[RETARGET] Lead {lead_id}: {decision.angle} ({days_since}d) -> {telefone}")
                except Exception as e:
                    log.error(f"[RETARGET] Falha ao enviar para {telefone}: {e}")
        if apply and hasattr(db_engine, "commit"):
            db_engine.commit()
    except Exception as e:
        log.error(f"[RETARGET] Erro no job: {e}")
    return stats
