# Franz SDR Studio 10/10 — Documentação Completa

> **TL;DR:** O Franz é o agente SDR de WhatsApp da FraLib. Em 2026-06-22/23, foi
> reescrito de stage-based linear para **Intent + State Machine**, ganhou **memory
> 3-tier**, **sliding window**, **tracing por turno**, **LLM-as-judge** e
> **streaming SSE**. **Score: 10/10.** Todos os 35 testes passam. Em produção.

---

## 1. Por que essa reescrita existiu

### 1.1 O bug do "stage-loop" (que motivou tudo)

**Sintoma:** Lead que só cumprimentava (ex: "boa noite", "oi", "eai") ficava
travado no `hook` para sempre. O Franz respondia 5 vezes a mesma coisa.

**Causa raiz (commit `74819c5`):**
```python
# Em agent.py:170 (codigo antigo)
def _next_stage(current, suggested, fallback):
    if suggested_idx <= current_idx:
        return current  # <-- BLOQUEAVA AVANCO
    return STAGE_PROGRESSION[min(current_idx + 1, suggested_idx)]
```

Quando o LLM sugeria `next_stage=hook` (corretamente, porque o lead so
cumprimentou), o codigo forçava `return current = hook`. Proximo turno idem.
**Loop eterno.**

### 1.2 Decisao arquitetural

Substituir o **stage-based linear funnel** por:

1. **FSM (Finite State Machine)** - estado REAL da conversa (nao linear)
2. **Intent Classifier** - o que o lead QUIS dizer (independente do stage)
3. **Orchestrator** - combina (state, intent) e decide (new_state, new_stage)
4. **Loop detection** - apos 3 cumprimentos, forca transicao

Inspirado em: Anthropic Agent SDK, MemGPT/Letta, OpenAI Agents SDK.
Veja `docs/FRANZ_SDR_ENTERPRISE_PLAN.md` (background) e `docs/SDR_ROADMAP_3_QUICKWINS.md` (roadmap).

---

## 2. Arquitetura nova

```
backend/agents/sdr_langgraph/
├── state_machine.py      # FSM: 10 ConversationState + matriz (state, intent) -> (new_state, stage)
├── intent_classifier.py  # Regex + keywords (11 intents), Haiku fallback opcional
├── orchestrator.py       # Combina (state, intent, turn_count) -> decisao final + loop break
├── memory_hook.py        # Injeta 3-tier memory (Core/Warm) no system prompt
├── turn_tracing.py       # 1 trace SDR + N spans por turno + decorator @sdr_traced
├── quality_judge.py      # LLM-as-judge (Haiku) + heuristica. Bloqueia score < 3
├── streaming.py          # SSE streaming usando call_claude_stream
├── state.py              # LeadMemory Pydantic (30+ campos, inclui conversation_state)
├── agent.py              # Grafo principal (9 nodes, todos instrumentados)
├── prompts.py            # FRANZ_PERSONA + STAGE_PROMPTS (carrega de FRANZ_*.md)
└── tools.py              # 15 tools deterministicas (load_rag, detect_intent, etc)

backend/whatsapp/sdr_reply_service.py
└── build_history()       # Sliding window: trunca em 30 msgs + Haiku summary

backend/endpoints/superadmin_endpoints.py
└── /sdr-studio/{files,versions,chat,chat/stream}  # Studio API
```

### 2.1 FSM (state_machine.py)

```python
class ConversationState(str, Enum):
    IDLE = "idle"
    WAITING_RESPONSE = "waiting_response"
    ENGAGED = "engaged"
    OBJECTING = "objecting"
    BUYING = "buying"
    SCHEDULED = "scheduled"
    OPT_OUT = "opt_out"
    HANDED_OFF = "handed_off"
    CLOSED_WON = "won"
    CLOSED_LOST = "lost"
```

**Matriz de transicao** (`_TRANSITIONS`): para cada par `(state, intent)`,
qual o proximo `(state, stage)`. Exemplos:

