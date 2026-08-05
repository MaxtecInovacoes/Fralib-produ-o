# Agentes FraLib — Mapa de Responsabilidades

Cada agente é um módulo Python. Esta tabela é a fonte de verdade para
entender o que cada arquivo faz, qual modelo LLM usa e em que fase do
pipeline ele roda.

## Pipeline de Geração (ordem de execução)

```
[1] HUNTER      Valida/coleta lead_data (utils/agente1_hunter_v2.py)
[2] CAIO        Qualifica lead — tier MORNO/STANDARD/PREMIUM, score 0-100 (agents/caio.py)
[3] ARQUITETO   PRD com seções, paleta OKLch, animações (agents/arquiteto_mestre.py)
[4] BUILDER     HTML via OpenUI chunked (agents/builder/agent.py — existe só na VPS)
[5] QA v2       Vision QA score 7.9/10 PASSED (agents/builder/quality_gate_v2/)
[6] DEPLOY      Site salvo em /var/www/fralib/sites/
[7] FRANZ       Lead marcado para outreach WhatsApp (agents/franz/ — agent loop MCP-like com tools)
```

## Agentes do Pipeline (ordem de execução)

| # | Agente | Arquivo | Modelo | max_tokens | Função |
|---|--------|---------|--------|------------|--------|
| 1 | Hunter | `utils/agente1_hunter_v2.py` | Playwright scraping | — | Valida/coleta lead_data via Google Maps |
| 2 | Caio | `agents/caio.py` | haiku | 2000 | Qualificador — classifica lead por tier/score |
| 3 | Arquiteto Mestre | `agents/arquiteto_mestre.py` | sonnet | 8000 | Gera PRD completo (seções, paleta OKLch, animações) |
| 4 | Builder (OpenUI) | `agents/builder/agent.py` | claude-sonnet-4-6 | 64000 (4×18000) | Gera HTML chunked via OpenUI (Node.js :3333) |
| 5 | QA v2 | `agents/builder/quality_gate_v2/` | gpt-4o-mini / 9router | — | Vision QA — pontua design, repair loop se < 7.5 |
| 6 | Deploy | (sem LLM) | — | — | Salva HTML em /var/www/fralib/sites/ + metadata.json |
| 7 | Franz | `agents/franz/` (agent loop) + `agents/franz.py` | sonnet | 4000 | SDR WhatsApp — outreach, follow-up, agendamento (MCP-like tools) |

## Agentes de Suporte

