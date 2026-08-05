# FraLib — Arquitetura

Visão geral do sistema, stack, containers Docker, fluxo de dados e padrões arquiteturais.

---

## 1. Stack

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Backend | Python 3.11 + FastAPI | — |
| Frontend | HTML5 + vanilla JavaScript | — |
| Banco | PostgreSQL 16 | Alpine |
| Cache | Redis 7 | Alpine |
| Worker | Python (mesmo código do app) | — |
| Geração HTML | OpenUI (Node.js 22) | Systemd host |
| Deploy | Docker Compose + Nginx | — |

### Bibliotecas Python Principais

- **SQLAlchemy 2.x** — ORM + raw SQL (`text()`)
- **Alembic** — migrations versionadas
- **JWT (PyJWT)** — autenticação stateless
- **SlowAPI** — rate limiting (limiter + decorators)
- **Playwright** — scraping headless (Hunter)
- **python-dotenv** — variáveis de ambiente
- **psycopg2** — driver PostgreSQL

---

## 2. Containers Docker

```
┌──────────────────────────────────────────────────────────┐
│  Host: 100.124.56.36 (VPS)                                │
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  postgres   │  │    redis    │  │   openui    │     │
│  │  :15434     │  │  :16379     │  │  :3333      │     │
│  │  Alpine 16  │  │  Alpine 7   │  │  Node 22    │     │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘     │
│         │                │                                │
│  ┌──────┴────────────────┴──────────┐                    │
│  │           fralib-app              │                    │
│  │        :8001 → :8000             │                    │
│  │   FastAPI + todos os routers     │                    │
│  │   21 routers, lifespan hooks      │                    │
│  │   CORS, security headers, SSE     │                    │
│  └───────────┬──────────────────────┘                    │
│              │                                           │
│  ┌───────────┴──────────────────────┐                    │
│  │         worker                   │                    │
│  │   Consome fila Postgres          │                    │
│  │   Pipeline + supply + Franz      │                    │
│  │   WORKER_JOB_TYPES env           │                    │
│  └──────────────────────────────────┘                    │
│                                                           │
│  Nginx (host)                                             │
│  └── /var/www/fralib/sites/ → sites publicados            │
│  └── app.seunegociofralib.site → proxy → :8001           │
└──────────────────────────────────────────────────────────┘
```

### Volumes

| Volume | Uso | Persistência |
|--------|-----|-------------|
| `fralib_fralib-postgres` | Dados Postgres (external) | Permanente |
| `fralib-redis` | Cache Redis | Docker-managed |
| `fralib-sites` | Sites publicados | Docker-managed |
| `fralib-logs` | Logs do app/worker | Docker-managed |
| `fralib-builder` | Sandbox do Builder | Docker-managed |

### Portas Expostas

| Container | Porta | Acesso |
|-----------|-------|--------|
| postgres | 15434 | Host 127.0.0.1 |
| redis | 16379 | Host 127.0.0.1 |
| app | 8001 | Público (via Nginx) |
| worker | — | Interno |
| openui | 3333 | Host 127.0.0.1 |

---

## 3. Arquitetura do Código

```
C:\fralib/
├── server.py                    # Entrypoint — FastAPI app + lifespan
├── worker.py                    # Entrypoint — Worker daemon
├── Dockerfile                   # Build: Node 22 + Python venv
├── docker-compose.prod.yml      # Orquestração 4 containers
├── alembic.ini                  # Config Alembic
├── alembic/                     # Migrations versionadas
├── backend/
│   ├── core/                    # Infra: database, auth, queue, rate_limit
│   ├── services/                # Business logic: llm_router, ia_manager, credits
│   ├── agents/                  # IA agents (pipeline + suporte)
│   │   ├── _arquivo/            # Agentes legados (arquivados)
│   │   ├── manager/             # Pipeline state machine
│   │   └── builder/             # OpenUI HTML generator
│   │       └── quality_gate_v2/ # Vision QA v2
│   ├── endpoints/               # 21 FastAPI routers
│   ├── utils/                   # Scrapers, crypto, passwords
│   └── agent_router.py          # Dynamic model routing (complexidade)
├── frontend/                    # HTML + vanilla JS
│   ├── build.py                 # Concatena partials → HTML
│   ├── partials/                # Componentes HTML parciais
│   └── js/                      # Módulos JavaScript
├── docs/                        # Documentação
├── tests/                       # pytest (unit + integration + e2e)
│   ├── unit/                    # Testes unitários
│   ├── integration/             # Testes de API + DB
│   └── e2e/                     # Testes end-to-end (Playwright)
└── logs/                        # Logs locais (não versionado)
```

---

## 4. Fluxo de Dados — Pipeline de Geração

