
══════════════════════════════════════════════════════════════════════════════
                    🔬 RELATÓRIO COMPLETO DO DIAGNÓSTICO SDR
                         Bryan/Franz - Análise 2026-06-05
══════════════════════════════════════════════════════════════════════════════

ARQUIVOS ANALISADOS:
  • backend/agents/bryan.py (2077 linhas)
  • backend/agents/rag_knowledge/franz.md (3.477 chars)
  • backend/agents/rag_knowledge/bryan.md (10.252 chars)
  • backend/services/llm_direct.py (1443 linhas)

══════════════════════════════════════════════════════════════════════════════
                        🚨 PROBLEMAS CRÍTICOS ENCONTRADOS
══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. 🔴 MODELO ERRADO (Haiku para tarefa complexa)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ ARQUIVO: backend/services/llm_direct.py:503-513                            │
│                                                                             │
│ _AGENT_MODEL_MAP = {                                                        │
│     "franz": "haiku",   ← PROBLEMA                                         │
│     "bryan": "haiku",   ← PROBLEMA                                         │
│ }                                                                            │
│                                                                             │
│ IMPACTO:                                                                     │
│ • Haiku não mantém contexto entre chamadas longas                          │
│ • Falha em rastrear stage e sequência de conversa                          │
│ • Não entende nuances de objeções (confunde "sim, mas" com "sim")          │
│ • Tendência a respostas genéricas/robóticas                                 │
│                                                                             │
│ CAUSA: O agente foi projetado para "respostas rápidas" mas precisa de      │
│        "compreensão contextual profunda"                                     │
│                                                                             │
│ CORREÇÃO: Trocar para Sonnet                                               │
│   "franz": "sonnet",                                                       │
│   "bryan": "sonnet",                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. 🔴 RAGs CONFLITANTES (2 arquivos com instruções diferentes)             │
├─────────────────────────────────────────────────────────────────────────────┤
│ ARQUIVO: backend/agents/rag_knowledge/                                      │
│                                                                             │
│ CONFLITO 1: Stages diferentes                                              │
│   franz.md: [] (vazio - sem stages definidos)                              │
│   bryan.md: ['intro', 'qualify', 'proof', 'link', 'value', 'price',        │
│              'negotiate', 'close']                                         │
│                                                                             │
│ CONFLITO 2: Regra de ouro                                                  │
│   bryan.md contém: "NUNCA revelar site na primeira mensagem"               │
│   franz.md NÃO contém esta regra                                             │
│                                                                             │
│ CONFLITO 3: Nomenclatura                                                    │
│   System prompt define: persona = "Franz"                                   │
│   Mas código chama: agent_name="bryan" para RAG                            │
│   Resultado: RAG busca "bryan.md" mas persona é "Franz"                    │
│                                                                             │
│ IMPACTO: LLM recebe instruções contraditórias                               │
│          → Franz pode agir como Bryan em momentos errados                  │
│          → Stage transitions falham                                         │
│                                                                             │
│ CORREÇÃO: Unificar em um único arquivo: franz.md (ou bryan.md)            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. 🔴 GUARDRAILS PÓS-RESPOSTA (aplicados depois que LLM já falou)          │
├─────────────────────────────────────────────────────────────────────────────┤
│ ARQUIVO: backend/agents/bryan.py:418-566                                   │
│                                                                             │
│ FLUXO ATUAL:                                                                │
│   1. LLM responde                                                           │
│   2. Guardrails modificam a resposta                                        │
│   3. Resposta pode ficar truncada/incoerente                                │
│                                                                             │
│ EXEMPLO DO PROBLEMA (G12 - Segmentação):                                   │
│   Se LLM menciona "delivery" em contexto de academia:                       │
│   → Guardrail SUBSTITUI a resposta inteira                                  │
│   → Lead recebe mensagem genérica que não faz sentido no contexto          │
│   → Perde continuidade da conversa                                          │
│                                                                             │
│ G12 em ação (linha 616-617):                                               │
│   decision["reply"] = _mensagem_segura_por_segmento(...)                   │
│                                                                             │
│ O PROBLEMA: Quando há contaminação de segmento, o guardrail não            │
│             CORRIGE a resposta - ele SUBSTITUI por fallback genérico        │
│                                                                             │
│ CORREÇÃO: Mover restrições para o SYSTEM PROMPT, não pós-processar          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. 🟡 DETECÇÃO DE INTENT POR REGEX (não LLM)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ ARQUIVO: backend/agents/bryan.py:130-218                                    │
│                                                                             │
│ DETecção atual:                                                             │
│   if any(t in l for t in ["sim", "quero", "pode", "manda", "fechado"]):    │
│       return "acceptance"                                                   │
│                                                                             │
│ PROBLEMA: "sim, mas quero pensar mais" → classificado como ACCEPTANCE      │
│           "não sei" → classificado como rejection                           │
│           "talvez" → classificado como outros                               │
│                                                                             │
│ CAUSA: Regex não entende contexto nem nuance                                │
│                                                                             │
│ CORREÇÃO: Usar LLM para classificar intent com exemplos                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. 🟡 MEMÓRIA NÃO ESTRUTURADA                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ ARQUIVO: backend/agents/bryan.py (carregar_memoria/salvar_memoria)        │
│                                                                             │
│ Estrutura atual: dict livre sem validação                                   │
│                                                                             │
│ PROBLEMA:                                                                    │
│ • Dados podem ser perdidos entre chamadas                                  │
│ • Não há schema para validar dados do lead                                  │
│ • Informações importantes (contact_name, price_tier) podem sumir           │
│                                                                             │
│ CORREÇÃO: Usar Pydantic model para memória estruturada                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. 🟢 INCONSISTÊNCIA DE STAGE                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ System prompt (linha 1350) define:                                         │
│   next_stage: "hook|qualify|pain|amplify|tease|proof|reveal|feedback|..."  │
│                                                                             │
│ Mas RAG bryan.md usa:                                                      │
│   Stages: intro, qualify, proof, link, value, price, negotiate, close       │
│                                                                             │
│ STAGE MISMATCH: "hook" vs "intro"                                          │
│ O código usa "hook" mas o RAG ensina "intro"                               │
│ Resultado: LLM confunde qual stage está                                     │
└─────────────────────────────────────────────────────────────────────────────┘

