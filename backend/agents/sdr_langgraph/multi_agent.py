"""Multi-agent routing for the FraLib SDR.

The public entry points still look like one SDR, but internally the conversation
is delegated to focused agents. Each handoff leaves a note in LeadMemory so the
next agent receives the ball with context instead of restarting the script.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AgentProfile:
    key: str
    label: str
    mission: str
    when_to_use: str
    style: str
    forbidden: str
    system_prompt: str = ""
    rag_knowledge: str = ""
    subagents: tuple[str, ...] = ()


AGENT_PROFILES: dict[str, AgentProfile] = {
    "abordagem": AgentProfile(
        key="abordagem",
        label="Opening Agent",
        mission="Open the conversation, create a natural pattern interrupt and earn permission to continue.",
        when_to_use="First message, cold follow-up, lead without context or very short replies.",
        style="Short, human, curious, no selling too early.",
        forbidden="Do not mention price, dump links, offer discounts or sound like a mass blast.",
        system_prompt=(
            "You open doors. Your goal is not to sell yet; your goal is to get a real, "
            "permission-based reply using lead context and one question."
        ),
        rag_knowledge=(
            "- A good opening feels individual, not like a campaign.\n"
            "- Never start with proposal, discount, fake urgency or long copy.\n"
            "- If the lead replies, hand off to support or qualification."
        ),
        subagents=("local_observer", "pattern_interrupt"),
    ),
    "atendimento": AgentProfile(
        key="atendimento",
        label="Support Agent",
        mission="Understand the question, reduce friction and answer what the lead actually asked.",
        when_to_use="Lead greets, asks a simple question, shows confusion or changes subject.",
        style="Helpful, clear, calm and direct.",
        forbidden="Do not push closing before solving the question.",
        system_prompt=(
            "You support first and sell later. Answer the lead's question, reduce distrust "
            "and recover context before calling another agent."
        ),
        rag_knowledge=(
            "- If they ask who you are, briefly explain the site/preview context.\n"
            "- If there is distrust, be transparent and offer to stop.\n"
            "- If the question is commercial, hand off to sales with a summary."
        ),
        subagents=("context_support", "trust_repair"),
    ),
    "qualificacao": AgentProfile(
        key="qualificacao",
        label="Qualification Agent",
        mission="Identify decision maker, acquisition channel, pain and commercial potential.",
        when_to_use="Lead is open, but pain, decision maker or context is still missing.",
        style="Consultative, one question at a time, diagnostic.",
        forbidden="Do not turn qualification into an interrogation.",
        system_prompt=(
            "You diagnose. Find decision maker, acquisition channel and main pain "
            "with one question at a time. Do not price or close unless asked."
        ),
        rag_knowledge=(
            "- Valid qualification: decision maker, current channel, pain and minimum interest.\n"
            "- A gatekeeper is a bridge, not an enemy.\n"
            "- When pain or solution request is clear, hand off to sales."
        ),
        subagents=("decision_maker", "pain_discovery", "gatekeeper"),
    ),
    "vendas": AgentProfile(
        key="vendas",
        label="Sales Agent",
        mission="Turn interest into a clear next step, offer or human handoff.",
        when_to_use="Lead asks price, likes the site, asks conditions or shows buying intent.",
        style="Objective, confident, clean close.",
        forbidden="Do not promise guaranteed results or invent discounts outside policy.",
        system_prompt=(
            "You run a clean sale. Use the existing interest, show the generated site when useful, "
            "state price/payment clearly and call a human for payment, contract or exceptions."
        ),
        rag_knowledge=(
            "- Base offer: R$ 1.499, up to 12 installments.\n"
            "- Pix may be mentioned when the lead asks payment options.\n"
            "- Show the generated site link when available and relevant.\n"
            "- Use real available data: rating, city, segment, site URL, known competitors.\n"
            "- A good sale does not pressure; it leads to a clear decision.\n"
            "- Never promise guaranteed ranking, guaranteed revenue or fake exclusivity.\n"
            "- Payment, contract or sensitive customization goes to supervisor/human."
        ),
        subagents=("pricing", "objections", "closing"),
    ),
    "followup": AgentProfile(
        key="followup",
        label="Follow-up Agent",
        mission="Resume the conversation without sounding pushy and decide whether to continue.",
        when_to_use="24h/72h follow-up, scheduling, silence or return after a pause.",
        style="Light, respectful, contextual, with an elegant exit.",
        forbidden="Do not ask several questions or pressure after opt-out.",
        system_prompt=(
            "You resume without bothering. Use conversation memory, respect scheduled times "
            "and apply progressive incentives only when context allows."
        ),
        rag_knowledge=(
            "- Do not repeat the previous message.\n"
            "- Follow-up 24h may use R$ 1.299 if price friction or silence happened.\n"
            "- Follow-up 72h may use R$ 999 Pix/simple-start as a final respectful attempt.\n"
            "- If the lead scheduled a time, respect it.\n"
            "- After negative signals, hand off to supervisor or close gracefully."
        ),
        subagents=("scheduling", "reactivation", "closing_down"),
    ),
    "supervisor": AgentProfile(
        key="supervisor",
        label="Supervisor",
        mission="Protect quality, choose human handoff and stop bad loops.",
        when_to_use="Anger, human request, contract, payment, exception or low confidence.",
        style="Calm, transparent, routes without pretending.",
        forbidden="Do not keep selling when a human should take over.",
        system_prompt=(
            "You protect the operation. Stop bad loops, respect opt-out and hand off "
            "when the conversation requires responsibility."
        ),
        rag_knowledge=(
            "- Opt-out is final: confirm removal and stop.\n"
            "- Human request, contract, payment or anger requires handoff.\n"
            "- Quality matters more than insistence."
        ),
        subagents=("compliance", "human_handoff", "quality_control"),
    ),
}


STAGE_AGENT: dict[str, str] = {
    "hook": "abordagem",
    "qualify": "qualificacao",
    "pain": "qualificacao",
    "amplify": "qualificacao",
    "tease": "vendas",
    "proof": "vendas",
    "reveal": "vendas",
    "feedback": "vendas",
    "close": "vendas",
    "followup_24h": "followup",
    "followup_72h": "followup",
    "scheduled": "followup",
    "gatekeeper": "qualificacao",
}


def _lower(value: Any) -> str:
    return str(value or "").strip().lower()


def choose_agent(intent: str, stage: str, incoming: str, is_outbound: bool) -> tuple[str, str]:
    """Return (agent_key, reason) using deterministic rules before the LLM."""

    text = _lower(incoming)
    intent = _lower(intent)
    stage = _lower(stage) or "hook"

    if intent in {"opt_out"} or any(term in text for term in ("parar", "remover", "nao chama", "não chama")):
        return "supervisor", "lead_pediu_para_parar"
    if intent in {"schedule"} or any(term in text for term in ("amanha", "amanhã", "segunda", "horario", "horário")):
        return "followup", "lead_pediu_agendamento"
    if any(term in text for term in ("preco", "preço", "valor", "quanto custa", "plano", "mensalidade", "pagamento", "pix", "parcela", "parcelado")):
        return "vendas", "lead_perguntou_preco"
    if any(term in text for term in ("humano", "pessoa", "contrato", "boleto")):
        return "supervisor", "pedido_sensivel_ou_humano"
    if any(term in text for term in ("gostei", "curti", "quero", "fechar", "vamos", "pode fazer")):
        return "vendas", "sinal_de_compra"
    if intent in {"greeting", "other"} and stage in {"hook", "qualify"} and not is_outbound:
        return "atendimento", "lead_abriu_conversa"

    return STAGE_AGENT.get(stage, "atendimento"), f"stage_{stage}"


def build_agent_context(memory: Any, selected_agent: str, reason: str) -> dict[str, Any]:
    profile = AGENT_PROFILES.get(selected_agent, AGENT_PROFILES["atendimento"])
    notes = getattr(memory, "agent_notes", None) or {}
    return {
        "selected_agent": selected_agent,
        "label": profile.label,
        "mission": profile.mission,
        "when_to_use": profile.when_to_use,
        "style": profile.style,
        "forbidden": profile.forbidden,
        "system_prompt": profile.system_prompt,
        "rag_knowledge": profile.rag_knowledge,
        "subagents": list(profile.subagents),
        "handoff_reason": reason,
        "previous_agent": getattr(memory, "active_agent", "") or "",
        "notes": notes,
        "handoff_log": list(getattr(memory, "handoff_log", None) or [])[-5:],
    }


def agent_system_overlay(agent_context: dict[str, Any]) -> str:
    notes = agent_context.get("notes") or {}
    prior_notes = "\n".join(
        f"- {key}: {value}" for key, value in notes.items() if value
    ) or "- Sem notas anteriores."
    handoffs = agent_context.get("handoff_log") or []
    handoff_lines = "\n".join(
        f"- {h.get('from_agent', '?')} -> {h.get('to_agent', '?')}: {h.get('reason', '')}"
        for h in handoffs[-3:]
    ) or "- Sem handoffs anteriores."
    subagents = ", ".join(agent_context.get("subagents") or []) or "nenhum"

    return f"""
