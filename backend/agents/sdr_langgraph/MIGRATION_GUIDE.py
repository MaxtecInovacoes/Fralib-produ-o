"""
SDR LangGraph Agent - Migration Guide
═══════════════════════════════════════════════════════════════════════════════

A migração do bryan.py para sdr_langgraph/ mantém 100% de compatibilidade
com o resto do sistema. As funções responder_lead, iniciar_contato e
followup_automatico têm a mesma assinatura.

═══════════════════════════════════════════════════════════════════════════════
                        ESTRUTURA DE ARQUIVOS
═══════════════════════════════════════════════════════════════════════════════

backend/agents/sdr_langgraph/
├── __init__.py          # Exports
├── state.py             # SDRState (TypedDict) + LeadMemory (Pydantic)
├── prompts.py           # System prompts estruturados por stage
├── tools.py             # RAG, intent detection, validações
├── agent.py             # Grafo LangGraph + nodes
└── compat.py            # Interface compatível com bryan.py

═══════════════════════════════════════════════════════════════════════════════
                        COMO USAR
═══════════════════════════════════════════════════════════════════════════════

# Forma 1: Import direto (recomendado)
from backend.agents.sdr_langgraph import (
    iniciar_contato,
    responder_lead,
    followup_automatico,
    LeadMemory,
    StageEnum,
)

# Iniciar contato
from backend.agents.sdr_langgraph import BryanInput
lead = BryanInput(
    nome="FitLife Academia",
    cidade="Curitiba",
    segmento="academia",
    telefone="41999999999",
    rating=4.2,
    site_url="https://fitlife.fralib.com.br",
)
output = iniciar_contato(lead, user_id=1)
print(output.reply)  # Mensagem do Franz

# Responder lead
output = responder_lead(
    telefone="41999999999",
    mensagem_recebida="oi",
    user_id=1,
)

# Follow-up
output = followup_automatico(
    telefone="41999999999",
    tipo="24h",
    user_id=1,
)

═══════════════════════════════════════════════════════════════════════════════
                        COMO MIGRAR DO BRYAN
═══════════════════════════════════════════════════════════════════════════════

PASSO 1: Substituir imports
─────────────────────────────────

# (legacy - removido)
# from agents.bryan import iniciar_contato, responder_lead, followup_automatico

# DEPOIS
from backend.agents.sdr_langgraph import iniciar_contato, responder_lead, followup_automatico

PASSO 2: Trocar Haiku por Sonnet
─────────────────────────────────

# backend/services/llm_direct.py
_AGENT_MODEL_MAP = {
    "franz": "sonnet",  # ← Era haiku
    "bryan": "sonnet",
}

PASSO 3: Unificar RAGs
─────────────────────────────────

# Deletar ou mesclar bryan.md em franz.md
# Manter apenas um arquivo RAG

PASSO 4: Aposentar bryan.py (opcional)
─────────────────────────────────

# Mover bryan.py para bryan.py.legacy
# OU manter como fallback se preferir

═══════════════════════════════════════════════════════════════════════════════
                        VANTAGENS DO LANGGRAPH
═══════════════════════════════════════════════════════════════════════════════

1. ESTADOS EXPLÍCITOS
   - Cada stage é um node separado
   - Não depende do LLM decidir em que stage está
   - Código decide routing, não prompt

2. TRANSIÇÕES VALIDADAS
   - VALID_TRANSITIONS garante que não pula stages
   - memory.update_stage() valida antes de mudar

3. MEMÓRIA TIPADA
   - LeadMemory é Pydantic model
   - Campos validados automaticamente
   - Sem dict livre se perdendo dados

4. TESTÁVEL
   - Cada node é uma função pura
   - Pode ser testado isoladamente
   - Mock de LLM é trivial

5. EXTENSÍVEL
   - Adicionar novo stage = criar nova função + edge
   - Adicionar tool = criar novo node
   - Não precisa mexer no prompt

═══════════════════════════════════════════════════════════════════════════════
                        DIFERENÇAS vs BRYAN.PY
═══════════════════════════════════════════════════════════════════════════════

| Aspecto              | bryan.py (antigo)        | sdr_langgraph (novo)     |
|----------------------|--------------------------|--------------------------|
| Modelo               | Haiku                   | Sonnet                   |
| RAGs                 | 2 conflitantes           | 1 unificado              |
| Estágios             | Inferido pelo LLM       | Explícito (StateGraph)   |
| Transições           | Sugeridas pelo LLM      | Validadas pelo código    |
| Memória              | Dict livre              | Pydantic model           |
| Detecção intent      | Regex                   | LLM (Haiku)              |
| Validação de stage   | None                    | VALID_TRANSITIONS        |
| Contaminação         | Substitui msg inteira    | Substitui palavras       |
| Guardrails           | Pós-resposta (G1-G13)   | Pré-resposta (no prompt) |
| Tamanho do código    | 2077 linhas             | ~500 linhas              |
| Testabilidade         | Difícil                 | Fácil                    |

═══════════════════════════════════════════════════════════════════════════════
"""

print(__doc__)
