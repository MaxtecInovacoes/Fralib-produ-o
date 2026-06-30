"""
LangGraph Agent Endpoints - REST API for LangGraph agents
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import uuid
import asyncio
from datetime import datetime

from .agent import get_agent
from .state import AgentType, AgentState
from .profiles import get_agent_profile
from .memory import get_memory_manager
from .error_handler import get_error_handler

router = APIRouter()


class MessageRequest(BaseModel):
    """Request model for processing messages"""
    session_id: Optional[str] = None
    lead_facts: Dict[str, Any]
    user_message: str
    is_outbound: bool = True


class MessageResponse(BaseModel):
    """Response model for message processing"""
    session_id: str
    status: str
    final_agent: str
    messages_processed: int
    response: str
    error: Optional[str] = None
    error_context: Optional[Dict[str, Any]] = None
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


class SessionSummary(BaseModel):
    """Session summary model"""
    session_id: str
    total_messages: int
    current_agent: str
    conversation_stages: List[str]
    error_summary: Dict[str, Any]
    memory_stats: Dict[str, Any]


# Global agent instance
agent_instance = get_agent()
memory_manager = get_memory_manager()
error_handler = get_error_handler()


@router.post("/process", response_model=MessageResponse)
async def process_message(request: MessageRequest):
    """Process a message through the LangGraph agent system"""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Process message
        result = await agent_instance.process_message(
            session_id=session_id,
            lead_facts=request.lead_facts,
            user_message=request.user_message,
            is_outbound=request.is_outbound
        )

        # Extract response from last message
        messages = result.get("result", {}).get("messages", [])
        response = messages[-1].content if messages else "No response generated"

        return MessageResponse(
            session_id=result["session_id"],
            status=result["status"],
            final_agent=result.get("final_agent", "unknown"),
            messages_processed=result.get("messages_processed", 0),
            response=response,
            error=result.get("error"),
            error_context=result.get("error_context"),
            escalated=result.get("escalated", False)
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


@router.get("/session/{session_id}", response_model=SessionSummary)
async def get_session_summary(session_id: str):
    """Get session summary"""
    try:
        # Load session state
        session_state = memory_manager.load_session_state(session_id)

        if not session_state:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get error summary
        error_summary = error_handler.get_error_summary(session_id)

        # Get memory stats
        memory_stats = {
            "core_entries": len(session_state.get("memory_entries", [])),
            "agent_notes": len(session_state.get("agent_notes", {})),
            "handoff_count": len(session_state.get("handoff_log", []))
        }

        return SessionSummary(
            session_id=session_id,
            total_messages=len(session_state.get("messages", [])),
            current_agent=session_state.get("current_agent", "unknown").value,
            conversation_stages=[session_state.get("conversation_stage", "unknown").value],
            error_summary=error_summary,
            memory_stats=memory_stats
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/reset")
async def reset_session(session_id: str):
    """Reset a session"""
    try:
        # Clear session data
        memory_manager.save_session_state(session_id, {
            "session_id": session_id,
            "messages": [],
            "current_agent": AgentType.ATENDIMENTO,
            "conversation_stage": "hook",
            "memory_entries": [],
            "agent_notes": {},
            "handoff_log": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })

        return {"message": "Session reset successfully", "session_id": session_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_status": "ready",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        # Get error handler stats
        error_stats = {
            "total_errors": len(error_handler.error_history),
            "circuit_breaker_state": error_handler.circuit_breaker.get_state()
        }

        return {
            "status": "healthy",
            "error_stats": error_stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-intent")
async def test_intent_detection(text: str):
    """Test intent detection on a text"""
    try:
        from .router import IntentDetector

        detector = IntentDetector()
        intent = detector.detect_intent(text)

        return {
            "text": text,
            "detected_intent": intent,
            "confidence": 0.8  # Mock confidence
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-complexity")
async def test_complexity_calculation(lead_facts: Dict[str, Any]):
    """Test complexity calculation on lead facts"""
    try:
        from .state import AgentConfig

        config = AgentConfig()
        complexity = config.calculate_complexity(lead_facts)

        return {
            "lead_facts": lead_facts,
            "calculated_complexity": complexity.value,
            "score_breakdown": {
                "reviews": lead_facts.get("qtd_reviews", 0),
                "nicho_premium": 1 if lead_facts.get("nicho") in config.nichos_premium else 0,
                "tier": lead_facts.get("tier", ""),
                "has_site": lead_facts.get("tem_site", False),
                "services_count": len(lead_facts.get("servicos", []))
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))