```
Cliente → frontend → API (pipeline_endpoints) → Fila Postgres
                                                        │
                                                  worker.py
                                                  claim_next()
                                                        │
                                              ┌─────────▼──────────┐
                                              │  Pipeline State    │
                                              │  Machine (FSM)     │
                                              └─────────┬──────────┘
                                                        │
                        ┌───────────────┬───────────────┼───────────────┬──────────────┐
                        │               │               │               │              │
                   [1] BANCO      [2] HUNTER      [3] CAIO    [4] ARQUITETO  [5] BUILDER
                   carrega lead   scraping        qualifica    PRD + design   OpenUI HTML
                   do Postgres    Google Maps     tier/score   paleta OKLch    chunked 4x
                        │               │               │               │              │
                        └───────────────┴───────────────┴───────────────┴──────────────┘
                                                        │
                                              ┌─────────▼──────────┐
                                              │  QA v2 (Vision LLM)│
                                              │  Score ≥ 7.5 PASS  │
                                              └─────────┬──────────┘
                                                        │
                                              ┌─────────▼──────────┐
                                              │  DEPLOY            │
                                              │  /var/www/fralib/   │
                                              │  sites/<tenant>/    │
                                              └─────────┬──────────┘
                                                        │
                                              ┌─────────▼──────────┐
                                              │  FRANZ             │
                                              │  WhatsApp outreach  │
                                              │  meowhats API       │
                                              └────────────────────┘
```

---

## 5. Padrões Arquiteturais

### 5.1 Pipeline State Machine

Arquivo: `backend/agents/manager/agent.py`

FSM com estados: `init → hunting → qualifying → designing → building → validating → publishing → outreach → done/failed`

Transições controladas pelo Manager. Cada estado tem checkpoint para retomada.

### 5.2 Pipeline Ledger (Magentic-One)

Arquivo: `backend/pipeline_ledger.py`

Registra: Facts (dados coletados), Plan (10 fases), Progress (status atual), Assignments (agente→tarefa), Decisions (decisões tomadas).

Persistido em disco (`/tmp/fralib_ledgers/`) + Postgres.

### 5.3 Pipeline Queue Manager

Arquivo: `backend/pipeline_queue_manager.py`

Controle de concorrência: max 3 pipelines simultâneos. Singleton `pipeline_queue`.

```
try_enter()  →  se < MAX_CONCURRENT, entra; senão aguarda
release()    →  libera slot ao finalizar
status()     →  retorna (ativos, max, disponíveis)
```

### 5.4 Postgres Job Queue

Arquivo: `backend/core/job_queue.py`

Fila distribuída usando `SELECT FOR UPDATE SKIP LOCKED`. Estados: `pending → running → completed / failed_retriable / failed_permanent`.

Backoff exponencial: 30s → 2min → 8min.

Crash recovery: heartbeat a cada 30s; se > 5min sem heartbeat, job volta para pending.

### 5.5 Agent Router (Dynamic Model Routing)

Arquivo: `backend/agent_router.py`

Classifica lead por complexidade (score 0–10) → seleciona modelo/tokens/temperature por agente.

Escala automática: haiku → sonnet → opus.

### 5.6 LLM Router (Multi-Provider Cascade)

Arquivo: `backend/services/llm_router.py`

Cascade Anthropic com fallback automático entre modelos. Suporta OpenAI, Google, Groq via `ia_manager`.

Retry com backoff exponencial + jitter via `retry_helper`.

### 5.7 IA Manager (Key Rotation + Circuit Breaker)

Arquivo: `backend/services/ia_manager.py`

Round-robin entre API keys do banco (`provider_keys` table). Circuit-breaker com cooldown. Orçamento diário: 2M tokens. Rate limit global: 30 calls/min.

### 5.8 Retry Helper

Arquivo: `backend/core/retry_helper.py`

Decorador `@com_retry` + função `tentar()` / `tentar_async()`. Backoff exponencial com jitter ±20%.

Distingue erros retriáveis (rate limit, timeout, 5xx) de permanentes (ValueError, TypeError, quota).

### 5.9 Multi-Tenant Schemas

Cada tenant tem schema próprio no Postgres. `criar_schema_tenant()` cria tabelas `leads` + `ciclos` por tenant.

---

## 6. Autenticação

- **JWT** (HS256) com secret em `.env` (`JWT_SECRET_KEY`)
- **HTTPBearer** — header `Authorization: Bearer <token>`
- **Roles**: `user`, `admin`, `superadmin`
- **Rate limit híbrido**: user_id (JWT) ou IP (fallback)
- **2FA opcional** — TOTP via `twofa-setup.js`

---

## 7. Feature Flags

