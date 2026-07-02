# AUDITORIA FRALIB — Diagnóstico Consolidado

**Data:** 2026-07-02
**Escopo:** Provedores externos · Smoke test · Custos · Cérebro do Franz
**Modo:** read-only. Nenhum arquivo de produção foi alterado por esta auditoria.

---

## 1. TL;DR (linguagem de criança)

> "A Fralib tem 4 aviões voando juntos: WhatsApp, provedores de lead, IA e banco. O WhatsApp agora tem painel de saúde (Trilha A). Os outros 3 estão voando no escuro — não tem painel que diga 'esse avião tá com problema'. E o piloto automático (Franz) tem 3 bugs sérios: às vezes manda duas mensagens em sequência, às vezes esquece o que o cliente falou 3 minutos atrás, e às vezes ignora o FAQ que o dono da empresa cadastrou. Não é fatal — dá pra consertar."

---

## 2. O que FUNCIONA (não mexer)

### Trilha A — já no ar (167 testes passando)
- `phone_health_score` por tenant, score 0-100
- Auto-throttle dinâmico (score≥80→100%, <20→10%)
- Auto-pause quando score=0 (24h)
- Endpoint `/api/superadmin/phone-health` e `/api/admin/phone-health`
- Card no admin + tabela no superadmin
- `send_text_parts_with_health` com 10 padrões de erro whatsmeow

### Cérebro do Franz — partes sólidas
- **State tipado** `SDRState` (TypedDict) + `LeadMemory` (Pydantic) com 30+ campos — `backend/agents/sdr_langgraph/state.py`
- **FSM explícita** matriz `_TRANSITIONS` + `decide_transition()` — `state_machine.py:62-262`
- **Orchestrator** classifica intent via regex, detecta loop, decide state+stage — `orchestrator.py`
- **Intent classifier regex** determinístico (sem LLM por padrão) — `intent_classifier.py`
- **Opt-out 2-step** (pergunta → confirma) — `agent.py:976-1054`
- **Quality judge** (Haiku-as-judge) bloqueia envio se score < 3 — `agent.py:1242-1289`
- **Anti-duplicação 4 camadas inbound**: message_id, content-hash 5s, `wpp_lock_until` Postgres, lead_lock Redis — `whatsapp_listener.py:334-426`
- **Handoff humano** envia últimas 6 msgs + link wa.me — `whatsapp_listener.py:496-548`
- **Histórico de até 100 msgs** + sumarização com Haiku se >30 — `history_helper.py`
- **RAG semântico** (sentence-transformers OU TF-IDF 64d fallback) — `retrieval_semantico.py`
- **Learning passivo** persistido por tenant em JSON — `learning.py`

### Custos — ledger canônico
- `llm_budget_ledger` registra tokens+USD por chamada LLM (canônico)
- `llm_pricing.py` tem tabela de preços por modelo
- `provider_keys` + `provider_alerts` para circuit-breaker
- `jobs.llm_tokens_used/cost_estimate` agregado por job

---

## 3. O que TÁ QUEBRANDO — Top 10 Bugs

