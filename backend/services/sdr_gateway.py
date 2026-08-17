"""Operational guardrails for the FraLib SDR.

This module is intentionally deterministic. The LLM can compose a message, but
this gateway decides whether the system is allowed to send it.
"""


from dataclasses import dataclass
import re
from typing import Any

from sqlalchemy import text


PRE_REVEAL_STAGES = {
    "",
    "new",
    "pendente_wpp",
    "hook",
    "intro",
    "qualify",
    "pain",
    "amplify",
    "tease",
    "proof",
    "followup1",
    "followup_24h",
    "f1",
}

HUMAN_STOP_STAGES = {
    "qualificados",
    "ganhos",
    "perdidos",
    "handoff",
    "won",
    "lost",
    "opt_out",
}

BLOCKED_STAGES = {
    "blocked_quality_incident",
    "blocked_plan",
    "quality_hold",
    "sdr_blocked",
}

FOLLOWUP_STAGES = {
    "followup1",
    "followup2",
    "followup_24h",
    "followup_72h",
    "f1",
    "f2",
    "scheduled",
}


@dataclass(frozen=True)
class SdrMessageContext:
    tenant_id: int
    lead_id: str | None
    lead_name: str
    lead_segment: str = ""
    stage: str = ""
    next_stage: str = ""
    message: str = ""
    site_url: str = ""
    prior_outbound: bool = False
    direction: str = "outbound"
    plan_allows_sdr: bool = True
    whatsapp_connected: bool = True
    within_schedule: bool = True
    site_ready: bool = True
    human_assumed: bool = False
    opt_out: bool = False


@dataclass(frozen=True)
class SdrGuardDecision:
    allowed: bool
    action: str
    code: str
    reason: str


def _norm(value: Any) -> str:
    return ("" if value is None else str(value)).strip().lower()


def contains_site_reveal(message: str, site_url: str = "") -> bool:
    content = _norm(message)
    url = _norm(site_url)
    return bool(
        re.search(r"https?://|seunegociofralib\.site|fralib\.site|wa\.me/", content)
        or (url and url in content)
        or ("projeto" in content and ("o que achou" in content or "reservado" in content))
    )


def contains_repeat_claim_without_history(message: str) -> bool:
    content = _norm(message)
    repeat_markers = (
        "aqui de novo",
        "de novo por aqui",
        "retomando aqui",
        "como falei",
        "conforme falei",
        "ja te mandei",
        "já te mandei",
    )
    return any(marker in content for marker in repeat_markers)


_SEGMENT_CONTAMINATION_RULES = (
    (
        ("academia", "fitness", "gym", "crossfit", "pilates", "musculacao", "musculação"),
        (
            "delivery",
            "cardapio",
            "cardápio",
            "ifood",
            "pizzaria",
            "pizza",
            "restaurante",
            "reserva de mesa",
            "prato",
            "marmita",
            "lanchonete",
            "pedido online",
            "fazer pedido",
            "entrega",
        ),
    ),
    (
        ("restaurante", "pizzaria", "cafe", "café", "bar", "lanchonete"),
        (
            "matricula",
            "matrícula",
            "musculacao",
            "musculação",
            "personal trainer",
            "treino funcional",
            "alunos novos",
            "equipamentos de treino",
        ),
    ),
)


def contains_segment_contamination(message: str, lead_segment: str = "") -> bool:
    content = _norm(message)
    segment = _norm(lead_segment)
    if not content or not segment:
        return False

    academia_terms = (
        "musculacao",
        "musculação",
        "treino funcional",
        "funcional",
        "personal trainer",
        "alunos novos",
        "matricula",
        "matrícula",
    )
    academia_segment = ("academia", "fitness", "gym", "crossfit", "pilates")
    if not any(marker in segment for marker in academia_segment):
        if any(term in content for term in academia_terms):
            return True

    for segment_markers, forbidden_terms in _SEGMENT_CONTAMINATION_RULES:
        if any(marker in segment for marker in segment_markers):
            return any(term in content for term in forbidden_terms)
    return False


def has_prior_outbound(db_or_conn: Any, lead_id: str | None, tenant_id: int | None) -> bool:
    if not lead_id or not tenant_id:
        return False
    row = db_or_conn.execute(
        text(
            """
            SELECT 1
            FROM interacoes
            WHERE lead_id = :lead_id
              AND user_id = :tenant_id
              AND direcao = 'saida'
            LIMIT 1
            """
        ),
        {"lead_id": lead_id, "tenant_id": tenant_id},
    ).fetchone()
    return bool(row)


def evaluate_sdr_output(ctx: SdrMessageContext) -> SdrGuardDecision:
    stage = _norm(ctx.stage)
    next_stage = _norm(ctx.next_stage)
    message = ctx.message or ""

    if not ctx.plan_allows_sdr:
        return SdrGuardDecision(False, "block", "plan_blocked", "Plano nao permite SDR")
    if not ctx.site_ready:
        return SdrGuardDecision(False, "block", "site_not_ready", "Lead sem site pronto")
    if stage in BLOCKED_STAGES or stage.startswith("blocked_"):
        return SdrGuardDecision(False, "block", "lead_blocked", "Lead bloqueado para SDR")
    if ctx.human_assumed or stage in HUMAN_STOP_STAGES:
        return SdrGuardDecision(False, "handoff", "human_assumed", "Humano assumiu a conversa")
    if ctx.opt_out:
        return SdrGuardDecision(False, "block", "opt_out", "Lead pediu para parar")
    if not ctx.whatsapp_connected:
        return SdrGuardDecision(False, "defer", "whatsapp_disconnected", "WhatsApp desconectado")
    if not ctx.within_schedule:
        return SdrGuardDecision(False, "defer", "outside_schedule", "Fora do horario do SDR")
    if not message.strip():
        return SdrGuardDecision(False, "block", "empty_message", "Mensagem vazia")

    if contains_segment_contamination(message, ctx.lead_segment):
        return SdrGuardDecision(
            False,
            "block",
            "segment_contamination",
            "Mensagem usa termos de outro segmento",
        )

    if ctx.direction == "followup" and not ctx.prior_outbound:
        return SdrGuardDecision(
            False,
            "block",
            "followup_without_history",
            "Follow-up sem mensagem de saida anterior",
        )

    if not ctx.prior_outbound and contains_repeat_claim_without_history(message):
        return SdrGuardDecision(
            False,
            "block",
            "repeat_claim_without_history",
            "Mensagem pressupoe contato anterior sem historico",
        )

    if (
        contains_site_reveal(message, ctx.site_url)
        and not ctx.prior_outbound
        and (stage in PRE_REVEAL_STAGES or next_stage in PRE_REVEAL_STAGES)
    ):
        return SdrGuardDecision(
            False,
            "block",
            "site_reveal_too_early",
            "Link/projeto revelado antes da apresentacao minima",
        )

    return SdrGuardDecision(True, "send", "allowed", "Envio permitido")


def sanitize_cold_followups(db_or_conn: Any, tenant_id: int | None = None, *, apply: bool = False) -> dict[str, int]:
    """Move cold follow-up leads with no outbound history back to the initial queue.

    Dry-run by default. The UPDATE is tenant-aware when tenant_id is provided.
    """

    params: dict[str, Any] = {}
    tenant_sql = ""
    if tenant_id is not None:
        tenant_sql = "AND l.user_id = :tenant_id"
        params["tenant_id"] = tenant_id

    select_sql = text(
        f"""
        SELECT COUNT(*)
        FROM leads l
        WHERE l.sdr_stage IN (
            'hook', 'intro', 'qualify', 'pain', 'amplify', 'tease', 'proof',
            'followup1', 'followup2', 'followup_24h', 'followup_72h', 'f1', 'f2'
        )
          AND l.status = 'concluido'
          AND l.site_url IS NOT NULL
          {tenant_sql}
          AND NOT EXISTS (
              SELECT 1
              FROM interacoes i
              WHERE i.lead_id = l.id
                AND i.user_id = l.user_id
                AND i.direcao = 'saida'
          )
        """
    )
    count = int(db_or_conn.execute(select_sql, params).scalar() or 0)
    if not apply or count <= 0:
        return {"matched": count, "updated": 0}

    update_sql = text(
        f"""
        UPDATE leads l
        SET sdr_stage = 'pendente_wpp',
            atualizado_em = NOW()::text
        WHERE l.sdr_stage IN (
            'hook', 'intro', 'qualify', 'pain', 'amplify', 'tease', 'proof',
            'followup1', 'followup2', 'followup_24h', 'followup_72h', 'f1', 'f2'
        )
          AND l.status = 'concluido'
          AND l.site_url IS NOT NULL
          {tenant_sql}
          AND NOT EXISTS (
              SELECT 1
              FROM interacoes i
              WHERE i.lead_id = l.id
                AND i.user_id = l.user_id
                AND i.direcao = 'saida'
          )
        """
    )
    result = db_or_conn.execute(update_sql, params)
    updated = int(getattr(result, "rowcount", 0) or 0)
    if hasattr(db_or_conn, "commit"):
        db_or_conn.commit()
    return {"matched": count, "updated": updated}