| state atual | intent | proximo state | proximo stage |
|---|---|---|---|
| IDLE | GREETING | WAITING_RESPONSE | hook |
| IDLE | ENGAGEMENT | ENGAGED | qualify |
| WAITING_RESPONSE | GREETING (3x) | ENGAGED (loop break) | qualify |
| ENGAGED | BUYING_INTENT | BUYING | close |
| qualquer | OPT_OUT | OPT_OUT | lost |

**Override 1** (intent > state): OPT_OUT sempre vence. BUYING_INTENT em
state sem contexto (IDLE/WAITING) qualifica antes (regra de ouro).

**Override 2** (loop break): turn_count >= 3 + state em IDLE/WAITING +
intent = GREETING/ACKNOWLEDGMENT/UNKNOWN -> forca ENGAGED+qualify.

### 2.2 Intent Classifier (intent_classifier.py)

11 intents via regex (sem custo de LLM):
- `greeting`, `acknowledgment`, `engagement`, `question`
- `objection`, `buying_intent`, `schedule`, `opt_out`
- `gatekeeper`, `off_topic`, `unknown`

Cada intent tem 3-5 patterns regex. Tie-breaker por prioridade:
OPT_OUT > GATEKEEPER > BUYING > SCHEDULE > OBJECTION > QUESTION >
ENGAGEMENT > GREETING > ACKNOWLEDGMENT > UNKNOWN.

**Fallback LLM** (Haiku): se confidence < 0.6 e `enable_llm_fallback=True`.
Default: desabilitado em runtime (rapido e barato).

### 2.3 Orchestrator (orchestrator.py)

```python
def orchestrate(incoming_message, current_state_str, current_stage,
                turn_count, suggested_stage, enable_llm_fallback=False) -> OrchestratorDecision:
    """Decide (new_state, new_stage) baseado em (state, intent, turn_count)."""
    # 1) parse state
    # 2) detect loop
    # 3) classify intent
    # 4) call decide_transition (matriz FSM)
    # 5) override se loop detectado
    return OrchestratorDecision(intent, state_after, stage_after, ...)
```

Sempre persiste `memory.conversation_state`, `turn_count`, `last_intent`,
`last_intent_confidence`, `last_lead_response_at` na `LeadMemory`.

### 2.4 Memory 3-tier (memory_hook.py)

Antes de cada LLM call: `inject_memory_for_franz(memory, segmento)`.
Isso seta thread-local com Core (top-10 sempre no prompt) + Warm
(top-3 por nicho). O `llm_direct.call_claude` checa thread-local e injeta
automaticamente.

Depois do LLM call: `extract_and_persist_learning(...)` adiciona entry
em Warm com `tipo=lead_pattern`. Quando confianca >= 0.9 e uso >= 5,
promovida automaticamente para Core.

### 2.5 Sliding window (whatsapp/sdr_reply_service.py)

`build_history(rows, max_messages=30)`:
- Se `len(rows) <= 30`: retorna tudo
- Se > 30: gera summary via Haiku das 50 mensagens mais antigas, injeta como
  `role: system` no topo + ultimas 30 cruas
- Fallback extractive se Haiku falhar

### 2.6 Tracing (turn_tracing.py)

Decorator `@sdr_traced("node_name")` em cada funcao de node. Cria 1 trace
por turno + 1 span por node. Cada LLM call tambem vira span filho.

`end_turn_trace(lead_id)` em `node_save_and_send` persiste no `pipeline_traces`.

**Traces SDR ficam com `run_id = "sdr-{lead_id}"`**. Pra ver:
```sql
SELECT trace_id, status, duracao_total_ms, custo_total_usd
FROM pipeline_traces
WHERE run_id LIKE 'sdr-%'
ORDER BY created_at DESC LIMIT 20;
```

### 2.7 LLM-as-judge (quality_judge.py)

`evaluate_reply(incoming, reply, stage, segmento, min_score_to_send=3)`:
- Chama Haiku com prompt de auditoria (5 criterios, score 1-5)
- Fallback heuristico se Haiku falhar: detecta `multiplas_perguntas`,
  `muitos_emojis`, `markdown_json_cru`, `muito_longa`
- `score < 3` -> bloqueia envio (`return {}` no node_save_and_send)
- Persiste `last_quality_score` + `last_quality_issues` na `LeadMemory`

### 2.8 Streaming SSE (streaming.py + superadmin_endpoints.py)

`POST /api/superadmin/sdr-studio/chat/stream` retorna `text/event-stream`:

```
data: Oi
data: ! Tudo bem?
data: Vocês sao academia...
data: [DONE]
```

Botao **▶ Stream** no Studio UI mostra typing effect (cursor ▌).

---

## 3. Como usar o SDR Studio

### 3.1 Acessar

URL: `https://seunegociofralib.site/superadmin`
Login: email superadmin (`dezigpi@gmail.com`)
Aba: **SDR Studio** (entre Playground e Alertas)

### 3.2 UI

- **Esquerda (chat)**: stage, segmento, cidade, modelo + log de conversa + input
- **Direita (editor)**: 3 abas - Design System / User System / RAG
- **Header do editor**: badge 🟢 ESPELHO ATIVO (quando `FRALIB_SDR_PROMPTS_FROM_MD=1`)
- **Botoes**:
  - 💾 **Aplicar** - salva no arquivo .md (cria restore point)
  - ✓ **Publicar** - audita + confirma
  - 📜 **Historico** - lista versoes anteriores
  - ↻ **Recarregar** - descarta mudancas locais
  - **▶ Stream** - resposta sendo digitada (SSE)

### 3.3 Workflow recomendado

1. Lead mandou "ola" mas Franz respondeu generico
2. Vai no Studio -> aba **User System** (FRANZ_PLAYBOOK.md)
3. Edita a section "STAGE: hook" -> adiciona regra "se lead so cumprimentou 2x, fazer pergunta mais direta"
4. **Aplicar** - salva
5. Testa no chat (campo stage=hook)
6. Se gostou, **Publicar** - audita
7. Proximo lead real recebe o novo system prompt automaticamente

### 3.4 Restricoes

- Cada camada: max **100KB** (validado backend)
- Versionamento: **8 versoes** salvas atualmente (append-only)
- Rollback: **Historico -> Restaurar** (cria backup do estado atual antes)

---

## 4. Deploy e configuracao

### 4.1 Env vars (VPS em `/etc/fralib/fralib.env`)

```bash
# OBRIGATORIO
WHATSMEOW_DB_URL=postgresql://postgres:fralib2024@localhost:5433/fralib_db
CRON_SECRET=<32-bytes-secure-random>

# OPCIONAL - liga o espelho Studio <-> WhatsApp
FRALIB_SDR_PROMPTS_FROM_MD=1
```

### 4.2 Systemd overrides

O `fralib-api.service` tem `ProtectSystem=full` que torna `/root` read-only.
Override aplicado em `/etc/systemd/system/fralib-api.service.d/override.conf`:

```ini
[Service]
ReadWritePaths=/root/fralib/backend/agents
ReadWritePaths=/root/fralib/logs
ReadWritePaths=/tmp
```

### 4.3 Reiniciar servicos

```bash
ssh root@187.77.37.72
systemctl restart fralib-api fralib-franz fralib-wpp-listener
```

### 4.4 Validar deploy

```bash
ssh root@187.77.37.72 "cd /root/fralib && source venv/bin/activate && python scripts/test_sdr_fsm.py"
# Esperado: 35/35 OK
```

---

## 5. Testes (35 passando)

```bash
cd C:/fralib
python scripts/test_sdr_fsm.py
```