| # | Severidade | Bug | Arquivo:linha | Impacto | Esforço fix |
|---|---|---|---|---|---|
| **1** | 🔴 CRÍTICO | `build_sdr_system_prompt` é **código morto** — custom_knowledge do tenant (até 8000 chars) nunca chega ao Franz | `backend/services/sdr_settings.py:456-505` | Painel "Base de conhecimento" é placebo | 1-2h |
| **2** | 🔴 CRÍTICO | `history` recebido pelo listener é **perdido** no `node_load_context` (só lê LeadMemory do JSON, não o history injetado) | `backend/agents/sdr_langgraph/agent.py:258-360` | Franz esquece do turno 3-4 em diante | 2-4h |
| **3** | 🔴 CRÍTICO | Race condition outbound_queue × response_executor — worker cron NÃO chama `set_cooldown_fn` nem `increment_daily`, só `send_text_parts` direto | `backend/services/outbound_queue.py:60, 210-280` vs `backend/whatsapp/response_executor.py:113` | Mensagem duplicada quando inbound responde durante outbound cron | 1-2 dias |
| **4** | 🟠 ALTO | JSON do LLM vaza pro lead quando truncado por max_tokens — regex `looks_like_json` em `sdr_reply_service.py:46` é permissivo | `backend/whatsapp/sdr_reply_service.py:46` + `whatsapp_listener.py:972-994` | Lead recebe `{"resposta": "..."` no WhatsApp | 4h |
| **5** | 🟠 ALTO | llm_router NÃO chama `ia_manager.mark_success/failure` — health de keys desconectado do router real | `backend/services/llm_router.py:158-420` | Cooldown de keys não dispara quando falha de verdade | 4-6h |
| **6** | 🟠 ALTO | **Facebook Ads sem nenhum health check** — único provedor externo que falha em silêncio total | `backend/services/facebook_ads_service.py` inteiro | Budget estourando sem ninguém ver | 1 dia |
| **7** | 🟠 ALTO | **Tokens Facebook Ads hardcoded** no construtor (linha 18-19) — vazamento grave | `backend/services/facebook_ads_service.py:18-19` | Risco de segurança (token pode revogar) | 30min |
| **8** | 🟡 MÉDIO | Lock Redis fail-closed mas bypass existe — `whatsapp_listener.py:867-878` ignora `guard="redis_offline"` | `backend/agents/sdr_langgraph/compat.py:267-278` + `whatsapp_listener.py:867` | Quando Redis cai, multi-instâncias do listener podem processar msg em paralelo | 4h |
| **9** | 🟡 MÉDIO | llm_router NÃO tem hook de tracking — chamadas via `call_llm` direto (não `call_claude`) ficam invisíveis em `llm_budget_ledger` | `backend/services/llm_router.py:158-420` | Custo real subnotificado (até 30%) | 1 dia |
| **10** | 🟡 MÉDIO | Jina Reader (`jina_intelligence.py`) NÃO rastreia custo da chamada API — só cache hit/miss | `backend/utils/jina_intelligence.py:222` | Billing impreciso | 4h |

---

## 4. Schema do Banco Proposto (3 tabelas)

### 4.1 `provider_health` (unifica saúde de provedores)
```sql
CREATE TABLE IF NOT EXISTS provider_health (
    id BIGSERIAL PRIMARY KEY,
    provider VARCHAR(40) NOT NULL,  -- 'anthropic'|'openai'|'google'|'groq'|'facebook_ads'|'hunter'|'meowhats'|'gosom'
    endpoint VARCHAR(120),
    status VARCHAR(20) NOT NULL,    -- 'healthy'|'degraded'|'down'|'unknown'
    latency_p95_ms INTEGER,
    success_rate_24h NUMERIC(5,2),
    calls_24h INTEGER,
    errors_24h INTEGER,
    custo_dia_brl NUMERIC(14,4) DEFAULT 0,
    last_error TEXT,
    last_checked_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata_json JSONB DEFAULT '{}'::jsonb,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_health_provider ON provider_health (provider);
CREATE INDEX IF NOT EXISTS idx_provider_health_status ON provider_health (status, last_checked_at DESC);
```

### 4.2 `cost_events` (custo unificado multi-provider)
```sql
CREATE TABLE IF NOT EXISTS cost_events (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER,
    user_id INTEGER,
    job_id INTEGER,
    provider VARCHAR(50) NOT NULL,  -- 'anthropic'|'openai'|'facebook_ads'|'jina'|'hunter'|'whatsapp_waba'
    model VARCHAR(100),
    service VARCHAR(80),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    units INTEGER DEFAULT 1,
    latency_ms INTEGER,
    custo_usd NUMERIC(12,6) DEFAULT 0,
    custo_brl NUMERIC(14,4),
    cotacao_usd_brl NUMERIC(8,4) DEFAULT 5.65,
    status VARCHAR(30) DEFAULT 'success',
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    criado_em TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cost_events_tenant_time ON cost_events (tenant_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_cost_events_provider_time ON cost_events (provider, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_cost_events_metadata_gin ON cost_events USING GIN (metadata);
```