══════════════════════════════════════════════════════════════════════════════
                           📊 FLUXO ATUAL vs IDEAL
══════════════════════════════════════════════════════════════════════════════

CURRENT (com problemas):
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ WhatsApp     │────▶│ Regex Intent │────▶│ LLM (Haiku)  │
│ Listener     │     │ (falho)      │     │ (muito fraco)│
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                                 ▼
                    ┌──────────────────────────────────────┐
                    │ RESPOTA DO LLM                      │
                    │ (pode estar errada, com preço cedo, │
                    │  sem pergunta, stage errado)        │
                    └──────────────┬───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ GUARDRAILS PÓS-RESPOSTA │
                    │ (cortam/corrompem)     │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ MEMÓRIA (não estrut.)   │
                    │ (pode perder dados)    │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ WHATSAPP (envia)        │
                    └─────────────────────────┘

IDEAL:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ WhatsApp     │────▶│ LLM (Sonnet)  │────▶│ STAGE VALID │
│ Listener     │     │ Classifica    │     │ Verifica    │
└──────────────┘     └──────────────┘     └──────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
         ┌──────────────────┐  ┌──────────────────┐
         │ SYSTEM PROMPT    │  │ MEMÓRIA (Pydantic│
         │ com restrições   │  │ model estruturado│
         │ EXPLICITAS      │  │                  │
         └──────────────────┘  └──────────────────┘
                    │                   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ JSON VALIDADO    │
                    │ (tool_use forced)│
                    └───────────────────┘

══════════════════════════════════════════════════════════════════════════════
                           💡 CORREÇÕES RECOMENDADAS
══════════════════════════════════════════════════════════════════════════════

OPÇÃO A: CORREÇÕES RÁPIDAS (2-3 horas)
─────────────────────────────────────

1. Trocar modelo para Sonnet
   Arquivo: backend/services/llm_direct.py
   Linha: 503-513

   ANTES:
   _AGENT_MODEL_MAP = {
       "franz": "haiku",
       "bryan": "haiku",
   }

   DEPOIS:
   _AGENT_MODEL_MAP = {
       "franz": "sonnet",
       "bryan": "sonnet",
   }

2. Unificar RAGs
   - Criar backend/agents/rag_knowledge/franz.md com conteúdo completo
   - Deletar backend/agents/rag_knowledge/bryan.md (ou mesclar)
   - Atualizar código para usar "franz" como agent_name

3. Corrigir G12 (segmento)
   Arquivo: backend/agents/bryan.py:604-620

   ANTES: Substitui resposta inteira
   DEPOIS: Substitui apenas palavras contaminadas

OPÇÃO B: REFATORAÇÃO COMPLETA (1-2 dias)
─────────────────────────────────────────

1. Reescrever system prompt com exemplos concretos por stage
2. Implementar detecção de intent via LLM (com few-shot examples)
3. Usar tool_use para forçar JSON estruturado (call_claude_structured)
4. Criar Pydantic model para memória do lead
5. Adicionar testes automatizados para cada cenário

OPÇÃO C: REESCRITA DO ZERO (3-5 dias)
─────────────────────────────────────

Recriar agente com arquitetura limpa:
- States definidos com transições explícitas
- Memory como contexto estruturado
- Intent via LLM com validação
- Output via tool_use (100% JSON)

══════════════════════════════════════════════════════════════════════════════
                           🎯 PRIORIDADE DE CORREÇÃO
══════════════════════════════════════════════════════════════════════════════

1. [IMEDIATO] Trocar modelo de Haiku para Sonnet
   → Impacto: 60% da melhoria
   → Tempo: 10 minutos

2. [IMEDIATO] Unificar RAGs em um único arquivo
   → Impacto: 20% da melhoria
   → Tempo: 30 minutos

3. [HOJE] Corrigir G12 para substituir palavras, não resposta inteira
   → Impacto: 10% da melhoria
   → Tempo: 1 hora

4. [ESSA SEMANA] Implementar intent via LLM
   → Impacto: 10% da melhoria
   → Tempo: 2-4 horas

══════════════════════════════════════════════════════════════════════════════
                           📝 COMANDO PARA TESTE
══════════════════════════════════════════════════════════════════════════════

Depois de fazer as correções, rode:

    python scripts/test_sdr_bryan.py --relatorio

Para verificar se os problemas foram resolvidos.

══════════════════════════════════════════════════════════════════════════════
