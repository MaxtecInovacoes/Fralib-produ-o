"""
SDR State - Estrutura tipada do estado do agente.
Cada chamada de grafo recebe um state, modifica, e retorna.
"""

from __future__ import annotations
from typing import TypedDict, List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════════════════════
# STAGE ENUM - Estágios válidos do funil
# ════════════════════════════════════════════════════════════════════

class StageEnum(str, Enum):
    HOOK = "hook"               # Primeira abordagem
    QUALIFY = "qualify"         # Confirmar decisor + canal
    PAIN = "pain"               # Descobrir problema
    AMPLIFY = "amplify"         # Amplificar dor
    TEASE = "tease"             # Plantar semente
    PROOF = "proof"             # Prova social
    REVEAL = "reveal"           # Mostrar site
    FEEDBACK = "feedback"       # Opinião sobre site
    CLOSE = "close"             # Fechar venda
    WON = "won"                 # Ganho
    LOST = "lost"               # Perdido
    OPT_OUT = "opt_out"         # Pediu pra parar
    SCHEDULED = "scheduled"     # Agendado para outro dia
    HANDOFF = "handoff"         # Humano assumiu
    FOLLOWUP_24H = "followup_24h"
    FOLLOWUP_72H = "followup_72h"
    REJECTION = "rejection"


# Transições válidas (grafos podem validar isso)
VALID_TRANSITIONS: Dict[str, List[str]] = {
    "hook": ["qualify", "gatekeeper", "opt_out", "lost"],
    "qualify": ["pain", "gatekeeper", "opt_out", "lost", "scheduled"],
    "pain": ["amplify", "qualify", "opt_out", "lost"],
    "amplify": ["tease", "pain", "opt_out", "lost"],
    "tease": ["proof", "opt_out", "lost"],
    "proof": ["reveal", "tease", "opt_out", "lost"],
    "reveal": ["feedback", "lost", "close"],
    "feedback": ["close", "proof", "lost"],
    "close": ["won", "urgency", "lost", "scheduled"],
    "followup_24h": ["qualify", "lost", "opt_out"],
    "followup_72h": ["lost", "opt_out"],
    "scheduled": ["qualify", "lost", "opt_out"],
    "rejection": ["lost"],
}


# ════════════════════════════════════════════════════════════════════
# LEAD MEMORY - Estado persistente do lead (multi-tenant)
# ════════════════════════════════════════════════════════════════════

