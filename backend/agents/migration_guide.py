"""
Migration guide from old SDR system to LangGraph agents
"""

import sys
import os
from typing import Dict, Any

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def migration_guide():
    """Print comprehensive migration guide"""

    guide = """
# Migration Guide: Old SDR System → LangGraph Agents

## Overview
This guide explains how to migrate from the old SDR system to the new LangGraph-based agent system.

## Key Differences

### Old System (sdr_langgraph/)
- Manual handoff management
- Simple state tracking
- Basic error handling
- No persistent memory
- Hardcoded routing rules

### New System (langgraph/)
- LangGraph state machines
- Centralized state management
- Advanced error handling with circuit breaker
- Hierarchical memory system (Core/Warm/Cold)
- Dynamic routing with intent detection
- REST API endpoints
- CLI tools for debugging

## Migration Steps

### 1. Update Dependencies
```bash
# Install LangGraph dependencies
pip install -r requirements_langgraph.txt

# Add to main requirements.txt
langgraph>=0.2.0
langchain>=0.2.0
langchain-core>=0.2.0
fastapi>=0.104.0
uvicorn>=0.24.0
```

### 2. Import Changes

#### Old Imports
```python
from backend.agents.sdr_langgraph.multi_agent import choose_agent, build_agent_context
from backend.agents.sdr_langgraph.agent import SDRGraph
from backend.agent_memory import CoreMemory, WarmMemory
```

#### New Imports
```python
from backend.agents.langgraph.state import AgentType, AgentConfig, create_initial_state
from backend.agents.langgraph.profiles import get_agent_profile, build_agent_context
from backend.agents.langgraph.agent import LangGraphAgent
from backend.agents.langgraph.memory import MemoryManager
from backend.agents.fralib_integration import FraLibLangGraphIntegration
```

### 3. Agent Management

#### Old Agent Selection
```python
def choose_agent(intent: str, stage: str, incoming: str, is_outbound: bool):
    # Hardcoded rules
    if "preco" in text:
        return "vendas", "lead_perguntou_preco"
```

#### New Agent Selection
```python
from backend.agents.langgraph.router import AgentRouter

router = AgentRouter()
next_agent, reason = router.determine_next_agent(state, user_message)
```

### 4. State Management

#### Old State
```python
class AgentRouter:
    def __init__(self, complexidade: str = "medio"):
        self.complexidade = complexidade
```

#### New State
```python
from backend.agents.langgraph.state import AgentState, create_initial_state

state = create_initial_state(lead_facts, session_id)
state["current_agent"] = AgentType.VENDAS.value
state["conversation_stage"] = ConversationStage.TEASE
```

### 5. Memory Management

#### Old Memory
```python
from backend.agent_memory import CoreMemory, WarmMemory

core = CoreMemory()
core.adicionar(entry)
```

#### New Memory
```python
from backend.agents.langgraph.memory import MemoryManager

memory_manager = MemoryManager()
memory_manager.add_experience(
    session_id=session_id,
    agent_type="vendas",
    nicho="restaurante",
    content="Experience content",
    confidence=0.7
)
```

### 6. Error Handling

#### Old Error Handling
```python
try:
    # Agent processing
    pass
except Exception as e:
    print(f"Error: {e}")
```

#### New Error Handling
```python
from backend.agents.langgraph.error_handler import ErrorHandler, ErrorType

error_handler = ErrorHandler()
error_context = error_handler.handle_error(error, state)
if error_handler.should_escalate(state):
    return "supervisor"
```

### 7. API Integration

#### Old API Calls
```python
# Direct agent calls
result = await sdr_graph.process_message(lead_facts, user_message)
```

#### New API Calls
```python
from backend.agents.fralib_integration import FraLibLangGraphIntegration

integration = FraLibLangGraphIntegration()
result = await integration.process_lead_conversation(lead_facts, conversation_history)
```

### 8. Configuration

#### Old Configuration
```python
ROUTING_TABLE = {
    "vendas": {"complexo": "sonnet", "medio": "sonnet", "simples": "sonnet"},
}
```

#### New Configuration
```python
from backend.agents.langgraph.state import AgentConfig

config = AgentConfig()
complexity = config.calculate_complexity(lead_facts)
model = config.get_model(AgentType.VENDAS, complexity)
```

## Migration Checklist

### Phase 1: Setup
- [ ] Install LangGraph dependencies
- [ ] Create backup of existing system
- [ ] Test individual components

### Phase 2: Core Migration
- [ ] Update imports in all files
- [ ] Replace agent selection logic
- [ ] Migrate state management
- [ ] Update memory handling

### Phase 3: Integration
- [ ] Update API endpoints
- [ ] Add new endpoints for LangGraph
- [ ] Update frontend calls
- [ ] Add health checks

### Phase 4: Testing
- [ ] Run unit tests
- [ ] Run integration tests
- [ ] Test error handling
- [ ] Test memory persistence

### Phase 5: Deployment
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Monitor performance
- [ ] Deploy to production

## Common Issues and Solutions

### Issue 1: LangGraph Import Errors
```python
# Fix: Update imports
from langgraph.graph import StateGraph, END, START
# Remove: from langgraph.prebuilt import ToolExecutor
```

### Issue 2: State Type Mismatches
```python
# Fix: Convert enums to strings
state["current_agent"] = AgentType.VENDAS.value  # Not AgentType.VENDAS
```

### Issue 3: Memory Persistence
```python
# Fix: Use new memory manager
memory_manager = MemoryManager()
# Not: CoreMemory() and WarmMemory()
```

### Issue 4: Error Handling
```python
# Fix: Use new error handler
error_handler = ErrorHandler()
# Not: try/except blocks only
```

## Performance Considerations

### Memory Usage
- Old: Simple in-memory storage
- New: Hierarchical storage with persistence

### Processing Speed
- Old: Direct function calls
- New: State graph processing with async support

### Scalability
- Old: Limited to single process
- New: Multi-process support with circuit breaker

## Testing Strategy

### Unit Tests
```python
# Test individual components
from backend.agents.langgraph.state import AgentType, AgentConfig
from backend.agents.langgraph.router import AgentRouter
from backend.agents.langgraph.memory import MemoryManager
```

### Integration Tests
```python
# Test full conversation flow
from backend.agents.fralib_integration import FraLibLangGraphIntegration
integration = FraLibLangGraphIntegration()
result = await integration.process_lead_conversation(lead_facts, history)
```

### Performance Tests
```python
# Test memory and processing performance
import time
start = time.time()
# Process conversation
end = time.time()
print(f"Processing time: {end - start}")
```

## Rollback Plan

If migration fails:
1. Revert imports to old system
2. Restore backup files
3. Restart services
4. Monitor system health

## Support

For issues during migration:
1. Check this guide
2. Run tests in `tests/`
3. Use CLI tool: `python -m backend.agents.langgraph.cli`
4. Review API docs at `/docs` endpoint

## Next Steps

1. Review this guide
2. Create backup
3. Start with Phase 1
4. Test each phase thoroughly
5. Deploy incrementally
"""

    print(guide)

if __name__ == "__main__":
    migration_guide()