### 4.3 `lead_conversation_state` (state explícito do Franz)
```sql
CREATE TABLE IF NOT EXISTS lead_conversation_state (
    id BIGSERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL UNIQUE,
    tenant_id INTEGER NOT NULL,
    current_intent VARCHAR(40),
    current_stage VARCHAR(40),
    last_message_at TIMESTAMP,
    last_response_at TIMESTAMP,
    turn_count INTEGER DEFAULT 0,
    history_summary TEXT,
    sdr_turns_log JSONB DEFAULT '[]'::jsonb,  -- últimos N turnos
    language_state JSONB DEFAULT '{}'::jsonb,  -- idioma, tom, personalização aplicada
    atualizado_em TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_lcs_tenant ON lead_conversation_state (tenant_id);
CREATE INDEX IF NOT EXISTS idx_lcs_last_message ON lead_conversation_state (last_message_at DESC);
```

---

## 5. Plano de Implementação

### Fase 0 — Tela de Vidro (1 semana)

#### Sprint 0.1 — Painel de Provedores Externos (2-3 dias)
- **Migration:** `backend/migrations/2026_07_provider_health.sql` (tabela acima)
- **Backend:** `backend/services/provider_health_service.py` — `record_health(provider, status, latency_ms, error)` + `compute_all_providers()`
- **Endpoint:** `GET /api/superadmin/dashboard/providers` — retorna `v_provider_health_now`
- **Widget:** Card no superadmin.html com semáforo por provider
- **Cron:** a cada 5min, ping cada provider e upsert em `provider_health`
- **Inclui:** saúde do meowhats central (`whatsapp_listener.py` tem WS ping 30s)
- **Critério de pronto:** 5+ provedores com status em tempo real, alerta se amarelo >15min
- **Resolve:** item 7 do plano original (saúde do meowhats global)

#### Sprint 0.2 — Smoke Test Pós-Deploy (1 dia)
- **Arquivo:** `tools/smoke_test.py`
- **Endpoints testados:** 8-12 críticos:
  - `GET /api/health`
  - `POST /api/auth/login`
  - `GET /api/admin/services` (autenticado)
  - `GET /api/superadmin/dashboard/overview` (autenticado)
  - `POST /api/cron/compute-phone-health-score`
  - `GET http://127.0.0.1:3001/health` (meowhats)
  - DB ping (`SELECT 1`)
  - LLM ping (claude-haiku com "ok")
- **Exit code 0/1 CI-friendly**
- **Integração:** step em `deploy.yml` (systemd + git push prod)
- **Critério de pronto:** 8+ endpoints validados, <30s execução

#### Sprint 0.3 — Dashboard de Custos (2 dias)
- **Migration:** `backend/migrations/2026_07_cost_events.sql` (tabela acima)
- **Backend:** `backend/agents/cost_tracker.py` — `record_cost_event(...)` fail-safe
- **Wrapper:** instrumentar `backend/services/llm_router.py:call_llm` para chamar `record_cost_event`
- **Cron diário:** agrega spend Facebook Ads via `get_overall_insights(1)` → `cost_events`
- **Cron diário:** refresh cotação USD/BRL via API pública
- **Endpoint:** `GET /api/superadmin/dashboard/cost-events` (já existe `costs`, só adicionar `cost_events`)
- **Widget:** card com breakdown por provider, alerta se >80% budget mensal
- **Fix crítico:** remover tokens hardcoded de `facebook_ads_service.py:18-19` → `app_settings` ou env
- **Critério de pronto:** todos provedores instrumentados, totalização mensal, alerta funcional

### Fase 1 — Corrigir Franz (2-3 semanas)

#### Sprint 1.1 — Janela de Simulação no Admin (2-3 dias)
- **Card:** `frontend/admin.html` → seção "🧪 Simulador Franz"
- **Endpoint:** `POST /api/admin/simulate` — recebe `{tenant_id, message, history}`, monta prompt igual runtime (reutiliza `build_sdr_system_prompt` corrigido), retorna `{response, intent, stage_after, kanban_action, rules_applied}`
- **Tabela:** `sdr_simulations (id, tenant_id, message, response, intent, stage_after, kanban_action, criado_em)`
- **UI:** textarea + botão "Testar", mostra resposta + ação no kanban + regras aplicadas
- **Histórico:** últimas 10 simulações
- **Critério de pronto:** admin digita, vê resposta em <5s, vê ação no kanban
- **POR QUE PRIMEIRO:** sem simulador, qualquer mudança no Franz vira "tiro no escuro"