class LeadMemory(BaseModel):
    """Memória estruturada do lead - substitui dict livre"""

    # Identificação
    lead_id: str
    user_id: int
    telefone: str
    nome: str = ""
    nome_contato: str = ""  # Nome da pessoa (não do negócio)
    cidade: str = ""
    segmento: str = ""
    rating: float = 0.0
    site_url: str = ""

    # Estado do funil
    stage: str = "hook"
    rejection_count: int = 0
    price_tier: int = 0  # 0=âncora, 1=1499, 2=999, 3=549, 4=pix
    gatekeeper_level: int = 0
    is_decisor: Optional[bool] = None

    # Estado de conversa (FSM nova - baseado em Intent + State, nao stage linear)
    conversation_state: str = "idle"  # ConversationState enum como string
    turn_count: int = 0               # quantas mensagens o lead mandou ate agora
    last_lead_response_at: Optional[str] = None  # timestamp ISO da ultima msg do lead
    last_intent: str = ""             # intent classificado da ultima msg
    last_intent_confidence: float = 0.0
    site_offer_count: int = 0        # quantas vezes o Franz ofereceu o site (max 2)

    # Variante A/B
    variant: str = "A"  # A, B, C, D

    # Estado de conversa
    last_message_sent: str = ""
    last_message_received: str = ""
    last_interaction_at: Optional[str] = None
    attempts: int = 0
    followup_count: int = 0
    followup_date: str = ""

    # Status
    deal_status: str = ""  # opt_out, won, lost
    is_human_takeover: bool = False

    # Opt-out pendente (2-step: Franz pergunta, lead confirma)
    opt_out_pending: bool = False  # True quando Franz perguntou se quer sair
    opt_out_pending_at: Optional[str] = None  # timestamp da pergunta

    # Discovery
    pain_identified: str = ""
    amplify_done: bool = False
    site_revealed: bool = False
    order_bump_offered: bool = False

    # Multiagente SDR
    active_agent: str = "abordagem"
    previous_agent: str = ""
    agent_notes: Dict[str, Any] = Field(default_factory=dict)
    handoff_log: List[Dict[str, Any]] = Field(default_factory=list)

    # Concorrentes (opcional)
    top_concorrentes: List[str] = Field(default_factory=list)
    main_objection: str = ""

    # BANT/MEDDIC estruturado (Fase 3)
    bant_budget: str = ""        # "nao_quero_dizer", "menos_500", "500_1500", "1500_5000", "mais_5000"
    bant_authority: str = ""     # "decisor", "influencia", "consulta", "nao_sei"
    bant_need_score: int = 0     # 0-10
    bant_timeline: str = ""      # "urgente", "30_dias", "90_dias", "sem_previsao"
    meddic_metrics: str = ""     # O lead quer atingir qual métrica?
    meddic_economic_buyer: str = ""  # Quem paga?
    meddic_champion: str = ""    # Quem apoia internamente?
    meddic_score: int = 0        # Score MEDDIC agregado 0-10

    # Humanização (Fase 1)
    humanization_profile: Dict[str, Any] = Field(default_factory=dict)
    # ^ Ex: {"avg_response_time_min": 12, "msg_length_pref": "short", "emoji_tolerance": "low"}
    lead_temperature: str = ""   # "frio", "morno", "quente" - inferido pelo bot
    wall_street_close_used: bool = False
    last_msg_sent_hash: str = ""  # Dedup anti-repetição
    msgs_sent_count: int = 0

    def update_stage(self, new_stage: str) -> bool:
        """Atualiza stage se transição for válida. Retorna True se mudou."""
        if new_stage == self.stage:
            return False
        allowed = VALID_TRANSITIONS.get(self.stage, []) + [self.stage]
        if new_stage in allowed or new_stage in [s.value for s in StageEnum]:
            self.stage = new_stage
            return True
        return False

    def mark_opt_out(self) -> None:
        self.stage = StageEnum.OPT_OUT.value
        self.deal_status = "opt_out"
        self.opt_out_pending = False  # Confirmado, nao esta mais pending

    def request_opt_out_confirmation(self) -> None:
        """Marca que Franz perguntou se lead quer parar. NAO muda stage ainda.
        Lead precisa responder 'sim' pra confirmar.
        """
        self.opt_out_pending = True
        from datetime import datetime
        self.opt_out_pending_at = datetime.now().isoformat()

    def confirm_opt_out_from_pending(self) -> bool:
        """Lead respondeu 'sim' a pergunta de opt_out. Marca opt_out.
        Returns True se confirmou agora, False se nao estava pending.
        """
        if not self.opt_out_pending:
            return False
        self.mark_opt_out()
        return True

    def cancel_opt_out_pending(self) -> None:
        """Lead respondeu 'nao' ou mudou de ideia. Cancela opt_out pendente."""
        self.opt_out_pending = False
        self.opt_out_pending_at = None

    def mark_lost(self) -> None:
        self.stage = StageEnum.LOST.value
        self.deal_status = "lost"

    def mark_won(self) -> None:
        self.stage = StageEnum.WON.value
        self.deal_status = "won"

    def increment_followup(self) -> int:
        self.followup_count += 1
        return self.followup_count

    def can_send_followup(self) -> bool:
        """Verifica se pode enviar follow-up (máx 2)"""
        return self.followup_count < 2


# ════════════════════════════════════════════════════════════════════
# SDR STATE - Estado do grafo (transitório por chamada)
# ════════════════════════════════════════════════════════════════════

class SDRState(TypedDict, total=False):
    """Estado do grafo SDR - modificado por cada node"""

    # Identificação
    user_id: int
    lead_id: Optional[str]
    telefone: str

    # Mensagens
    incoming_message: str  # Mensagem do lead (ou vazia se outbound)
    outgoing_message: str  # Mensagem para enviar (setada pelo stage node)
    is_outbound: bool  # True se é mensagem que o agente envia (intro/followup)

    # Memória do lead (carregada do storage)
    memory: LeadMemory

    # Contexto para o LLM
    nome: str
    cidade: str
    segmento: str
    rating: float
    site_url: str
    sdr_stage: str

    # Detecção de intent (calculada no início)
    detected_intent: str
    detected_emotion: str
    intent_confidence: float

    # RAG (carregado uma vez por chamada)
    rag_context: str

    # Stage atual (depois do routing)
    current_stage: str
    next_stage: str

    # Controle
    should_send: bool
    should_handoff: bool
    guard_reason: str

    # Histórico
    history: List[Dict[str, str]]  # [{"role": "user/assistant", "content": "..."}]

    # Métricas
    variant: str  # A/B/C/D
    persona: str  # "consultivo" | "lobo" | "auto"
    selected_agent: str
    previous_agent: str
    agent_context: Dict[str, Any]
    agent_handoff_reason: str
    error: str
    latency_ms: int
