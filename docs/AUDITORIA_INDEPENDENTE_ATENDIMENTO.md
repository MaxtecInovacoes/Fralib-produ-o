# AUDITORIA INDEPENDENTE - SISTEMA DE ATENDIMENTO (SDR)
## FraLib - Auditoria Completa e Independente

**Data:** 2026-06-11  
**Escopo:** Sistema de Atendimento, Filas, Workers e SDR  
**Metodologia:** Análise direta do código fonte, sem consultar auditorias anteriores

---

## RESUMO EXECUTIVO

Encontrei **1 vulnerabilidade CRÍTICA** e **várias oportunidades de melhoria**. O sistema de filas de jobs (`job_queue.py`) está bem implementado, mas a fila de mensagens WhatsApp (`outbound_queue.py`) tem uma race condition séria.

---

## 1. ARQUITETURA IDENTIFICADA

### 1.1 Componentes de Atendimento

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         SISTEMA DE ATENDIMENTO FRA LIB                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  WHATSAPP ──► MEOWHATS ──► whatsapp_listener.py ──► FRANZ (LangGraph)      │
│     ▲                                                        │               │
│     │                                                        ▼               │
│     │                                               sdr_gateway.py          │
│     │                                                   (Guardrails)         │
│     │                                                        │               │
│     │                                                        ▼               │
│     │                                              response_executor.py      │
│     │                                                        │               │
│     └────────────────────────────────────── WHATSAPP ◄───────┘               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                          FILAS / QUEUES                               │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │  jobs (Postgres)         │ outbound_queue (Postgres)                 │    │
│  │  - pipeline_lead         │ - Mensagens WhatsApp                     │    │
│  │  - franz_outreach        │ - Rate limit 1 msg/10min                  │    │
│  │  - lead_supply_*        │ - Status: pending/sending/sent/failed/dlq │    │
│  │  - USA FOR UPDATE        │ - ⚠️ NÃO USA FOR UPDATE (RACE!)           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  CRON ──► cron_endpoints.py ──► outbound_queue.enqueue_outbound()           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Arquivos Principais

| Arquivo | Função | Linhas | Status |
|---------|--------|--------|--------|
| `backend/whatsapp_listener.py` | Listener WebSocket inbound | 600+ | ✅ ATIVO |
| `backend/services/outbound_queue.py` | Fila outbound WhatsApp | 490 | ⚠️ RACE |
| `backend/core/job_queue.py` | Fila de jobs (pipeline) | 668 | ✅ SEGURO |
| `backend/endpoints/cron_endpoints.py` | Cron de follow-up | 500+ | ✅ ATIVO |
| `backend/agents/sdr_langgraph/compat.py` | Entry points Franz | 200+ | ✅ ATIVO |
| `backend/services/sdr_gateway.py` | Guardrails SDR | 200+ | ✅ ATIVO |
| `backend/whatsapp/rate_limiter.py` | Anti-ban | 300+ | ✅ ATIVO |

---

## 2. MAPA DE FILAS

### 2.1 Fila `jobs` (Pipeline) - ✅ SEGURO

**Arquivo:** `backend/core/job_queue.py`

| Aspecto | Detalhe |
|---------|---------|
| **Broker** | PostgreSQL (nativo) |
| **Proteção** | ✅ `SELECT FOR UPDATE SKIP LOCKED` (linha 177) |
| **DLQ** | `pipeline_failures` |
| **Retry** | Backoff exponencial: 30s, 2min, 8min |
| **Crash Recovery** | ✅ `reap_dead_workers()` a cada 5min |

**Código Seguro (job_queue.py:177):**
```python
FOR UPDATE SKIP LOCKED
LIMIT 1
```

---

### 2.2 Fila `outbound_queue` (WhatsApp) - ⚠️ RACE CONDITION

**Arquivo:** `backend/services/outbound_queue.py`