| Agente | Arquivo | Função |
|--------|---------|--------|
| Memory | `agents/memory.py` | Memória episódica + semântica do Franz |
| Brain | `agents/brain.py` | Orquestração central de agentes |
| Animation Injector | `agents/animation_injector.py` | Injetor de animações CSS/JS no HTML |
| Animation Profile | `agents/animation_profile.py` | Perfis de animação por nicho |
| Design Context | `agents/design_context.py` | Tokens OKLch por nicho (cores, tipografia) |
| Design Guidelines | `agents/design_guidelines.py` | Guidelines de design system |
| Open Design Selector | `agents/open_design_selector.py` | Seleção de design system para o Builder |
| Liam SEO | `agents/liam_seo.py` | SEO — meta tags, schema, geo-tags |
| Liam Tools | `agents/liam_tools.py` | Tools auxiliares do Liam (legado) |
| Liam Constitutional | `agents/liam_constitutional.py` | Constitutional AI — guardrails do Liam |
| Liam LATS | `agents/liam_lats.py` | Language Agent Tree Search (experimental) |
| Liam MOA | `agents/liam_moa.py` | Mixture of Agents (experimental) |
| Liam Models | `agents/liam_models.py` | Definição de modelos do Liam (legado) |
| Franz Agent Loop | `agents/franz_agent_loop.py` | Loop de agentes do Franz |
| Liam Agent Loop | `agents/liam_agent_loop.py` | Loop de agentes do Liam (legado) |
| Theo Agent Loop | `agents/theo_agent_loop.py` | Loop de agentes do Theo |
| Franz Agent Loop | `agents/franz_agent_loop.py` | Loop de agentes do Franz |
| Arquiteto Agent Loop | `agents/arquiteto_agent_loop.py` | Loop de agentes do Arquiteto |
| Liz Rubricas | `agents/liz_rubricas.py` | Rubricas de avaliação da Liz |
| Craft Rules | `agents/craft_rules.py` | Regras de craft para geração de conteúdo |
| Validation Enforcer | `agents/validation_enforcer.py` | Enforcement de validações |
| Validation Layer | `agents/validation_layer.py` | Camada de validação genérica |
| Color Extractor | `agents/color_extractor.py` | Extrai paleta de cores de referências |
| Color Enforcer | `agents/color_enforcer.py` | Garante consistência de cores no output |
| Cinematic Post Processor | `agents/cinematic_post_processor.py` | Pós-processamento cinematográfico |
| SEO Context | `agents/seo_context.py` | Contexto SEO para geração |
| Skill Loader | `agents/skill_loader.py` | Carrega skills dinâmicas dos agentes |
| Token Tracker | `agents/token_tracker.py` | Rastreia consumo de tokens por agente + custo USD (thread-local) |
| Observability | `observability.py` | Traces/spans por run — dashboard em `/api/observability/dashboard` |
| Pipeline Checkpoint | `agents/pipeline_checkpoint.py` | Checkpoints para retomada de pipeline |
| Unsplash Fetcher | `agents/unsplash_fetcher.py` | Busca imagens no Unsplash |
| Markdown PRD Parser | `agents/markdown_prd_parser.py` | Parseia PRDs em Markdown |
| LLM Direct | `agents/llm_direct.py` | Chamada direta a LLM (bypass router) |

## Agentes Legado (não executam no pipeline, mantidos para referência)

| Agente | Arquivo | O que fazia | Substituído por |
|--------|---------|-------------|-----------------|
| Theo | `agents/theo.py` | Estrategista — briefing inicial, PRD textual | Arquiteto Mestre (funde Theo + Designer) |
| Designer PRD | `agents/designer_prd.py` | Arquiteto visual — seções, paleta, animações | Arquiteto Mestre (funde Theo + Designer). **Classe usada como contrato de schema (DesignerPRD, ColorPalette, SectionSpec, AnimationSpec)** |
| Liam | `agents/liam.py` | Gerador HTML antigo (~1373 linhas) | Builder OpenUI chunked |
| Liz | `agents/liz.py` | Revisora de código — valida HTML gerado | QA v2 (Vision LLM + repair loop) |
| Liam Tools | `agents/liam_tools.py` | Tools auxiliares do Liam | — |
| Liam LATS | `agents/liam_lats.py` | Language Agent Tree Search (experimental) | — |
| Liam MOA | `agents/liam_moa.py` | Mixture of Agents (experimental) | — |
| Liam Models | `agents/liam_models.py` | Definição de modelos do Liam | LLM Router |
| Franz Agent Loop | `agents/franz_agent_loop.py` | Loop de agentes do Franz | Franz (via cron dispatcher) |
| Liam Agent Loop | `agents/liam_agent_loop.py` | Loop de agentes do Liam (legado) | — |
| Theo Agent Loop | `agents/theo_agent_loop.py` | Loop de agentes do Theo | — |
| Arquiteto Agent Loop | `agents/arquiteto_agent_loop.py` | Loop de agentes do Arquiteto | Pipeline FSM em manager/agent.py |
| Liz Rubricas | `agents/liz_rubricas.py` | Rubricas de avaliação da Liz | QA v2 |

---

## Regra de Ouro da Modificação de Arquivos

> **NUNCA criar arquivo que já existe.**