#### Sprint 1.2 — Corrigir Top 3 Bugs do Franz (3-5 dias)

**Bug #1 — custom_knowledge morto:**
- Modificar `backend/agents/sdr_langgraph/agent.py:554-559` (montagem do system prompt) para chamar `build_sdr_system_prompt(persona_text, settings)` ao invés de só `get_persona_text`
- Injetar `custom_knowledge` (até 3500 chars runtime) entre persona_text e agent_system_overlay
- Teste: cadastrar "Trabalho só com clínicas em SP" no painel → Franz responde "Entendi, atendo clínicas em SP"

**Bug #2 — history perdido:**
- Modificar `node_load_context` (`agent.py:258-360`) para ler `state.get("history", [])` ANTES de montar `LeadMemory`
- Manter fallback para LeadMemory do JSON quando history não vem
- Teste: turno 3-4, Franz cita o que o lead disse no turno 1

**Bug #3 — race condition outbound×inbound:**
- Modificar `backend/services/outbound_queue.py:260-303` para passar por um wrapper que:
  1. Consulta `leads.last_outbound_at` antes de enviar
  2. Se `last_inbound > last_outbound`, **aborta** (já responderam)
  3. Chama `set_cooldown_fn(lead_key)` antes de enviar
  4. Chama `increment_daily_count(tenant_id, lead_id)` após sucesso
- Adicionar lock Redis também no `cron_endpoints.py:iniciar_contato` (não só `responder_lead`)
- Teste de stress: 100 msgs paralelas pro mesmo lead → 100 envios, 0 duplicação

#### Sprint 1.3 — UI de Personalização (2-3 dias)
- **Seção:** "🤖 Configurar Franz" no `admin.html`
- **Tabs:** Básico / Avançado / Base de conhecimento
- **Cada campo com toggle "Personalizar"** — quando off, usa nativo
- **Preview em tempo real** do system prompt montado
- **Botão "Testar no simulador"** — integra com Sprint 1.1
- **Botão "Restaurar nativo"** por campo
- **Granularidade:** só nome / personalidade / total
- **Critério de pronto:** tenant muda nome e vê no simulador, ativa/desativa cada seção sem quebrar

#### Sprint 1.4 — Orquestração KPI entre Agentes (5-7 dias)
- **Migration:** `backend/migrations/2026_07_lead_outcomes.sql`
  - `lead_outcomes (id, tenant_id, nicho, horario_contato, abordagem_usada, site_template, kanban_stage_final, dias_ate_fechamento, criado_em)`
  - `sdr_kpi_aggregated (id, nicho, metrica, valor, periodo, sample_size, atualizado_em)`
- **Hook:** quando lead muda para `sdr_stage='ganho'` ou `'perdido'` → INSERT em `lead_outcomes`
- **Cron:** `aggregate_sdr_kpis.py` diário → `sdr_kpi_aggregated`
- **Agentes leitores:**
  - `outbound_scheduler` lê `melhor_horario_por_nicho` antes de mandar
  - `prompt_selector` lê `abordagem_melhor_por_nicho` antes de gerar
  - `site_generator` lê `site_template_melhor_por_nicho` antes de render
- **Critério de pronto:** 3+ tenants com >30 leads cada → sistema passa a aprender nichos/horários automaticamente

#### Sprint 1.5 — Race Condition Hardening + Transparência (3-4 dias)
- **Resolução completa:** worker outbound consulta `leads.last_inbound_at` antes de cada envio
- **Lock distribuído:** cron também wrapped em `_lead_lock_guard` (mesmo padrão de `responder_lead`)
- **Transparência pro lead:** quando listener detecta estado `cooldown/paused/handoff` → enfileira msg curta de status ANTES de silenciar
- **Tabela:** `sdr_turns (id, lead_id, stage_before, stage_after, intent, confidence, latency_ms, llm_cost_usd, criado_em)` para auditoria de turnos
- **Critério de pronto:** lead em cooldown recebe "Já te respondo em 5 min, tá?"

