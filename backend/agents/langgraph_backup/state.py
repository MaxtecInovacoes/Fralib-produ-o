"""
LangGraph Agent State - Centralized state management for conversation flow
"""

from typing import Annotated, Dict, List, Optional, TypedDict
from langgraph.graph.message import AnyMessage, add_messages
from datetime import datetime
from enum import Enum


class AgentType(str, Enum):
    """Agent types with their purposes"""
    ABORDAGEM = "abordagem"
    ATENDIMENTO = "atendimento"
    QUALIFICACAO = "qualificacao"
    VENDAS = "vendas"
    FOLLOWUP = "followup"
    SUPERVISOR = "supervisor"


class ConversationStage(str, Enum):
    """Conversation stages for state transitions"""
    HOOK = "hook"
    QUALIFY = "qualify"
    PAIN = "pain"
    AMPLIFY = "amplify"
    TEASE = "tease"
    PROOF = "proof"
    REVEAL = "reveal"
    FEEDBACK = "feedback"
    CLOSE = "close"
    FOLLOWUP_24H = "followup_24h"
    FOLLOWUP_72H = "followup_72h"
    SCHEDULED = "scheduled"
    GATEKEEPER = "gatekeeper"


class LeadComplexity(str, Enum):
    """Lead complexity levels"""
    SIMPLE = "simples"
    MEDIUM = "medio"
    COMPLEX = "complexo"


class AgentState(TypedDict):
    """Centralized state for conversation management"""
    # Messages and conversation
    messages: Annotated[List[AnyMessage], add_messages]
    current_agent: AgentType
    conversation_stage: ConversationStage
    is_outbound: bool

    # Lead context
    lead_facts: Dict[str, any]
    nicho: str
    tier: str

    # Agent management
    next_agent: Optional[AgentType]
    handoff_reason: str
    previous_agent: Optional[AgentType]

    # Memory and learning
    memory_entries: List[Dict[str, any]]
    agent_notes: Dict[str, str]
    handoff_log: List[Dict[str, any]]

    # Performance tracking
    attempt_count: int
    last_error: Optional[str]
    confidence_score: float

    # Metadata
    session_id: str
    created_at: str
    updated_at: str


class AgentConfig:
    """Configuration for each agent type"""

    def __init__(self):
        self.nichos_premium = [
            "restaurante", "hotel", "clinica_estetica", "arquitetura",
            "imobiliaria", "clinica_medica", "advocacia", "odontologia",
        ]

        self.routing_table = {
            AgentType.ABORDAGEM: {LeadComplexity.COMPLEX: "sonnet", LeadComplexity.MEDIUM: "sonnet", LeadComplexity.SIMPLE: "sonnet"},
            AgentType.ATENDIMENTO: {LeadComplexity.COMPLEX: "sonnet", LeadComplexity.MEDIUM: "sonnet", LeadComplexity.SIMPLE: "sonnet"},
            AgentType.QUALIFICACAO: {LeadComplexity.COMPLEX: "sonnet", LeadComplexity.MEDIUM: "sonnet", LeadComplexity.SIMPLE: "haiku"},
            AgentType.VENDAS: {LeadComplexity.COMPLEX: "sonnet", LeadComplexity.MEDIUM: "sonnet", LeadComplexity.SIMPLE: "sonnet"},
            AgentType.FOLLOWUP: {LeadComplexity.COMPLEX: "haiku", LeadComplexity.MEDIUM: "haiku", LeadComplexity.SIMPLE: "haiku"},
            AgentType.SUPERVISOR: {LeadComplexity.COMPLEX: "haiku", LeadComplexity.MEDIUM: "haiku", LeadComplexity.SIMPLE: "haiku"},
        }

        self.max_tokens = {
            AgentType.ABORDAGEM: {"complexo": 16000, "medio": 12000, "simples": 8000},
            AgentType.QUALIFICACAO: {"complexo": 6000, "medio": 4000, "simples": 3000},
            AgentType.VENDAS: {"complexo": 8000, "medio": 6000, "simples": 4000},
            AgentType.ATENDIMENTO: {"complexo": 6000, "medio": 4000, "simples": 3000},
            AgentType.FOLLOWUP: {"complexo": 4000, "medio": 3000, "simples": 2000},
            AgentType.SUPERVISOR: {"complexo": 4000, "medio": 3000, "simples": 2000},
        }

        self.temperature = {
            AgentType.ABORDAGEM: 0.7,
            AgentType.ATENDIMENTO: 0.6,
            AgentType.QUALIFICACAO: 0.5,
            AgentType.VENDAS: 0.5,
            AgentType.FOLLOWUP: 0.7,
            AgentType.SUPERVISOR: 0.3,
        }

    def get_model(self, agent: AgentType, complexity: LeadComplexity) -> str:
        """Get model for agent based on complexity"""
        return self.routing_table.get(agent, {}).get(complexity, "sonnet")

    def get_max_tokens(self, agent: AgentType, complexity: LeadComplexity) -> int:
        """Get max tokens for agent based on complexity"""
        complexity_str = complexity.value
        return self.max_tokens.get(agent, {}).get(complexity_str, 4000)

    def get_temperature(self, agent: AgentType) -> float:
        """Get temperature for agent"""
        return self.temperature.get(agent, 0.7)

    def calculate_complexity(self, facts: Dict[str, any]) -> LeadComplexity:
        """Calculate lead complexity based on facts"""
        score = 0

        # Reviews scoring
        qtd_reviews = facts.get("qtd_reviews", 0) or 0
        if qtd_reviews >= 20:
            score += 3
        elif qtd_reviews >= 5:
            score += 1

        # Niche scoring
        nicho = facts.get("nicho") or facts.get("segmento") or ""
        if nicho in self.nichos_premium:
            score += 3

        # Tier scoring
        tier = facts.get("tier") or ""
        if tier == "PREMIUM":
            score += 3
        elif tier == "STANDARD":
            score += 1

        # Site presence
        if facts.get("tem_site"):
            score += 2

        # Services count
        qtd_servicos = len(facts.get("servicos", []) or []) if isinstance(facts.get("servicos"), list) else facts.get("qtd_servicos", 0) or 0
        if qtd_servicos > 8:
            score += 2
        elif qtd_servicos > 4:
            score += 1

        # Determine complexity
        if score >= 7:
            return LeadComplexity.COMPLEX
        elif score >= 3:
            return LeadComplexity.MEDIUM
        return LeadComplexity.SIMPLE


def create_initial_state(lead_facts: Dict[str, any], session_id: str) -> AgentState:
    """Create initial agent state"""
    return AgentState(
        messages=[],
        current_agent=AgentType.ATENDIMENTO.value,  # Convert to string
        conversation_stage=ConversationStage.HOOK,
        is_outbound=True,
        lead_facts=lead_facts,
        nicho=lead_facts.get("nicho", ""),
        tier=lead_facts.get("tier", "STANDARD"),
        next_agent=None,
        handoff_reason="initial_state",
        previous_agent=None,
        memory_entries=[],
        agent_notes={},
        handoff_log=[],
        attempt_count=0,
        last_error=None,
        confidence_score=0.5,
        session_id=session_id,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )