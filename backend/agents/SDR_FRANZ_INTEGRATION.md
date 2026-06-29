# Integração LangGraph com SDR/Franz

## Visão Geral

Este documento explica como usar o novo sistema LangGraph em conjunto com o SDR/Franz existente.

## Arquitetura da Integração

```
┌─────────────────────────────────────────────────────────────┐
│                    SDR/Franz Existente                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐   │
│  │ Hook    │→ │ Qualify │→ │ Pain    │→ │ ... → Close │   │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Bridge de Integração
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Novo Sistema LangGraph                      │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐   │
│  │ Memory      │  │ Router      │  │ Error Handler     │   │
│  │ System      │  │ Intelligent │  │ Circuit Breaker   │   │
│  └─────────────┘  └─────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Uso Básico

### 1. Sincronizar Memória do Lead

```python
from backend.agents.fralib_integration import sync_sdr_memory

# Após cada interação do SDR/Franz
memory_data = {
    "lead_id": "123",
    "active_agent": "vendas",
    "stage": "close",
    "segmento": "restaurante",
    "bant_budget": "1500_5000",
    "agent_notes": {"vendas": "Lead interessado em Pix"}
}

result = sync_sdr_memory(
    memory_data=memory_data,
    session_id="lead_123",
    user_id=1
)

# Result contém:
# - _memory_context: Contexto de memória
# - _memory_entries: Número de entradas de memória
```

### 2. Obter Contexto de Roteamento

```python
from backend.agents.fralib_integration import get_sdr_routing_context

# Antes de selecionar o próximo agente
context = get_sdr_routing_context(
    session_id="lead_123",
    user_id=1,
    lead_data={
        "active_agent": "vendas",
        "stage": "close",
        "segmento": "restaurante"
    }
)

# Result contém:
# - recommended_agent: Agente recomendado
# - routing_reason: Razão do roteamento
# - confidence: Confiança do routing
# - memory_context: Contexto de memória
```

### 3. Tratar Erros

```python
from backend.agents.fralib_integration import handle_sdr_error

try:
    # Código do SDR/Franz
    response = sdr_agent.process(message)
except Exception as e:
    error_context = handle_sdr_error(
        error=e,
        state={"active_agent": "vendas", "stage": "close"},
        session_id="lead_123"
    )

    if error_context["should_escalate"]:
        # Transferir para supervisor
        pass
```

### 4. Registrar Interações

```python
from backend.agents.fralib_integration import record_sdr_interaction

# Após cada interação
record_sdr_interaction(
    session_id="lead_123",
    user_id=1,
    lead_data={"active_agent": "vendas", "segmento": "restaurante"},
    user_message="Quanto custa?",
    agent_response="R$ 1.499 em até 12x",
    stage="close",
    success=True  # Ou False se falhou
)
```

### 5. Preparar Handoff para Closer

```python
from backend.agents.fralib_integration import prepare_closer_handoff

# Quando o lead está pronto para fechamento humano
context = prepare_closer_handoff(
    session_id="lead_123",
    user_id=1,
    lead_data={
        "lead_id": "123",
        "nome": "João Silva",
        "telefone": "11999999999",
        "stage": "close",
        "segmento": "restaurante",
        "bant_budget": "1500_5000",
        "lead_temperature": "quente",
        "pain_identified": "Precisa de site para delivery"
    },
    history=[
        {"role": "user", "content": "Quero ver o site"},
        {"role": "assistant", "content": "Aqui está..."}
    ]
)

# Result contém score combinado e contexto de memória
print(f"Score Total: {context['total_score']}")
print(f"Ação Recomendada: {context['recommended_action']}")
```

### 6. Detectar Intenção

```python
from backend.agents.fralib_integration import detect_sdr_intent

# Analisar mensagem do lead
result = detect_sdr_intent("Quanto custa o site?")
# Result: {"intent": "price", "confidence": 0.8, "message": "Quanto custa..."}
```

### 7. Calcular Complexidade do Lead

```python
from backend.agents.fralib_integration import calculate_sdr_lead_complexity

complexity = calculate_sdr_lead_complexity({
    "segmento": "restaurante",
    "qtd_reviews": 25,
    "tier": "PREMIUM",
    "tem_site": True,
    "servicos": ["delivery", "mesas", "bar"]
})
# Returns: "complexo"
```

## Endpoints REST

### Sincronizar Memória
```
POST /api/franz-bridge/memory/sync
{
    "session_id": "lead_123",
    "user_id": 1,
    "memory_data": {...}
}
```

### Obter Contexto de Routing
```
POST /api/franz-bridge/routing
{
    "session_id": "lead_123",
    "user_id": 1,
    "lead_data": {...}
}
```

### Registrar Interação
```
POST /api/franz-bridge/interaction
{
    "session_id": "lead_123",
    "user_id": 1,
    "lead_data": {...},
    "user_message": "...",
    "agent_response": "...",
    "stage": "close",
    "success": true
}
```

### Preparar Handoff
```
POST /api/franz-bridge/closer-handoff
{
    "session_id": "lead_123",
    "user_id": 1,
    "lead_data": {...},
    "history": [...]
}
```

### Detectar Intenção
```
POST /api/franz-bridge/intent
{
    "message": "Quanto custa?"
}
```

### Calcular Complexidade
```
POST /api/franz-bridge/complexity
{
    "lead_data": {...}
}
```

### Health Check
```
GET /api/franz-bridge/health
GET /api/franz-bridge/stats
```

## Exemplo Completo de Integração

```python
"""
Exemplo completo de integração com o SDR/Franz
"""
import asyncio
from backend.agents.fralib_integration import (
    sync_sdr_memory,
    get_sdr_routing_context,
    record_sdr_interaction,
    prepare_closer_handoff,
    handle_sdr_error,
    calculate_sdr_lead_complexity
)


class SDRWithMemory:
    """SDR wrapper que adiciona memória ao sistema existente"""

    def __init__(self, user_id: int):
        self.user_id = user_id

    async def process_message(self, lead_data: dict, message: str):
        session_id = f"lead_{lead_data.get('lead_id', 'unknown')}"

        # 1. Sincronizar memória antes de processar
        sync_sdr_memory(lead_data, session_id, self.user_id)

        # 2. Calcular complexidade
        complexity = calculate_sdr_lead_complexity(lead_data)
        print(f"Lead complexity: {complexity}")

        # 3. Obter contexto de routing
        routing = get_sdr_routing_context(session_id, self.user_id, lead_data)
        print(f"Recommended agent: {routing['recommended_agent']}")

        # 4. Processar mensagem com o SDR existente
        try:
            response = await self._call_sdr(lead_data, message)
            success = True
        except Exception as e:
            error = handle_sdr_error(e, lead_data, session_id)
            print(f"Error handled: {error['error_type']}")
            if error['should_escalate']:
                response = "Transferindo para um especialista..."
                success = False
            else:
                response = "Desculpe, tive um problema. Pode repetir?"

        # 5. Registrar interação
        record_sdr_interaction(
            session_id=session_id,
            user_id=self.user_id,
            lead_data=lead_data,
            user_message=message,
            agent_response=response,
            stage=lead_data.get("stage", "hook"),
            success=success
        )

        return response

    async def handoff_to_closer(self, lead_data: dict, history: list):
        """Prepara e executa handoff para closer"""
        session_id = f"lead_{lead_data.get('lead_id', 'unknown')}"

        context = prepare_closer_handoff(
            session_id=session_id,
            user_id=self.user_id,
            lead_data=lead_data,
            history=history
        )

        # Usar contexto para decisão
        if context["total_score"] > 40:
            return {
                "action": "call",
                "priority": "high",
                "context": context
            }
        else:
            return {
                "action": "whatsapp",
                "priority": "normal",
                "context": context
            }

    async def _call_sdr(self, lead_data: dict, message: str):
        """Chama o SDR/Franz existente"""
        # Aqui você chama o SDR/Franz normalmente
        from backend.agents.sdr_langgraph import responder_lead
        return await responder_lead(lead_data, message)


# Uso
async def main():
    sdr = SDRWithMemory(user_id=1)

    lead = {
        "lead_id": "123",
        "nome": "João Silva",
        "telefone": "11999999999",
        "segmento": "restaurante",
        "stage": "close",
        "bant_budget": "1500_5000",
        "lead_temperature": "quente"
    }

    # Processar mensagem
    response = await sdr.process_message(lead, "Quero fechar negócio")
    print(f"Response: {response}")

    # Handoff para closer
    handoff = await sdr.handoff_to_closer(lead, [{"role": "user", "content": "Quero fechar"}])
    print(f"Handoff: {handoff['action']}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Benefícios da Integração

1. **Memória Persistente**: O sistema aprende com cada interação
2. **Routing Inteligente**: Detecção automática de intenções
3. **Error Handling Robusto**: Circuit breaker e escalonamento
4. **Score Enriquecido**: BANT + memória para decisões de handoff
5. **Fallback Seguro**: Funciona mesmo se o novo sistema falhar

## Notas de Implementação

- O novo sistema é **aditivo** - não substitui o SDR/Franz
- O SDR/Franz continua sendo a fonte principal de lógica
- O novo sistema adiciona: memória, routing, e tratamento de erros
- Em caso de falha do bridge, o SDR/Franz continua funcionando normalmente