1. **Listar antes de criar** — antes de criar qualquer arquivo, execute `ls`/`Glob` na pasta alvo para confirmar que não existe equivalente.
2. **Proibir duplicatas** — não criar segunda interface, segundo helper, segundo service para o mesmo domínio.
3. **Alterar existente** — se arquivo similar existe, edite-o. Não crie paralelo.
4. **Arquivos novos precisam de pergunta** — se não houver match claro, pergunte antes de criar.
5. **Exceções**: testes, configs, lockfiles podem ser criados sem bloqueio.

---

## Mapa do Projeto

| O que procuro | Onde está |
|---------------|-----------|
| Entrypoint da API | `server.py` (raiz) |
| Entrypoint do worker | `worker.py` (raiz) |
| Pipeline FSM | `backend/agents/manager/agent.py` |
| Job queue | `backend/core/job_queue.py` |
| LLM router | `backend/services/llm_router.py` |
| API keys / round-robin | `backend/services/ia_manager.py` |
| Créditos / planos | `backend/services/credits_manager.py` |
| Multi-tenant schemas | `backend/core/database.py` → `criar_schema_tenant()` |
| Env vars | `.env` (raiz — NÃO commitado) |
| Config centralizada | `backend/config.py` |
| Agente Builder | `backend/agents/builder/agent.py` (VPS only) |
| QA Vision v2 | `backend/agents/builder/quality_gate_v2/` |
| Franz (SDR) | `backend/agents/franz/ — agent loop + franz_tools.py` |
| Hunter | `backend/utils/agente1_hunter_v2.py` |
| Meowhats listener | `backend/whatsapp_listener.py` |
| Migrations | `alembic/` |
| Frontend build | `frontend/build.py` + `frontend/build_admin.py` |
| Deploy config | `docker-compose.prod.yml` + `docs/ARQUITETURA_DEPLOY.md` |
| OpenUI service | `/root/fralib/openui-service/` (VPS) |
| Nginx config | `/etc/nginx/sites-enabled/` (VPS) |

---

## Validação Obrigatória

Após qualquer mudança no código, execute **pelo menos** os testes unitários:

```bash
pytest tests/unit/ -v
```

Para mudanças em endpoints ou pipeline:
```bash
pytest tests/ -v --tb=short
```

Para verificar coverage (meta: 80%+):
```bash
pytest --cov=backend --cov-report=term-missing
```

Antes de commit:
```bash
# 1. Testes passam
pytest tests/ -q

# 2. Lint
ruff check backend/

# 3. Format
black backend/
isort backend/
```

---

## Naming Conventions

### Python

| Tipo | Convenção | Exemplo |
|------|-----------|---------|
| Módulos/arquivos | `snake_case.py` | `pipeline_endpoints.py` |
| Classes | `PascalCase` | `PipelineState`, `LeadInput` |
| Funções/métodos | `snake_case()` | `step_builder()`, `qualificar()` |
| Variáveis | `snake_case` | `lead_data`, `quality_score` |
| Constantes | `UPPER_SNAKE_CASE` | `MAX_ATTEMPTS`, `STATE_DONE` |
| Privado | `_leading_underscore` | `_log_step_error()`, `_db` |
| Type aliases | `snake_case` | `LeadInput` |
| Dataclasses | `PascalCase` | `@dataclass class PipelineState` |

### Frontend (JS vanilla)

| Tipo | Convenção | Exemplo |
|------|-----------|---------|
| Arquivos JS | `kebab-case.js` | `auth-helper.js` |
| Variáveis/funções | `camelCase` | `sendMessage()`, `leadData` |
| Constantes | `UPPER_SNAKE_CASE` | `API_BASE_URL` |
| CSS classes | `kebab-case` | `.kpi-card`, `.btn-primary` |
| HTML files | `kebab-case.html` | `admin.html` |

### Banco de Dados

| Tipo | Convenção | Exemplo |
|------|-----------|---------|
| Tabelas | `snake_case` | `leads`, `pipeline_error_log` |
| Colunas | `snake_case` | `lead_id`, `criado_em` |
| Schemas (tenant) | `tenant_{id}` | `tenant_1`, `tenant_2` |
| Sequences | `snake_case` | `jobs_id_seq` |
| Indexes | `ix_{table}_{col}` | `ix_leads_user_id` |

