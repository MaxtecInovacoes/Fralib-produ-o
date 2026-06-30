"""
LangGraph Agent Module - Main module entry point
"""

from .state import AgentState, AgentType, ConversationStage, LeadComplexity
from .profiles import AGENT_PROFILES, get_agent_profile, get_stage_agent
from .router import AgentRouter, IntentDetector, create_handoff_record
from .memory import MemoryManager, get_memory_manager
from .error_handler import ErrorHandler, ErrorType, ErrorSeverity, CircuitBreaker
from .agent import LangGraphAgent, get_agent
from .endpoints import router as endpoints_router

__version__ = "1.0.0"
__author__ = "FraLib Team"

# Export main classes and functions
__all__ = [
    # State management
    "AgentState",
    "AgentType",
    "ConversationStage",
    "LeadComplexity",
    "create_initial_state",

    # Profiles
    "AGENT_PROFILES",
    "get_agent_profile",
    "get_stage_agent",

    # Routing
    "AgentRouter",
    "IntentDetector",
    "create_handoff_record",

    # Memory
    "MemoryManager",
    "get_memory_manager",
    "MemoryEntry",

    # Error handling
    "ErrorHandler",
    "ErrorType",
    "ErrorSeverity",
    "CircuitBreaker",
    "get_error_handler",
    "get_circuit_breaker",

    # Main agent
    "LangGraphAgent",
    "get_agent",

    # API endpoints
    "endpoints_router",
]