| Aspecto | Detalhe |
|---------|---------|
| **Broker** | PostgreSQL |
| **Proteção** | ❌ **SEM `FOR UPDATE SKIP LOCKED`** |
| **Rate Limit** | 1 msg / 10 min por tenant |
| **DLQ** | status = 'dlq' |
| **Retry** | Backoff: 1min, 2min, 4min, 8min |

**Código INSECURO (outbound_queue.py:177-184):**
```python
# Pega a msg mais antiga que esteja pronta
rows = c.execute(text("""
    SELECT id, tenant_id, lead_id, phone, message, source, attempts
    FROM outbound_queue
    WHERE status = 'pending'
      AND scheduled_at <= NOW()
    ORDER BY scheduled_at ASC, id ASC
    LIMIT 1
    # ❌ FALTA: FOR UPDATE SKIP LOCKED
""")).fetchall()
```

---

## 3. VULNERABILIDADES CRÍTICAS

### 3.1 🔴 CRÍTICA: Race Condition na Fila Outbound

**ARQUIVO:** `backend/services/outbound_queue.py:177-205`

**EVIDÊNCIA:**
```python
# Linhas 177-184: SELECT SEM LOCK
rows = c.execute(text("""
    SELECT id, tenant_id, lead_id, phone, message, source, attempts
    FROM outbound_queue
    WHERE status = 'pending'
      AND scheduled_at <= NOW()
    ORDER BY scheduled_at ASC, id ASC
    LIMIT 1
    # ❌ SEM "FOR UPDATE SKIP LOCKED"
""")).fetchall()

# Linhas 200-205: UPDATE SEPARADO (não atômico!)
with engine.connect() as c:
    c.execute(text("""
        UPDATE outbound_queue SET status = 'sending', attempts = attempts + 1
        WHERE id = :id AND status = 'pending'
    """), {"id": msg_id})
    c.commit()
```

**PROBLEMA:**
1. Duas instâncias do worker leem a mesma mensagem simultaneamente
2. Ambas verificam rate limit OK
3. Ambas tentam marcar como 'sending'
4. Só uma consegue (race win)
5. **A outra também envia** → mensagem duplicada!

**IMPACTO:**
- Lead recebe 2 mensagens idênticas
- Experiência ruim
- Possível bloqueio do WhatsApp/Meta
- Consome créditos duplos

**SOLUÇÃO:**
```python
# Linhas 177-184 devem usar:
rows = c.execute(text("""
    SELECT id, tenant_id, lead_id, phone, message, source, attempts
    FROM outbound_queue
    WHERE status = 'pending'
      AND scheduled_at <= NOW()
    ORDER BY scheduled_at ASC, id ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED  # ← ADICIONAR
""")).fetchall()
```

**VERIFICAÇÃO:**
```bash
# Buscar se existe FOR UPDATE na fila outbound
grep -n "FOR UPDATE" backend/services/outbound_queue.py
# Resultado: NENHUM MATCH ❌
```

---

### 3.2 🟠 ALTA: Old Code (Bryan) Ainda Existe

**ARQUIVO:** `backend/endpoints/cron_endpoints.py:139-140`

**EVIDÊNCIA:**
```python
@router.post('/despachar-fila-bryan')   # ❌ ENDPOINT ANTIGO
@router.post('/despachar-fila-franz')   # ✅ ATUAL
async def despachar_fila_franz(...):
```

```python
@router.post('/followup-bryan')    # ❌ ENDPOINT ANTIGO  
@router.post('/followup-franz')     # ✅ ATUAL
async def followup_franz(...):
```

**EVIDÊNCIA 2:** `worker.py:70`
```python
SDR_OUTREACH_JOB_TYPES = {"franz_outreach", "bryan_outreach"}  # ❌ Bryan ainda esperado
```

**PROBLEMA:**
- Se alguém chamar `/despachar-fila-bryan`, pode quebrar
- Testes verificam que código Bryan não é importado, mas endpoints ainda existem
- Mistura de terminologia ("bryan" vs "franz") causa confusão