### Variáveis de Ambiente

| Tipo | Convenção | Exemplo |
|------|-----------|---------|
| Geral | `UPPER_SNAKE_CASE` | `DATABASE_URL`, `JWT_SECRET_KEY` |
| Feature flags | `UPPER_SNAKE_CASE` | `FRALIB_SKIP_HTML_QUALITY_GATE` |

---

## Agentes Arquivados (não usados, mantidos para referência)

| Agente | Arquivo | Motivo arquivamento |
|--------|---------|---------------------|
| Alex | `agents/_arquivo/alex.py` | Integrador — substituído por Arquiteto Mestre |
| Alex Cores | `agents/_arquivo/alex_cores.py` | Cores do Alex — substituído por Design Context |
| Alex Fotos | `agents/_arquivo/alex_fotos.py` | Fotos do Alex — substituído por Unsplash Fetcher |
| Alex Logo | `agents/_arquivo/alex_logo.py` | Logo do Alex — substituído por Builder |
| Alex Models | `agents/_arquivo/alex_models.py` | Models do Alex — substituído por LLM Direct |
| Liam Motion | `agents/_arquivo/liam_motion.py` | Animações do Liam — substituído por Animation Profile |
| Animation Injector (old) | `agents/_arquivo/animation_injector.py` | Versão antiga — substituída pela nova |
| Design Guidelines (old) | `agents/_arquivo/design_guidelines.py` | Versão antiga — substituída pela nova |
| Design System (old) | `agents/_arquivo/design_system.py` | Sistema antigo — substituído por Design Context |

## Roteamento de Modelos

**Arquivo:** `backend/agent_router.py`

Agentes são roteados por papel no pipeline (hardcoded no manager):

| Agente | Função no Pipeline | Modelo |
|--------|-------------------|--------|
| Arquiteto Mestre | Geração de PRD | opus |
| Builder (OpenUI) | Geração de HTML chunked | claude-sonnet-4-6 |
| Caio | Qualificação do lead | haiku |
| Franz | SDR WhatsApp outreach | sonnet |
| QA v2 | Vision QA (gpt-4o-mini) | gpt-4o-mini / 9router |

> **Nota:** A tabela antiga de roteamento por complexidade (SIMPLES/MÉDIO/COMPLEXO) referia-se aos agentes Theo, Liam, Liz — todos **legado**. O pipeline atual usa modelo fixo por agente conforme tabela acima.

## Router LLM Multi-Provider

**Arquivo:** `backend/services/llm_router.py`

Cascade Anthropic (fallback automático):
```
opus-5 → opus-4-8 → opus-4-7 → sonnet-5 → sonnet-4-6 → sonnet-4-5 → haiku-5 → haiku-4-5
```

Suporta OpenAI, Google, Groq via `ia_manager.pick_key()`.

## Serviços Auxiliares

| Serviço | Arquivo | Função |
|---------|---------|--------|
| IA Manager | `backend/services/ia_manager.py` | Round-robin de API keys + circuit-breaker |
| Credits Manager | `backend/services/credits_manager.py` | Planos (trial/starter/pro/ilimitado), duplo cadeado |
| Token Bucket | `backend/services/token_bucket.py` | Rate limiting por token bucket |
| Email Service | `backend/services/email_service.py` | Envio de e-mails transacionais |
| Site Health Check | `backend/services/site_health_check.py` | Monitoramento de sites publicados |
| Lead Supply Engine | `backend/services/lead_supply_engine.py` | Engine de supply de leads (Hunter + Caio + tick) |

## Core (Infraestrutura)

| Módulo | Arquivo | Função |
|--------|---------|--------|
| Database | `backend/core/database.py` | SQLAlchemy engine + schemas multi-tenant |
| Auth | `backend/core/auth.py` | JWT + HTTPBearer + role lookup |
| Job Queue | `backend/core/job_queue.py` | Fila persistente Postgres (SELECT FOR UPDATE SKIP LOCKED) |
| Rate Limiter | `backend/core/rate_limiter.py` | SlowAPI — user_or_ip hybrid key |
| Retry Helper | `backend/core/retry_helper.py` | `@com_retry` — backoff exponencial + jitter |

## Endpoints (21 routers)

| Router | Arquivo | Função |
|--------|---------|--------|
| Auth | `endpoints/auth_endpoints.py` | Login, registro, JWT |
| Dashboard | `endpoints/dashboard_endpoints.py` | KPIs, métricas |
| Pipeline | `endpoints/pipeline_endpoints.py` | CRUD pipeline, trigger jobs |
| Pipeline Edit | `endpoints/pipeline_edit_endpoints.py` | Edição de pipelines |
| SSE | `endpoints/sse_endpoints.py` | Server-Sent Events (progresso pipeline) |
| Credits | `endpoints/credits_endpoints.py` | Consumo de créditos |
| Users | `endpoints/users_endpoints.py` | CRUD usuários |
| Leads | `endpoints/leads_endpoints.py` | CRUD leads |
| Beta | `endpoints/beta_endpoints.py` | Cadastro beta |
| WhatsApp | `endpoints/whatsapp_endpoints.py` | Config WhatsApp |
| LLM | `endpoints/llm_endpoints.py` | Config LLM provider |
| API Usage | `endpoints/api_usage_endpoints.py` | Métricas de uso API |
| Superadmin | `endpoints/superadmin_endpoints.py` | Painel superadmin |
| Provider Keys | `endpoints/provider_keys_endpoints.py` | CRUD API keys |
| Provider Alerts | `endpoints/provider_alerts_endpoints.py` | Alertas de providers |
| Agent Config | `endpoints/agent_config_endpoints.py` | Config de agentes |
| Falhas | `endpoints/falhas_endpoints.py` | Log de falhas de pipeline |
| Site Editor | `endpoints/site_editor_endpoints.py` | Editor visual de sites |
| Tracking | `endpoints/tracking_endpoints.py` | Tracking de visitas |
| Cron | `endpoints/cron_endpoints.py` | Cron endpoints (Franz outreach) |
| Blog | `endpoints/blog_endpoints.py` | Gerenciamento de blog |
| OBS | `endpoints/obs_endpoints.py` | Observabilidade |
| Queue | `endpoints/queue_endpoints.py` | Status da fila de jobs |

## Utilitários

| Utilitário | Arquivo | Função |
|-----------|---------|--------|
| Hunter v2 | `utils/agente1_hunter_v2.py` | Coleta dados de leads via scraping |
| Espionar Concorrência | `utils/espionar_concorrencia.py` | Análise de concorrentes |
| Google Local Scraper | `utils/google_local_scraper.py` | Scraper Google Local |
| Google Maps Gosom | `utils/google_maps_gosom.py` | Google Maps via Gosom |
| Password Utils | `utils/password_utils.py` | Hash/verify de senhas |
| Secrets Crypto | `utils/secrets_crypto.py` | Criptografia de secrets |

## Frontend

| Arquivo | Função |
|---------|--------|
| `frontend/admin.html` | Painel admin (partials server-side) |
| `frontend/dashboard.html` | Dashboard do usuário |
| `frontend/login.html` | Login |
| `frontend/landing.html` | Landing page pública |
| `frontend/blog/index.html` | Blog |
| `frontend/build.py` | Build do frontend (concatena partials) |
| `frontend/build_admin.py` | Build do admin |
| `frontend/js/auth-helper.js` | Helper de autenticação JWT |
| `frontend/js/csrf-helper.js` | Helper CSRF token |
| `frontend/js/socket-client.js` | Cliente SSE/WebSocket |
| `frontend/js/site-editor.js` | Editor visual de sites |
| `frontend/js/toast.js` | Toast notifications |
| `frontend/js/twofa-setup.js` | Setup 2FA |
| `frontend/js/pixel-office.js` | Pixel tracking |
