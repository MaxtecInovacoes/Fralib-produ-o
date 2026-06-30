"""
Agent Profiles - Define agent behaviors, missions, and constraints
"""

from typing import Dict, List, Optional
from .state import AgentType, AgentState


class AgentProfile:
    """Profile definition for each agent type"""

    def __init__(
        self,
        key: str,
        label: str,
        mission: str,
        when_to_use: str,
        style: str,
        forbidden: str,
        system_prompt: str = "",
        rag_knowledge: str = "",
        subagents: List[str] = None,
        max_attempts: int = 3,
        timeout_seconds: int = 30
    ):
        self.key = key
        self.label = label
        self.mission = mission
        self.when_to_use = when_to_use
        self.style = style
        self.forbidden = forbidden
        self.system_prompt = system_prompt
        self.rag_knowledge = rag_knowledge
        self.subagents = subagents or []
        self.max_attempts = max_attempts
        self.timeout_seconds = timeout_seconds


# Agent profiles with detailed specifications
AGENT_PROFILES: Dict[AgentType, AgentProfile] = {
    AgentType.ABORDAGEM: AgentProfile(
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
        subagents=["local_observer", "pattern_interrupt"],
        max_attempts=2,
        timeout_seconds=20
    ),

    AgentType.ATENDIMENTO: AgentProfile(
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
        subagents=["context_support", "trust_repair"],
        max_attempts=3,
        timeout_seconds=25
    ),

    AgentType.QUALIFICACAO: AgentProfile(
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
        subagents=["decision_maker", "pain_discovery", "gatekeeper"],
        max_attempts=3,
        timeout_seconds=30
    ),

    AgentType.VENDAS: AgentProfile(
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
        subagents=["pricing", "objections", "closing"],
        max_attempts=2,
        timeout_seconds=35
    ),

    AgentType.FOLLOWUP: AgentProfile(
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
        subagents=["scheduling", "reactivation", "closing_down"],
        max_attempts=2,
        timeout_seconds=25
    ),

    AgentType.SUPERVISOR: AgentProfile(
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
        subagents=["compliance", "human_handoff", "quality_control"],
        max_attempts=1,
        timeout_seconds=15
    )
}


# Stage to agent mapping for deterministic routing
STAGE_AGENT_MAPPING: Dict[str, AgentType] = {
    "hook": AgentType.ABORDAGEM,
    "qualify": AgentType.QUALIFICACAO,
    "pain": AgentType.QUALIFICACAO,
    "amplify": AgentType.QUALIFICACAO,
    "tease": AgentType.VENDAS,
    "proof": AgentType.VENDAS,
    "reveal": AgentType.VENDAS,
    "feedback": AgentType.VENDAS,
    "close": AgentType.VENDAS,
    "followup_24h": AgentType.FOLLOWUP,
    "followup_72h": AgentType.FOLLOWUP,
    "scheduled": AgentType.FOLLOWUP,
    "gatekeeper": AgentType.QUALIFICACAO,
}


def get_agent_profile(agent_type: AgentType) -> AgentProfile:
    """Get profile for agent type"""
    return AGENT_PROFILES.get(agent_type, AGENT_PROFILES[AgentType.ATENDIMENTO])


def get_stage_agent(stage: str) -> AgentType:
    """Get agent for conversation stage"""
    return STAGE_AGENT_MAPPING.get(stage, AgentType.ATENDIMENTO)


def build_agent_context(state: AgentState) -> Dict[str, any]:
    """Build agent context from state"""
    profile = get_agent_profile(state["current_agent"])

    return {
        "selected_agent": state["current_agent"].value,
        "label": profile.label,
        "mission": profile.mission,
        "when_to_use": profile.when_to_use,
        "style": profile.style,
        "forbidden": profile.forbidden,
        "system_prompt": profile.system_prompt,
        "rag_knowledge": profile.rag_knowledge,
        "subagents": profile.subagents,
        "max_attempts": profile.max_attempts,
        "timeout_seconds": profile.timeout_seconds,
        "handoff_reason": state.get("handoff_reason", ""),
        "previous_agent": state.get("previous_agent", ""),
        "notes": state.get("agent_notes", {}),
        "handoff_log": state.get("handoff_log", [])[-5:],
        "lead_context": state["lead_facts"],
        "conversation_history": [msg.content for msg in state["messages"][-5:]],
    }


def generate_agent_prompt(context: Dict[str, any]) -> str:
    """Generate system prompt for agent"""
    profile = get_agent_profile(context["selected_agent"])

    prompt = f"""
ACTIVE AGENT: {context['label']}
MISSION: {context['mission']}
WHEN TO USE: {context['when_to_use']}
STYLE: {context['style']}
FORBIDDEN: {context['forbidden']}

SYSTEM PROMPT:
{profile.system_prompt}

KNOWLEDGE:
{profile.rag_knowledge}

AVAILABLE SUBAGENTS: {', '.join(profile.subagents)}
MAX ATTEMPTS: {profile.max_attempts}
TIMEOUT: {profile.timeout_seconds}s

HANDOFF REASON: {context['handoff_reason']}

LEAD CONTEXT:
{context['lead_context']}

RECENT CONVERSATION:
{chr(10).join(context['conversation_history'])}

MEMORY NOTES:
{chr(10).join(f"- {k}: {v}" for k, v in context['notes'].items() if v)}

RECENT HANDOFFS:
{chr(10).join(f"- {h.get('from_agent', '?')} -> {h.get('to_agent', '?')}: {h.get('reason', '')}" for h in context['handoff_log'][-3:])}

RESPONSE GUIDELINES:
- Reply only from the active agent specialty
- Customer-facing reply must be in Brazilian Portuguese
- If another agent should take over next, indicate clearly
- Never erase context from previous agents
- Keep responses concise and focused
"""

    return prompt.strip()