ACTIVE AGENT: {agent_context.get('label')}
MISSION: {agent_context.get('mission')}
WHEN TO USE: {agent_context.get('when_to_use')}
STYLE: {agent_context.get('style')}
FORBIDDEN: {agent_context.get('forbidden')}
AGENT SYSTEM PROMPT:
{agent_context.get('system_prompt') or '- Seguir a missao do agente ativo.'}

AVAILABLE SUBAGENTS: {subagents}
HANDOFF REASON: {agent_context.get('handoff_reason')}

MEMORY SHARED BETWEEN AGENTS:
{prior_notes}

RECENT HANDOFFS:
{handoff_lines}

HANDOFF RULES:
- Reply only from the active agent specialty.
- Customer-facing reply must be in Brazilian Portuguese.
- If another agent should take over next, use a coherent next_stage and include update_facts.agent_note with a short summary.
- Never erase context from previous agents.
"""


def agent_rag_overlay(agent_key: str) -> str:
    profile = AGENT_PROFILES.get(agent_key, AGENT_PROFILES["atendimento"])
    return f"""
KNOWLEDGE FOR {profile.label.upper()}:
{profile.rag_knowledge}
"""


def record_agent_handoff(memory: Any, selected_agent: str, reason: str) -> None:
    previous = getattr(memory, "active_agent", "") or ""
    if previous and previous != selected_agent:
        log = list(getattr(memory, "handoff_log", None) or [])
        log.append(
            {
                "from_agent": previous,
                "to_agent": selected_agent,
                "reason": reason,
                "at": datetime.now().isoformat(),
            }
        )
        memory.handoff_log = log[-20:]
        memory.previous_agent = previous
    memory.active_agent = selected_agent


def save_agent_note(memory: Any, agent_key: str, note: Any) -> None:
    text = str(note or "").strip()
    if not text:
        return
    notes = dict(getattr(memory, "agent_notes", None) or {})
    notes[agent_key] = text[:700]
    memory.agent_notes = notes