---

## 6. Estimativa Consolidada

| Sprint | Dias | Valor | Dependência |
|---|---|---|---|
| 0.1 — Painel Provedores | 2-3 | Alto | nenhuma |
| 0.2 — Smoke Test | 1 | Alto | nenhuma |
| 0.3 — Dashboard Custos | 2 | Alto | nenhuma |
| 1.1 — Simulador | 2-3 | **Crítico** | nenhuma (vem primeiro) |
| 1.2 — Top 3 Bugs Franz | 3-5 | **Crítico** | nenhuma (vem segundo) |
| 1.3 — UI Personalização | 2-3 | Médio | 1.2 (precisa `custom_knowledge` funcionar) |
| 1.4 — KPI Orquestração | 5-7 | Médio | nenhuma |
| 1.5 — Race + Transparência | 3-4 | Médio | 1.2 (precisa estado do Franz estabilizado) |
| **TOTAL Fase 0+1** | **~20-28 dias úteis (4-5 semanas)** | | |

---

## 7. Riscos e Dependências

| Risco | Mitigação |
|---|---|
| Mudança no system prompt do Franz pode quebrar tenants ativos | Simulador (1.1) ANTES de mudar prompt permite testar |
| Race condition fix pode afetar outbound cron em produção | Feature flag `outbound_lock_check_enabled` para rollout gradual |
| Token FB Ads hardcoded pode revogar se mudarmos | Mover para env primeiro, depois `app_settings` |
| Redis fail-closed pode bloquear 100% das mensagens | Já existe fallback Postgres `wpp_lock_until` (30s TTL) |
| Sprint 1.4 (KPI) precisa de dados históricos | Backfill de `lead_outcomes` dos últimos 90 dias via job noturno |

---

## 8. Recomendação de Execução (esta noite)

Sequência autônoma com **ECC loop + testes verdes como gate**:

1. **Sprint 0.1** (provedores) — testes primeiro, implementação depois
2. **Sprint 0.2** (smoke test) — script + 5 testes pytest
3. **Sprint 0.3** (custos) — migration + cost_tracker + 8 testes
4. **Sprint 1.1** (simulador) — endpoint + UI + 6 testes
5. **Sprint 1.2** (Top 3 bugs) — 3 fixes + 10 testes (incluindo teste de stress race condition)
6. **Sprint 1.5** (race + transparência) — extends 1.2
7. **Sprint 1.3** (UI personalização) — depois de 1.2 funcionar
8. **Sprint 1.4** (KPI) — independente, roda em paralelo

**Critério de parada:** tudo verde nos 167 testes existentes + 50+ testes novos = ~220 testes passando.

**Onde pode travar:** se algum teste crítico do Franz existente quebrar com as mudanças de system prompt → volta e adapta, não avança.

---

## 9. Glossário (pra acordar e revisar)

- **ECC loop:** Edit-Check-Cycle — Claude faz mudanças, roda testes, se vermelho corrige, repete até verde
- **FSM:** Finite State Machine — Franz tem matriz de transições explícitas
- **Anti-duplicação 4 camadas:** message_id + content-hash + wpp_lock (Postgres) + lead_lock (Redis)
- **sdr_stage:** coluna na tabela `leads` que diz em que coluna do Kanban o lead tá (intro/hook/followup/etc)
- **custom_knowledge:** texto de até 8000 chars que tenant cadastra como FAQ do negócio
- **build_sdr_system_prompt:** função que monta o system prompt, hoje é código morto (BUG #1)
- **last_outbound/last_inbound:** timestamps que dizem quem falou por último (lead ou bot) — chave pro anti-loop

---

**Fim da auditoria. Próximo passo: execução autônoma das Sprints 0.1 → 1.5 com gate de testes verdes.**