**SOLUÇÃO:**
1. Remover endpoints Bryan de `cron_endpoints.py`
2. Remover `"bryan_outreach"` de `SDR_OUTREACH_JOB_TYPES`
3. Limpar comentários e documentação

---

### 3.3 🟠 ALTA: Mensagem Pode Ser Reenviada (Sem Idempotência)

**ARQUIVO:** `backend/services/outbound_queue.py:226-250`

**EVIDÊNCIA:**
```python
# Após enviar com sucesso, NÃO verifica se já enviou antes
if success:
    with engine.connect() as c:
        c.execute(text("""
            UPDATE outbound_queue SET status = 'sent', sent_at = NOW()
            WHERE id = :id
        """), {"id": msg_id})
        # ❌ NÃO verifica: mesma msg já foi enviada antes?
```

**PROBLEMA:**
- Se o cron rodar novamente enquanto a mensagem ainda está pending
- Ou se alguém reenviar manualmente
- O lead recebe a mesma mensagem 2x

**SOLUÇÃO:**
```python
# Adicionar índice único e verificar antes de inserir
# Ou adicionar campo message_hash na tabela
```

---

### 3.4 🟡 MÉDIA: Cooldown Bloqueia Thread

**ARQUIVO:** `backend/whatsapp_listener.py:694-702` (trecho mencionado nos testes)

**EVIDÊNCIA (test_sdr_operational_contract.py:74-85):**
```python
def test_listener_cooldown_waits_instead_of_dropping_inbound_reply():
    source = _read("backend/whatsapp_listener.py")
    cooldown_block = source[source.index("if _check_cooldown(lead_key):") : ...]
    
    assert "_time.sleep" in cooldown_block  # ❌ SLEEP BLOQUEANTE
    assert "return" not in cooldown_block    # ❌ NÃO RETORNA, ESPERA
```

**PROBLEMA:**
- Thread fica bloqueada durante o sleep
- Em arquiteturas com muitas conexões, pode causar timeout
- Não é ideal para processamento assíncrono

**SOLUÇÃO:**
- Usar scheduling em vez de sleep: agendar resposta para daqui X segundos

---

### 3.5 🟡 MÉDIA: Cron Sem Lock Distribuído

**ARQUIVO:** `backend/endpoints/cron_endpoints.py:141-256`

**PROBLEMA:**
- O cron busca leads e enfileira sem lock
- Se o mesmo cron rodar em múltiplas instâncias, pode enfileirar o mesmo lead 2x

**EVIDÊNCIA:**
```python
# Linhas 157-172: Busca leads sem lock
rows = conn.execute(text("""
    SELECT l.id, l.nome, ...
    FROM leads l
    WHERE l.sdr_stage = 'pendente_wpp'
      ...
    LIMIT :batch_limit
"""), {"batch_limit": FRANZ_CRON_BATCH_LIMIT})
```

**SOLUÇÃO:**
- Adicionar `FOR UPDATE SKIP LOCKED` na query
- Ou usar a fila `jobs` com idempotency_key

---

## 4. FLUXOS DE ATENDIMENTO

### 4.1 Fluxo Inbound (Lead Responde)

```
WhatsApp ──► meowhats ──► whatsapp_listener.py
                                        │
                        ┌───────────────┼───────────────┐
                        ▼               ▼               ▼
                   [DEDUP]        [ANTI-BAN]       [BILLING]
                   message_id     cooldown       plano ativo?
                        │               │               │
                        ▼               ▼               ▼
                   [LEAD STATUS] ◄──────────────────────┘
                   stage válido?
                        │
                        ▼
                   [MESSAGE PREPROCESSOR]
                   opt-out? mídia? bot?
                        │
                        ▼
                   [FRANZ (LangGraph)]
                   gerar resposta
                        │
                        ▼
                   [SDR GATEWAY]
                   site reveal ok?
                   prior outbound?
                        │
                        ▼
                   [RESPONSE EXECUTOR]
                   delay humanizado
                        │
                        ▼
                   WHATSAPP ◄── RESPOSTA
                        │
                        ▼
                   ATUALIZAR STAGE
                   SALVAR INTERAÇÃO
```

