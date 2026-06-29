"""
FastAPI endpoints for LangGraph agents integration with FraLib
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uuid
import asyncio
from datetime import datetime

from .fralib_integration import integration, FraLibLangGraphIntegration
from .langgraph.state import AgentType
from .langgraph.profiles import get_agent_profile

router = APIRouter()


class LeadFacts(BaseModel):
    """Lead facts model"""
    nicho: str
    cidade: str
    tier: str = "STANDARD"
    qtd_reviews: int = 0
    tem_site: bool = False
    servicos: List[str] = []
    nome_lead: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None


class ConversationRequest(BaseModel):
    """Conversation request model"""
    lead_facts: LeadFacts
    user_message: str
    current_agent: Optional[str] = None
    session_id: Optional[str] = None
    conversation_history: List[Dict[str, str]] = []


class ConversationResponse(BaseModel):
    """Conversation response model"""
    session_id: str
    status: str
    final_agent: str
    response: str
    complexity: str
    agent_config: Dict[str, Any]
    memory_tokens: int
    error: Optional[str] = None
    escalated: bool = False


class AgentInfo(BaseModel):
    """Agent information model"""
    key: str
    label: str
    mission: str
    when_to_use: str
    style: str
    forbidden: str
    system_prompt: str
    rag_knowledge: str
    subagents: List[str]


class ComplexityRequest(BaseModel):
    """Complexity calculation request"""
    lead_facts: LeadFacts


class ComplexityResponse(BaseModel):
    """Complexity calculation response"""
    complexity: str
    score_breakdown: Dict[str, Any]
    recommended_model: str
    max_tokens: int


@router.post("/conversation", response_model=ConversationResponse)
async def process_conversation(request: ConversationRequest):
    """Process conversation through LangGraph agents"""
    try:
        # Convert LeadFacts to dict
        lead_facts_dict = request.lead_facts.dict()

        # Get integration instance
        integration_instance = FraLibLangGraphIntegration()

        # Calculate complexity
        complexity = integration_instance.calculate_lead_complexity(lead_facts_dict)

        # Get agent configuration
        current_agent = AgentType(request.current_agent) if request.current_agent else None
        agent_config = integration_instance.get_agent_model_config(
            current_agent or AgentType.ATENDIMENTO,
            complexity
        )

        # Process conversation
        result = await integration_instance.process_lead_conversation(
            lead_facts=lead_facts_dict,
            conversation_history=request.conversation_history,
            session_id=request.session_id
        )

        # Get memory context
        memory_context = integration_instance.get_memory_context(
            session_id=result.get("session_id", ""),
            agent_type=current_agent or AgentType.ATENDIMENTO,
            nicho=lead_facts_dict["nicho"]
        )

        return ConversationResponse(
            session_id=result.get("session_id", ""),
            status=result.get("status", "unknown"),
            final_agent=result.get("final_agent", "unknown"),
            response=result.get("response", ""),
            complexity=complexity,
            agent_config=agent_config,
            memory_tokens=memory_context.get("total_tokens", 0),
            error=result.get("error"),
            escalated=result.get("escalated", False)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complexity", response_model=ComplexityResponse)
async def calculate_complexity(request: ComplexityRequest):
    """Calculate lead complexity"""
    try:
        integration_instance = FraLibLangGraphIntegration()
        lead_facts_dict = request.lead_facts.dict()

        complexity = integration_instance.calculate_lead_complexity(lead_facts_dict)

        # Get score breakdown
        config = integration_instance.config
        score_breakdown = {
            "reviews": lead_facts_dict.get("qtd_reviews", 0),
            "nicho_premium": 1 if lead_facts_dict.get("nicho") in config.nichos_premium else 0,
            "tier": lead_facts_dict.get("tier", ""),
            "has_site": lead_facts_dict.get("tem_site", False),
            "services_count": len(lead_facts_dict.get("servicos", []))
        }

        # Get recommended model
        agent_config = integration_instance.get_agent_model_config(AgentType.VENDAS, complexity)

        return ComplexityResponse(
            complexity=complexity,
            score_breakdown=score_breakdown,
            recommended_model=agent_config["model"],
            max_tokens=agent_config["max_tokens"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents", response_model=List[AgentInfo])
async def get_agents():
    """Get all available agents"""
    agents_info = []

    for agent_type in AgentType:
        profile = get_agent_profile(agent_type)
        agents_info.append(AgentInfo(
            key=profile.key,
            label=profile.label,
            mission=profile.mission,
            when_to_use=profile.when_to_use,
            style=profile.style,
            forbidden=profile.forbidden,
            system_prompt=profile.system_prompt,
            rag_knowledge=profile.rag_knowledge,
            subagents=profile.subagents
        ))

    return agents_info


@router.get("/session/{session_id}/memory")
async def get_session_memory(session_id: str):
    """Get session memory context"""
    try:
        integration_instance = FraLibLangGraphIntegration()

        # Get memory context for all agents
        memory_data = {}
        for agent_type in AgentType:
            memory_context = integration_instance.get_memory_context(
                session_id=session_id,
                agent_type=agent_type,
                nicho="general"  # You might want to make this configurable
            )
            memory_data[agent_type.value] = memory_context

        return {
            "session_id": session_id,
            "memory_data": memory_data,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/experience")
async def record_experience(
    session_id: str,
    agent: str,
    nicho: str,
    user_message: str,
    agent_response: str,
    success: bool = True
):
    """Record conversation experience"""
    try:
        integration_instance = FraLibLangGraphIntegration()
        agent_type = AgentType(agent)

        integration_instance.record_conversation_experience(
            session_id=session_id,
            agent_type=agent_type,
            nicho=nicho,
            user_message=user_message,
            agent_response=agent_response,
            success=success
        )

        return {"message": "Experience recorded successfully", "session_id": session_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "components": {
            "langgraph": "ready",
            "memory": "ready",
            "routing": "ready"
        }
    }


@router.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        integration_instance = FraLibLangGraphIntegration()

        # Get memory statistics
        memory_stats = {
            "core_entries": len(integration_instance.memory_manager.core.entries),
            "warm_nichos": len(list(integration_instance.memory_manager.warm.warm_dir.glob('*.json'))),
            "cold_sessions": len(list(integration_instance.memory_manager.cold.cold_dir.glob('*.json'))),
        }

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "memory_stats": memory_stats,
            "agents_count": len(AgentType),
            "supported_nichos": len(integration_instance.config.nichos_premium)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))