| Flag | Valores | Função |
|------|---------|--------|
| `FRALIB_AGENCY_OS` | off \| shadow \| on | Rollout progressivo do Agency OS |
| `FRALIB_SKIP_HTML_QUALITY_GATE` | 0 \| 1 | Pular QA Vision |
| `FRALIB_BUILDER_AUTO_APPROVE` | 0 \| 1 | Auto-aprovar HTML sem QA |
| `FRALIB_BUILDER_ENGINE` | openui | Engine de geração HTML |
| `FRALIB_TRACING` | 0 \| 1 | Tracing de pipeline |
| `USE_QA_V2` | False \| True | Usar QA Vision v2 |

---

## 8. Deploy

### Fluxo

```
editar local → git add → git commit → git push origin master
                                    │
                              post-receive hook
                                    │
                              VPS: git pull + rebuild containers
```

### Containers que precisam rebuild após mudança

| Mudança | Containers afetados |
|---------|-------------------|
| `backend/**/*.py` | app + worker |
| `frontend/**` | app |
| `Dockerfile` | app + worker |
| `openui-service/` | restart systemd `fralib-openui` |

### Comandos úteis na VPS

```bash
# Logs
journalctl -u fralib-api -f
docker logs -f fralib-worker-pipeline-1
journalctl -u fralib-openui -f

# Restart
docker compose -f /opt/fralib/docker-compose.prod.yml restart app worker
systemctl restart fralib-openui

# DB direto
docker exec -it fralib-postgres-1 psql -U fralib_user -d fralib_db
```

---

## 9. Observabilidade

### 9.1 Infraestrutura

- **Logs**: container logs (docker) + journalctl (openui)
- **Métricas**: `api_usage_endpoints` — tracking de chamadas LLM
- **Pipeline errors**: tabela `pipeline_error_log` — erro estruturado por step
- **Provider alerts**: tabela `provider_alerts` — saúde dos providers
- **Tracing**: flag `FRALIB_TRACING=1` — traces/spans por run

### 9.2 Trace/Span Model

Arquivo: `observability.py`

```
Trace (1 por pipeline run)
  ├── trace_id: str (UUID curto)
  ├── run_id: str (referência ao job)
  ├── lead_nome, nicho, tier, complexidade
  ├── spans: List[Span]
  │   ├── span_id, nome, agente, modelo
  │   ├── inicio, fim, duracao_ms, status
  │   ├── input_tokens, output_tokens, cache_hit_tokens
  │   ├── custo_usd, erro, eventos[]
  │   └── ...
  └── Agregados: total_input_tokens, total_output_tokens,
                 total_cache_hit, custo_total_usd, total_chamadas_llm
```

### 9.3 Instrumentação (código)

**Worker (`worker.py`):**
- Cria `Trace` por job consumido da fila
- Inicia span `pipeline_total` no início de cada run
- Wira dados do `TokenTracker` (tokens, custo) nos spans do trace
- Chama `salvar_trace(trace)` no final de cada run (try/except best-effort)

**Manager FSM (`backend/agents/manager/agent.py`):**
- Acessa trace via variável global `_t`
- Cada step da FSM cria um span via `_t.iniciar_span(f"step_{step_name}", ...)`
- FSM steps: `step_load`, `step_hunter`, `step_caio`, `step_design`, `step_build`, `step_validate`, `step_deploy`, `step_franz`

**Salvamento (`observability.salvar_trace()`):**
- INSERT INTO `pipeline_traces` com ON CONFLICT DO UPDATE
- Tabela: 16 colunas (trace_id, run_id, lead_nome, nicho, tier, complexidade,
  duracao_total_ms, status, total_input_tokens, total_output_tokens,
  total_cache_hit, custo_total_usd, total_chamadas_llm, spans_json, created_at)

### 9.4 Error Logging

Arquivo: `backend/core/pipeline_error_log.py`

- `log_step_error(lead_id, tenant_id, step_name, exc, categoria=None)`
- INSERT INTO `pipeline_error_log` (lead_id, tenant_id, step, exception_type,
  message, traceback, fase_origem)
- Categorização automática: TIMEOUT, LLM_ERROR, DB_ERROR, HTML_ERROR

### 9.5 Dashboard

Arquivo: `backend/endpoints/obs_endpoints.py`

| Endpoint | Função |
|----------|--------|
| `GET /api/observability/dashboard` | KPIs agregados |
| `GET /api/observability/por-agente` | Métricas por agente |
| `GET /api/observability/gargalos` | Steps mais lentos |
| `GET /api/observability/alertas` | Alertas de anomalia |
| `GET /api/observability/traces` | Lista de traces recentes |
| `GET /api/observability/trace/{trace_id}` | Detalhe de um trace |

---

## 10. Limitações Conhecidas

- Builder (`agents/builder/agent.py`) existe só na VPS — não no disco local
- `pipeline_endpoints.py` tem 1664 linhas — aguardando refatoração
- `Franz.py` tem 1362 linhas — próximo do limite
- 3 workers consolidados em 1 (commit f47bd586)
- OpenUI é o único gerador HTML (Liam removido)