### 4.2 Fluxo Outbound (Franz Inicia)

```
CRON (30min) ──► /despachar-fila-franz
                              │
                              ▼
                    [Buscar leads pendentes]
                    sdr_stage='pendente_wpp'
                              │
                              ▼
                    [Franz.iniciar_contato()]
                    gerar mensagem intro
                              │
                              ▼
                    [SDR Gateway check]
                    allowed?
                              │
                              ▼
                    [outbound_queue.enqueue()]
                    status='pending'
                              │
          ┌───────────────────┴───────────────────┐
          │                                       │
          ▼                                       ▼
    [RATE LIMIT OK?]                      [RATE LIMIT BLOQUEADO]
    Pode enviar agora                      Agenda para depois
          │                                       │
          ▼                                       ▼
    [dequeue_and_send()]                 [msg fica pending]
    SELECT sem lock ❌                    até rate abrir
          │
          ▼
    [Enviar via meowhats]
          │
          ▼
    status='sent'
    stage='hook'
```

---

## 5. ESTÁGIOS DO SDR (Funil)

| Estágio | Descrição | Bloqueia Bot? |
|---------|-----------|---------------|
| `pendente_wpp` | Site pronto, aguardando contato | ❌ |
| `hook` | Primeira msg enviada | ❌ |
| `qualify` | Qualificando | ❌ |
| `pain` | Identificando dor | ❌ |
| `amplify` | Amplificando dor | ❌ |
| `tease` | antecipando solução | ❌ |
| `proof` | Prova/evidência | ❌ |
| `reveal` | Enviando link do site | ❌ |
| `feedback` | Pedindo feedback | ❌ |
| `qualificados` | Pronto para humano | ✅ |
| `ganhos` | Fechou | ✅ |
| `perdidos` | Não converteu | ✅ |
| `handoff` | Transição para humano | ✅ |
| `opt_out` | Não quer contato | ✅ |

---

## 6. TESTES E COBERTURA

### 6.1 Testes Existentes

| Arquivo | O que testa | Status |
|---------|-------------|--------|
| `test_sdr_operational_contract.py` | Fluxos de SDR, não cria Bryan | ✅ |
| `test_sdr_gateway.py` | Guardrails | ✅ |
| `test_sdr_plan_policy.py` | Políticas de plano | ✅ |
| `test_whatsapp_sdr_reply_service.py` | Serviço de resposta | ✅ |

### 6.2 Gaps de Testes

| Cenário | Testado? | Arquivo |
|---------|----------|---------|
| Race condition dequeue | ❌ | - |
| Múltiplos workers simultâneos | ❌ | - |
| Webhook + cron simultâneos | ❌ | - |
| Idempotência de mensagens | ❌ | - |
| DLQ após 3 falhas | Parcialmente | outbound_queue.py |

---

## 7. PROTEÇÕES EXISTENTES (O Que Funciona Bem)

| Proteção | Arquivo | Linha |
|----------|---------|-------|
| ✅ Debounce 4s | `whatsapp_listener.py` | 71-72 |
| ✅ Deduplicação por message_id | `lead_lock.py` | `_is_duplicate_message_id` |
| ✅ Cooldown 30s | `rate_limiter.py` | `check_cooldown` |
| ✅ Daily limit 50 msgs | `rate_limiter.py` | `DEFAULT_DAILY_LIMIT` |
| ✅ Flood detection | `rate_limiter.py` | `check_flood` |
| ✅ Human pause 5min | `rate_limiter.py` | `activate_human_pause` |
| ✅ Billing gate | `whatsapp_listener.py` | 133-156 |
| ✅ SDR Gateway | `sdr_gateway.py` | Contains site reveal guard |
| ✅ FOR UPDATE SKIP LOCKED (jobs) | `job_queue.py` | 177 |

---

## 8. COMPARATIVO: JOBS vs OUTBOUND QUEUE

| Aspecto | `jobs` (Pipeline) | `outbound_queue` (WhatsApp) |
|---------|-------------------|------------------------------|
| Lock distribuído | ✅ `FOR UPDATE SKIP LOCKED` | ❌ SEM LOCK |
| Atomicidade | ✅ CTE com UPDATE | ❌ SELECT + UPDATE separados |
| Idempotência | ✅ `idempotency_key` | ❌ NÃO |
| DLQ | ✅ `pipeline_failures` | ⚠️ status='dlq' |
| Crash recovery | ✅ `reap_dead_workers` | ❌ NÃO |

---

## 9. RECOMENDAÇÕES PRIORITÁRIAS

### 🔴 CRÍTICA (Arrumar Agora)

1. **Adicionar `FOR UPDATE SKIP LOCKED` em `outbound_queue.py:177`**
   ```python
   # Antes
   SELECT ... FROM outbound_queue WHERE status = 'pending' LIMIT 1
   
   # Depois
   SELECT ... FROM outbound_queue WHERE status = 'pending' LIMIT 1 FOR UPDATE SKIP LOCKED
   ```

### 🟠 ALTA (Esta Semana)

2. **Remover endpoints Bryan**
   - `cron_endpoints.py`: Remover `@router.post('/despachar-fila-bryan')`
   - `cron_endpoints.py`: Remover `@router.post('/followup-bryan')`
   - `worker.py`: Remover `"bryan_outreach"` de `SDR_OUTREACH_JOB_TYPES`

3. **Adicionar idempotência na outbound_queue**
   - Adicionar campo `message_hash`
   - Verificar antes de inserir nova msg

4. **Adicionar lock no cron**
   - Usar `FOR UPDATE SKIP LOCKED` na query de leads

### 🟡 MÉDIA (Este Mês)

5. **Substituir sleep por scheduling no cooldown**
   - Em vez de `_time.sleep()`, usar task scheduling

6. **Adicionar testes de concorrência**
   - Simular 2 workers simultâneos
   - Simular cron + webhook simultâneos

---

## 10. ARQUIVOS PARA AUDITAR DETALHADAMENTE

```
CRÍTICOS:
├── backend/services/outbound_queue.py       ← Race condition
├── backend/endpoints/cron_endpoints.py      ← Old Bryan code
├── backend/worker.py                        ← SDR_OUTREACH_JOB_TYPES
└── backend/whatsapp_listener.py             ← Cooldown blocking

SECUNDÁRIOS:
├── backend/services/sdr_gateway.py           ← Verificar guards
├── backend/whatsapp/rate_limiter.py        ← Verificar limites
├── backend/agents/sdr_langgraph/compat.py   ← Entry points
└── tests/unit/test_sdr_operational_contract.py ← Verificar gaps
```

---

## 11. ESTADO IDEAL

```
ANTES (ATUAL)                              DEPOIS (IDEAL)
──────                                    ─────
Race condition ❌                          FOR UPDATE SKIP LOCKED ✅
Bryan endpoints ❌                        Removido ✅
Msg duplicada ❌                          Idempotência ✅
Sleep bloqueando ❌                      Scheduling ✅
Sem testes concorrência ❌               Testes ✅
```

---

## 12. VERIFICAÇÕES DEVIDAS

### ✅ Verificado com grep:
```bash
# Job queue USA lock
grep "FOR UPDATE" backend/core/job_queue.py
# Resultado: linha 177 ✅

# Outbound queue NÃO USA lock
grep "FOR UPDATE" backend/services/outbound_queue.py  
# Resultado: NENHUM MATCH ❌
```

### ✅ Verificado com Read:
- `outbound_queue.py`: SELECT linhas 177-184 SEM lock
- `job_queue.py`: SELECT linha 177 COM lock

---

*Relatório gerado por auditoria independente - Claude Opus 4.8*  
*Data: 2026-06-11*