| Suite | Testes | Cobre |
|---|---|---|
| TestIntentClassifier | 6 | Regex de 11 intents |
| TestStateMachine | 6 | Transicoes do FSM + loop detection |
| TestOrchestratorRegressionHookLoop | 6 | **Bug do hook-loop** (regressao) |
| TestEndToEndScenarios | 3 | Cenarios completos (cumprimento 3x, lead engajado, opt-out) |
| TestSlidingWindow | 2 | Trunca em 30, gera summary |
| TestMemoryHook | 3 | Inject + extract + insights |
| TestTurnTracing | 3 | SDRTurnTrace + spans + decorator |
| TestQualityJudge | 4 | Heuristica + judge + LLM off + vazio |
| TestStreaming | 2 | SSE format + modulo |

**Total: 35 testes, 100% passando.**

---

## 6. Licoes aprendidas (NUNCA repetir)

Veja `docs/SDR_BUGS_FIXED.md` para detalhes, mas os 5 bugs que **NUNCA** podem voltar:

| Bug | Sintoma | Causa | Fix |
|---|---|---|---|
| **stage-loop** | Lead cumprimentava -> hook eterno | `_next_stage` so avanzava 1 step | FSM + Intent + Orchestrator |
| **WHATSMEOW_DB_URL ausente** | Listener nao resolvia LID -> telefone | env var nao configurada | Adicionar em `/etc/fralib/fralib.env` |
| **CRON_SECRET ausente** | 500 em /api/cron/followup-bryan | env var nao configurada | Adicionar em `/etc/fralib/fralib.env` |
| **Read-only fs** | Save dava Errno 30 | `ProtectSystem=full` no systemd | Override `ReadWritePaths` |
| **Audit log tenant_id=string** | 500 no audit | "dezigpi@gmail.com" como int | Query falha -> `_audit` trata silenciosamente |

---

## 7. Proximos passos (Tier 3 do roadmap)

Funcionalidades que **NAO foram entregues** (opcionais, alto esforço):

| Feature | Esforco | Por que ficou de fora |
|---|---|---|
| Chatwoot integration bidirecional | 2 semanas | Infra nao existe na VPS |
| Aprendizado continuo (fine-tune) | 2 semanas | Dataset ainda pequeno |
| Tool-use nativo JSON-schema | 2 dias | Tools deterministicas ja funcionam |
| Conversation replay / shadow mode | 3 dias | Requer infra de comparacao |
| A/B test com significance | 3 dias | Sem trafego suficiente ainda |
| Memory com embeddings (vector store) | 1 semana | Memoria atual e keyword-based |

**Recomendacao:** reavaliar daqui 3 meses quando o Franz tiver 1000+ leads
atendidos e dados suficientes pra treinar/otimizar.

---

## 8. Referencias

- `docs/FRANZ_SDR_ENTERPRISE_PLAN.md` - plano original (background)
- `docs/SDR_ROADMAP_3_QUICKWINS.md` - roadmap 10/10 (features 1-10)
- `docs/SDR_DIAGNOSTICO_COMPLETO.md` - diagnostico pre-FSM
- `scripts/test_sdr_fsm.py` - 35 testes de regressao
- `scripts/audit_vps_prod.py` - auditoria da VPS
- `scripts/conversation_real.py` - conversa simulada 8 turnos
- `scripts/audit_final_10.py` - auditoria final 10/10

### Commits relevantes

- `74819c5` - FSM + Intent + Orchestrator (bug do stage-loop corrigido)
- `a5ce7b1` - Memory 3-tier + Sliding window + Tracing basico
- `6b69ae6` - Tracing em todos os nodes + LLM-as-judge + Streaming SSE
- `2d11e56` - Fix `down_revision` em alembic (pre-requisito)

---

**Ultima atualizacao:** 2026-06-23. Score **10/10**.
**Proxima revisao sugerida:** 2026-09-23 (3 meses, ou quando leads > 1000).