"""
Endpoints de integração entre o novo sistema LangGraph e o SDR/Franz.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime


router = APIRouter(prefix="/franz-bridge", tags=["franz_bridge"])


class SDRMemorySyncRequest(BaseModel):
    """Request para sincronizar memória SDR"""
    session_id: str
    user_id: int
    memory_data: Dict[str, Any]


class SDRMemorySyncResponse(BaseModel):
    """Response da sincronização de memória"""
    success: bool
    memory_context: Dict[str, Any]
    synced_entries: int


class SDRRoutingRequest(BaseModel):
    """Request para obter contexto de routing"""
    session_id: str
    user_id: int
    lead_data: Dict[str, Any]


class SDRRoutingResponse(BaseModel):
    """Response do contexto de routing"""
    recommended_agent: str
    routing_reason: str
    confidence: float
    stage: str
    nicho: str
    memory_context: Dict[str, Any]


class SDRInteractionRequest(BaseModel):
    """Request para registrar interação SDR"""
    session_id: str
    user_id: int
    lead_data: Dict[str, Any]
    user_message: str
    agent_response: str
    stage: str
    success: bool


class SDRInteractionResponse(BaseModel):
    """Response do registro de interação"""
    success: bool
    recorded: bool


class SDRErrorRequest(BaseModel):
    """Request para tratar erro SDR"""
    session_id: str
    state: Dict[str, Any]
    error_message: str


class SDRErrorResponse(BaseModel):
    """Response do tratamento de erro"""
    error_type: str
    severity: str
    recovery_action: str
    should_escalate: bool
    circuit_breaker_state: str


class CloserHandoffRequest(BaseModel):
    """Request para preparar handoff ao closer"""
    session_id: str
    user_id: int
    lead_data: Dict[str, Any]
    history: List[Dict[str, Any]]


class CloserHandoffResponse(BaseModel):
    """Response do contexto de handoff"""
    session_id: str
    user_id: int
    lead_nome: str
    lead_telefone: str
    stage: str
    temperature: str
    bant_score: int
    memory_score: int
    total_score: int
    pain_identified: str
    recommended_action: str
    memory_context: Dict[str, Any]


class IntentDetectionRequest(BaseModel):
    """Request para detectar intent"""
    message: str


class IntentDetectionResponse(BaseModel):
    """Response da detecção de intent"""
    intent: str
    confidence: float
    message: str


class ComplexityRequest(BaseModel):
    """Request para calcular complexidade"""
    lead_data: Dict[str, Any]


class ComplexityResponse(BaseModel):
    """Response da complexidade calculada"""
    complexity: str
    lead_data: Dict[str, Any]


# ════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════════

@router.post("/memory/sync", response_model=SDRMemorySyncResponse)
async def sync_sdr_memory(request: SDRMemorySyncRequest):
    """Sincroniza dados do LeadMemory com o memory system"""
    try:
        from .franz_bridge import sync_memory_to_sdr

        result = sync_memory_to_sdr(
            memory_data=request.memory_data,
            session_id=request.session_id,
            user_id=request.user_id
        )

        return SDRMemorySyncResponse(
            success=True,
            memory_context=result.get("_memory_context", {}),
            synced_entries=result.get("_memory_entries", 0)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/routing", response_model=SDRRoutingResponse)
async def get_sdr_routing(request: SDRRoutingRequest):
    """Obtém contexto de routing para o SDR"""
    try:
        from .franz_bridge import get_sdr_routing_context

        result = get_sdr_routing_context(
            session_id=request.session_id,
            user_id=request.user_id,
            lead_data=request.lead_data
        )

        return SDRRoutingResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interaction", response_model=SDRInteractionResponse)
async def record_sdr_interaction(request: SDRInteractionRequest):
    """Registra uma interação SDR no memory system"""
    try:
        from .franz_bridge import record_sdr_interaction

        record_sdr_interaction(
            session_id=request.session_id,
            user_id=request.user_id,
            lead_data=request.lead_data,
            user_message=request.user_message,
            agent_response=request.agent_response,
            stage=request.stage,
            success=request.success
        )

        return SDRInteractionResponse(success=True, recorded=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/error", response_model=SDRErrorResponse)
async def handle_sdr_error(request: SDRErrorRequest):
    """Trata erro do SDR usando o error handler"""
    try:
        from .franz_bridge import handle_sdr_error

        result = handle_sdr_error(
            error=Exception(request.error_message),
            state=request.state,
            session_id=request.session_id
        )

        return SDRErrorResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/closer-handoff", response_model=CloserHandoffResponse)
async def prepare_closer_handoff(request: CloserHandoffRequest):
    """Prepara contexto para handoff ao closer humano"""
    try:
        from .franz_bridge import prepare_closer_handoff_context

        result = prepare_closer_handoff_context(
            session_id=request.session_id,
            user_id=request.user_id,
            lead_data=request.lead_data,
            history=request.history
        )

        return CloserHandoffResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intent", response_model=IntentDetectionResponse)
async def detect_intent(request: IntentDetectionRequest):
    """Detecta intent de uma mensagem"""
    try:
        from .franz_bridge import get_intent_from_message

        result = get_intent_from_message(request.message)

        return IntentDetectionResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complexity", response_model=ComplexityResponse)
async def calculate_complexity(request: ComplexityRequest):
    """Calcula complexidade do lead"""
    try:
        from .franz_bridge import calculate_lead_complexity_for_sdr

        complexity = calculate_lead_complexity_for_sdr(request.lead_data)

        return ComplexityResponse(
            complexity=complexity,
            lead_data=request.lead_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def franz_bridge_health():
    """Health check do Franz Bridge"""
    try:
        from .langgraph.memory import get_memory_manager
        from .langgraph.error_handler import get_error_handler

        memory_manager = get_memory_manager()
        error_handler = get_error_handler()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "memory_manager": "ready",
                "error_handler": "ready",
                "circuit_breaker": error_handler.circuit_breaker.get_state(),
            },
            "memory_stats": {
                "core_entries": len(memory_manager.core.entries),
                "warm_nichos": len(list(memory_manager.warm.warm_dir.glob("*.json"))),
                "cold_sessions": len(list(memory_manager.cold.cold_dir.glob("*.json"))),
            }
        }

    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/stats")
async def franz_bridge_stats():
    """Estatísticas do Franz Bridge"""
    try:
        from .langgraph.memory import get_memory_manager
        from .langgraph.error_handler import get_error_handler

        memory_manager = get_memory_manager()
        error_handler = get_error_handler()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "memory": {
                "core_entries": len(memory_manager.core.entries),
                "warm_nichos": len(list(memory_manager.warm.warm_dir.glob("*.json"))),
                "cold_sessions": len(list(memory_manager.cold.cold_dir.glob("*.json"))),
            },
            "errors": {
                "total_errors": len(error_handler.error_history),
                "circuit_breaker_state": error_handler.circuit_breaker.get_state(),
                "failure_count": error_handler.circuit_breaker.failure_count,
            },
            "routing": {
                "available_agents": 6,
                "available_intents": 8,
                "supported_nichos": 15,
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))