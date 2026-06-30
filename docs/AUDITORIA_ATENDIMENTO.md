# AUDITORIA DE ATENDIMENTO - FRALIB

## Resumo Executivo

O sistema de atendimento da fralib é baseado em **WhatsApp + SDR automatizado (Franz)** com uma arquitetura de filas em PostgreSQL. O objetivo é qualificar leads e fechar vendas de forma automatizada.

---

## 1. MAPA DE SISTEMAS E ARQUITETURA

### 1.1 Componentes de Atendimento

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRALIB - ATENDIMENTO                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐      ┌──────────────────────┐
│   WHATSAPP LISTENER  │      │   WHATSAPP OUTBOUND  │
│  (whatsapp_listener) │◄────►│   (outbound_queue)   │
└──────────┬───────────┘      └──────────┬───────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐      ┌──────────────────────┐
│   MESSAGE PROCESSOR  │      │   MEOWHATS API       │
│ (message_preprocess) │      │   (localhost:3001)   │
└──────────┬───────────┘      └──────────────────────┘
           │
           ▼
┌──────────────────────┐
│    FRANZ (SDR)      │
│  (sdr_langgraph)     │
└──────────┬───────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐  ┌─────────┐
│ HOOK    │  │ QUALIFY │
│ PAIN    │  │ AMPLIFY │
│ TEASE   │  │ PROOF   │
│ REVEAL  │  │ CLOSE   │
└─────────┘  └─────────┘
```

### 1.2 Arquivos Principais

| Arquivo | Função | Status |
|---------|--------|--------|
| `backend/whatsapp_listener.py` | Listener WebSocket (inbound) | ✅ ATIVO |
| `backend/services/outbound_queue.py` | Fila outbound | ✅ ATIVO |
| `backend/agents/sdr_langgraph/` | Agente Franz (LangGraph) | ✅ ATIVO |
| `backend/endpoints/cron_endpoints.py` | Cron de follow-up | ✅ ATIVO |
| `backend/services/sdr_gateway.py` | Guardrails | ✅ ATIVO |
| `backend/whatsapp/rate_limiter.py` | Anti-ban | ✅ ATIVO |
| `backend/services/closer_queue.py` | Handoff para humanos | ✅ ATIVO |
| `backend/services/whatsapp_automation_service.py` | Sequência 7 dias | ✅ ATIVO |

---

## 2. FLUXO DE ATENDIMENTO (CAMINHO FELIZ)

### 2.1 Quando o Cliente Envia Mensagem (INBOUND)

```
WhatsApp ──► meowhats WebSocket ──► whatsapp_listener.py
                                              │
                                    ┌─────────┴─────────┐
                                    ▼                   ▼
                              [DEDUP]           [ANTI-BAN]
                              - message_id      - 30s cooldown
                              - content hash    - 50 msgs/dia
                                    │           - flood detection
                                    ▼                   │
                              [BILLING GATE]◄──────────┘
                                    │
                                    ▼
                              [LEAD STATUS]
                              - stage válido?
                              - não é terminal?
                                    │
                                    ▼
                              [MESSAGE PREPROCESSOR]
                              - Regex (opt-out)
                              - Heurísticas
                              - LLM (Haiku)
                                    │
                                    ▼
                              [FRANZ (LangGraph)]
                              - Detecta intent
                              - Gera resposta
                              - Atualiza stage
                                    │
                                    ▼
                              [SDR GUARD]
                              - Contaminação?
                              - Site reveal ok?
                                    │
                                    ▼
                              [RESPONSE EXECUTOR]
                              - Delay humanizado
                              - Envia msg
                              - Persiste interação
                                    │
                                    ▼
                              WhatsApp ◄── RESPOSTA
```

### 2.2 Quando o Sistema Inicia (OUTBOUND)

```
CRON (a cada 30min) ──► /despachar-fila-franz
                                    │
                                    ▼
                        [Busca leads pendentes]
                        sdr_stage = 'pendente_wpp'
                        status = 'concluido'
                                    │
                                    ▼
                        [Franz.iniciar_contato()]
                        - Gera mensagem intro
                        - Escolhe variante A/B
                                    │
                                    ▼
                        [SDR Guard check]
                                    │
                                    ▼
                        [outbound_queue.enqueue()]
                                    │
                                    ▼
                        [outbound_queue.pending]
                                    │
                                    ▼
                        [Worker processa (30s)]
                        - Rate limit: 1 msg/10min
                        - Envia via meowhats
                                    │
                                    ▼
                        lead.sdr_stage = 'hook'
                        [interacoes] ← log
```

### 2.3 Fluxo de Follow-up

```
CRON (a cada 1h) ──► /followup-franz
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
            [FU1: 24h sem resposta]    [FU2: 72h sem resposta FU1]
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
                          [Escolhe template FU]
                          - FOLLOWUP_1
                          - FOLLOWUP_2
                          - FOLLOWUP_3
                                  │
                                  ▼
                          [Franz.followup()]
                          [enqueue_outbound()]
                                  │
                                  ▼
                    24h sem resposta FU2 ──► sdr_stage = 'perdidos'
```

---

## 3. FILAS E WORKERS

### 3.1 Tabela de Filas

| # | Nome | Tipo | Producer | Consumer | DLQ |
|---|------|------|----------|----------|-----|
| 1 | `jobs` (pipeline) | Postgres | API, Pipeline | `worker.py` | `pipeline_failures` |
| 2 | `jobs` (franz_outreach) | Postgres | Pipeline, Cron | `worker.py` | `pipeline_failures` |
| 3 | `jobs` (lead_supply) | Postgres | Watchdog | `worker.py` | N/A |
| 4 | `outbound_queue` | Postgres | Worker, Cron | `worker.py` | status='dlq' |
| 5 | `closer_queue` | Postgres | SDR | Frontend | N/A |
| 6 | `AgentBus` | In-Memory | Agentes | Agentes | N/A |

### 3.2 Fluxo de Filas

```
                    JOBS QUEUE (Postgres)
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
       [pipeline]    [franz_out]   [lead_supply]
            │            │            │
            ▼            ▼            ▼
        WORKER      WORKER       WORKER
        (Job 1)     (Job 2)      (Job 3)
            │            │            │
            └────────────┼────────────┘
                         │
                         ▼
              OUTBOUND_QUEUE (WhatsApp)
                         │
                         ▼
            ┌────────────────────────┐
            │   PROCESSAMENTO       │
            │   Rate limit 1/10min   │
            └────────────────────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
       [ENVIADO]                  [DLQ]
       sdr_stage='hook'         3 retries fail
```

---

## 4. VULNERABILIDADES CRÍTICAS

### 4.1 🔴 CRÍTICA: Race Condition no Dequeue

**ARQUIVO:** `backend/services/outbound_queue.py:177-205`

**PROBLEMA:**
```python
# Linhas 177-184 - SELECT SEM LOCK
rows = c.execute(text("""
    SELECT id, tenant_id, lead_id, phone, message, source, attempts
    FROM outbound_queue
    WHERE status = 'pending'
      AND scheduled_at <= NOW()
    ORDER BY scheduled_at ASC, id ASC
    LIMIT 1
""")).fetchall()
```

O SELECT não usa `SELECT FOR UPDATE SKIP LOCKED`. Se duas instâncias do worker rodarem simultaneamente, ambas podem pegar a MESMA mensagem e enviar DUAS VEZES.

**IMPACTO:** Mensagem duplicada ao lead, possível bloqueio do WhatsApp.

**SOLUÇÃO:**
```python
rows = c.execute(text("""
    SELECT id, tenant_id, lead_id, phone, message, source, attempts
    FROM outbound_queue
    WHERE status = 'pending'
      AND scheduled_at <= NOW()
    ORDER BY scheduled_at ASC, id ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
""")).fetchall()
```

---

### 4.2 🟠 ALTA: Race Condition entre Webhook e Cron

**ARQUIVOS:**
- `backend/whatsapp_listener.py:615-654`
- `backend/endpoints/cron_endpoints.py:259-546`

**PROBLEMA:**
```
1. Lead responde via WhatsApp → Listener processa → stage avança para 'qualify'
2. Cron followup_franz executa simultaneamente → encontra lead com stage antigo
3. Duas mensagens enviadas em sequência rápida
```

O listener tem `wpp_lock_until` mas o cron NÃO tem lock equivalente.

**IMPACTO:** Duas mensagens seguidas, experiência ruim para lead.

---

### 4.3 🟠 ALTA: Mensagem Pode Ser Consumida Múltiplas Vezes

**ARQUIVO:** `backend/services/outbound_queue.py:226-250`

**PROBLEMA:** Após sucesso no envio, não há verificação se a mesma mensagem já foi enviada antes para o mesmo lead. Um retry manual ou duplicação no cron pode reenviar.

**SOLUÇÃO:** Adicionar idempotency key na tabela: `UNIQUE(lead_id, message_hash)`

---

### 4.4 🟡 MÉDIA: Old Code Residual

**ENCONTRADO:**
- `backend/agents/langgraph_backup/` - Pasta com código antigo
- `bryan.py` mencionado em comentários
- Endpoints duplicados: `/despachar-fila-bryan` e `/despachar-fila-franz`

**PROBLEMA:** Se variáveis de ambiente mudarem ou houver fallback incorreto, código antigo pode ser ativado.

**SOLUÇÃO:** Remover código em `langgraph_backup/` ou adicionar verificação de versão ativa.

---

### 4.5 🟡 MÉDIA: Cooldown Blocking

**ARQUIVO:** `backend/whatsapp_listener.py:694-702`

**PROBLEMA:**
```python
if remaining > 0:
    _time.sleep(min(remaining, _cooldown_seconds_for_key(lead_key)))
```

O sleep inline bloqueia a thread. Em arquiteturas com múltiplas conexões, isso pode causar timeout.

**SOLUÇÃO:** Usar task scheduling em vez de sleep.

---

### 4.6 🟢 BAIXA: Falta Testes de Concorrência

**ARQUIVO:** `tests/unit/test_sdr_operational_contract.py`

**PROBLEMA:** Não há testes que simulem:
- Duas instâncias processando fila simultaneamente
- Retry de mensagem após sucesso no DB
- Webhook recebido enquanto cron está enviando

---

### 4.7 🟢 BAIXA: Falta Versionamento

**PROBLEMA:** Não há endpoint ou logging que exiba qual versão do código SDR está ativa. Dificulta troubleshooting.

---

## 5. VERDADES ANTIGAS E CAMINHOS ALTERNATIVOS

### 5.1 Bryan vs Franz

| Aspecto | Bryan (ANTIGO) | Franz (NOVO) |
|---------|----------------|--------------|
| Status | DEPRECADO | ATIVO |
| Arquivo | Não existe mais | `agents/sdr_langgraph/` |
| Entry point | `responder_lead_bryan()` | `responder_lead()` |
| Cron endpoint | `/despachar-fila-bryan` | `/despachar-fila-franz` |
| Teste | `test_active_sdr_paths_do_not_create_bryan_runtime` | N/A |

**VERIFICAÇÃO:** O código Bryan foi removido, mas os endpoints antigos ainda existem em `cron_endpoints.py`.

---

### 5.2 Caminhos Não Documentados

| Caminho | Arquivo | Descrição |
|---------|---------|-----------|
| Queue direta | `outbound_queue.py` | Rate limit 1 msg/10min |
| Automation 7 dias | `whatsapp_automation_service.py` | Sequência day 1-7 |
| Disparo manual | `whatsapp_disparo_endpoints.py` | Templates por admin |
| Closer humano | `closer_queue.py` | Handoff stage 'qualificados' |

---

### 5.3 Stages Bloqueantes

O bot PARA de responder quando lead está em:
```python
BLOCKED_STAGES = ('qualificados', 'ganhos', 'perdidos', 'handoff')
```

Isso significa que se o lead avançar para esses stages, o bot ignora mensagens.

---

## 6. PONTOS DE FALHA E GARGALOS

### 6.1 Gargalos Conhecidos

| Gargalo | Local | Impacto | Solução |
|---------|-------|---------|---------|
| **MAX_PIPELINES_GLOBAL=4** | `job_queue.py:37` | Limita throughput | Aumentar para 8-16 |
| **Rate limit 1 msg/10min** | `outbound_queue.py:26` | WhatsApp lento | Reduzir para 1/5min |
| **Worker morre mid-job** | `worker.py` | Job fica "running" | `reap_dead_workers()` |
| **MEOWHATS indisponível** | API externa | Msgs pending | Retry com backoff |

### 6.2 Alertas Monitorados

```python
# Em outbound_queue.py
backlog_alert: outbound_queue.pending > 100
dlq_alert: outbound_queue.dlq > 10
oldest_pending_minutes: msg pendentes > X min
reaper: Worker recovery
franz_reconcile: Jobs sem contato
```

---

## 7. ESTADO IDEAL DO ATENDIMENTO

### 7.1 O que funciona bem ✅

1. **Debounce e Anti-ban:** 4s buffer, deduplicação por message_id, cooldown 30s
2. **Rate limiting:** 1 msg/10min por tenant protege contra bloqueio
3. **DLQ:** Mensagens falhadas vão para DLQ, não perdem
4. **Human takeover:** Se humano envia msg, bot pausa 5min
5. **Billing gate:** SDR só ativa se plano permite
6. **Stage gating:** Stages bloqueantes param o bot

### 7.2 O que precisa melhorar ⚠️

1. **Race condition no dequeue:** Pode enviar duplicado
2. **Race webhook vs cron:** Pode enviar 2 msgs seguidas
3. **Idempotência:** Mesma msg pode ser reenviada
4. **Old code:** Endpoints Bryan ainda existem
5. **Cooldown blocking:** Sleep inline em vez de scheduling
6. **Testes:** Falta testes de concorrência

### 7.3 Estado Ideal

```
┌─────────────────────────────────────────────────────────────────┐
│                    ESTADO IDEAL                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. RACE CONDITION RESOLVIDA                                  │
│     - SELECT FOR UPDATE SKIP LOCKED                            │
│     - Lock distribuído Redis no cron                            │
│                                                                 │
│  2. IDEMPOTÊNCIA                                               │
│     - UNIQUE(lead_id, message_hash) na outbound_queue          │
│     - Ou: check em memória antes de enviar                      │
│                                                                 │
│  3. OLD CODE REMOVIDO                                          │
│     - Remover /despachar-fila-bryan                            │
│     - Remover /followup-bryan                                  │
│     - Remover langgraph_backup/                                │
│                                                                 │
│  4. SCHEDULING EM VEZ DE SLEEP                                │
│     - Cooldown agenda resposta para depois                      │
│     - Não bloqueia thread                                       │
│                                                                 │
│  5. TESTES DE CONCORRÊNCIA                                     │
│     - Simular 2 workers simultâneos                            │
│     - Simular webhook + cron simultâneos                       │
│                                                                 │
│  6. MONITORAMENTO                                              │
│     - Dashboard de filas em tempo real                         │
│     - Alertas de DLQ > 5                                       │
│     - Métricas de FRT (First Response Time)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. RECOMENDAÇÕES PRIORITÁRIAS

### 🔴 Imediato (Crítico)

1. **Adicionar `FOR UPDATE SKIP LOCKED`** em `outbound_queue.py:177`
2. **Adicionar idempotency key** na tabela `outbound_queue`

### 🟠 Esta Semana (Alto)

3. **Adicionar lock no cron** antes de processar lead
4. **Remover endpoints Bryan** de `cron_endpoints.py`

### 🟡 Este Mês (Médio)

5. **Substituir sleep por scheduling** no cooldown
6. **Adicionar testes de concorrência**

### 🟢 Melhoria Contínua

7. **Remover `langgraph_backup/`**
8. **Adicionar health check de versão**

---

## 9. ARQUIVOS PARA AUDITAR

### 9.1 Críticos (Verificar Agora)

```
backend/services/outbound_queue.py      ← Race condition
backend/whatsapp_listener.py            ← Race webhook vs cron
backend/endpoints/cron_endpoints.py    ← Old code Bryan
backend/agents/sdr_langgraph/          ← Verificar entry points
```

### 9.2 Secundários

```
backend/core/job_queue.py              ← MAX_PIPELINES_GLOBAL
backend/worker.py                      ← Reaper de jobs
backend/services/sdr_gateway.py        ← Guardrails
tests/unit/test_sdr_operational_contract.py  ← Cobertura
```

---

*Relatório gerado em: 2026-06-11*
*Auditor: Claude Opus 4.8*
