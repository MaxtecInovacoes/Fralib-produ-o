# FraLib — Dicionário de Arquivos

Índice completo de módulos Python e arquivos do projeto com descrição de cada um.

---

## Convenções

- **Nomeação**: `snake_case.py` para Python, `kebab-case.html` para HTML, `camelCase.js` para JS
- **Tamanho máximo**: 800 linhas (refatorar se exceder)
- **Docstrings**: obrigatórias em módulos públicos
- **Type annotations**: obrigatórias em assinaturas

---

## backend/core/ — Infraestrutura

| Arquivo | Descrição |
|---------|-----------|
| `__init__.py` | Package marker |
| `database.py` | SQLAlchemy engine + session factory. `get_db()` dependency para FastAPI. `criar_schema_tenant()` cria schema + tabelas por tenant. Engine compartilhado importado como `_shared_engine` em auth.py. |
| `auth.py` | JWT decode + HTTPBearer. `get_current_user()` valida token + busca role do banco. SECRET_KEY do `.env`. |
| `job_queue.py` | Fila persistente Postgres. `enqueue()` com idempotency_key + ON CONFLICT DO NOTHING. `claim_next()` SELECT FOR UPDATE SKIP LOCKED. Backoff exponencial: 30s → 2min → 8min. Estados: pending/running/completed/failed_retriable/failed_permanent. Crash recovery via heartbeat 30s. |
| `rate_limiter.py` | SlowAPI limiter compartilhado. Chave híbrida: user_id (JWT) ou IP (fallback). |
| `retry_helper.py` | `@com_retry` decorator. `tentar()` sync + `tentar_async()` async. Backoff exponencial + jitter ±20%. Distingue erros retriáveis (rate limit, timeout, 5xx) de permanentes (ValueError, TypeError, quota). |

## backend/services/ — Lógica de Negócio

| Arquivo | Descrição |
|---------|-----------|
| `__init__.py` | Package marker |
| `llm_router.py` | Multi-provider LLM router. Cascade Anthropic: opus-5 → opus-4-8 → opus-4-7 → sonnet-5 → sonnet-4-6 → sonnet-4-5 → haiku-5 → haiku-4-5. Suporta OpenAI, Google, Groq. Usa `ia_manager.pick_key()`. |
| `ia_manager.py` | Round-robin de API keys do banco (`provider_keys` table). Circuit-breaker com cooldown. DAILY_TOKEN_BUDGET=2M, GLOBAL_MAX_CALLS_PER_MIN=30. LRU atômico via DB. |
| `credits_manager.py` | Sistema de planos (trial/starter/pro/ilimitado/beta). Duplo cadeado: créditos diários + cooldown. Reset lazy por data BRT. CUSTO_POR_CICLO_USD=0.34. |
| `token_bucket.py` | Rate limiting por token bucket algorithm. |
| `email_service.py` | Envio de e-mails transacionais (reset senha, welcome). |
| `site_health_check.py` | Monitoramento de sites publicados — ping + status HTTP. |
| `lead_supply_engine.py` | Engine central de supply de leads. `run_production_tick()`, `run_caio_job()`, `run_hunter_job()`. `handle_pipeline_job_finished()` atualiza lead_inventory + re-arma próximo tick. `log_pipeline_error()` persiste erro estruturado em `pipeline_error_log`. |

## backend/agents/ — Agentes IA

### Agentes do Pipeline (ordem de execução)

| # | Arquivo | Agente | Função | Modelo |
|---|---------|--------|--------|--------|
| 1 | `theo.py` | Theo | Estrategista — briefing inicial, PRD textual | sonnet/haiku → opus |
| 2 | `designer_prd.py` | Designer PRD | Arquiteto visual — seções, paleta, animações | opus/sonnet |
| 3 | `arquiteto_mestre.py` | Arquiteto Mestre | Funde Theo + Designer em PRD unificado | opus |
| 4 | `builder/agent.py` | Builder | Gera HTML chunked via OpenUI (4×18000=64000 tokens) | sonnet-4-6 |
| 5 | `liz.py` | Liz | Revisora de código — valida HTML gerado | haiku/sonnet |
| 6 | `caio.py` | Caio | Qualificador — tier MORNO/STANDARD/PREMIUM, score 0-100 | haiku |
| 7 | `bryan.py` | Franz | SDR WhatsApp — outreach, follow-up, agendamento | haiku |

### Agentes de Suporte

| Arquivo | Função |
|---------|--------|
| `manager/agent.py` | PipelineState dataclass + FSM. Estados: init→hunting→qualifying→designing→building→validating→publishing→outreach→done/failed. Flag USE_QA_V2. |
| `brain.py` | Orquestração central — coordena agentes. |
| `memory.py` | Memória episódica + semântica do Franz. |
| `agent_rag.py` | Retrieval-augmented generation — contexto de conhecimento. |
| `animation_injector.py` | Injetor de animações CSS/JS no HTML final. |
| `animation_profile.py` | Perfis de animação por nicho (durações, easings). |
| `color_extractor.py` | Extrai paleta de cores de referências visuais. |
| `color_enforcer.py` | Garante consistência de cores no HTML gerado. |
| `design_context.py` | Tokens OKLch por nicho (cores primárias, secundárias, tipografia). |
| `design_guidelines.py` | Guidelines de design system (spacing, grid, breakpoints). |
| `open_design_selector.py` | Seleciona design system para o Builder. |
| `keyword_research.py` | Pesquisa de palavras-chave SEO para o PRD. |
| `seo_context.py` | Contexto SEO (meta tags, schema markup, geo). |
| `liam_seo.py` | SEO engine legado do Liam. |
| `liam_constitutional.py` | Constitutional AI — guardrails e princípios do Liam. |
| `liam_lats.py` | Language Agent Tree Search (experimental). |
| `liam_moa.py` | Mixture of Agents (experimental). |
| `liam_models.py` | Definição de modelos do Liam (legado). |
| `liam_tools.py` | Tools auxiliares do Liam (legado). |
| `liam_agent_loop.py` | Loop de agentes do Liam (legado). |
| `theo_tools.py` | Tools auxiliares do Theo. |
| `theo_agent_loop.py` | Loop de agentes do Theo. |
| `arquiteto_tools.py` | Tools auxiliares do Arquiteto. |
| `arquiteto_agent_loop.py` | Loop de agentes do Arquiteto. |
| `bryan_tools.py` | Tools auxiliares do Bryan (agendamento, parse). |
| `bryan_agent_loop.py` | Loop de agentes do Bryan (SDR conversations). |
| `liz_rubricas.py` | Rubricas de avaliação da Liz (critérios de qualidade). |
| `craft_rules.py` | Regras de craft para geração de conteúdo. |
| `skill_loader.py` | Carrega skills dinâmicas dos agentes. |
| `token_tracker.py` | Rastreia consumo de tokens por agente + custo USD. |
| `pipeline_checkpoint.py` | Checkpoints para retomada de pipeline após crash. `limpar_checkpoints_expirados()` remove > 24h. |
| `unsplash_fetcher.py` | Busca imagens no Unsplash API por nicho/termo. |
| `markdown_prd_parser.py` | Parseia PRDs em Markdown para estrutura interna. |
| `llm_direct.py` | Chamada direta a LLM (bypass router) — usado em casos específicos. |
| `validation_enforcer.py` | Enforcement de validações pós-geração. |
| `validation_layer.py` | Camada de validação genérica (HTML, CSS, JS). |
| `cinematic_post_processor.py` | Pós-processamento cinematográfico (parallax, reveals). |

### Agentes Arquivados (`_arquivo/`) — não usados, mantidos para referência

| Arquivo | Descrição |
|---------|-----------|
| `alex.py` | Integrador — substituído por Arquiteto Mestre |
| `alex_cores.py` | Cores do Alex — substituído por Design Context |
| `alex_fotos.py` | Fotos do Alex — substituído por Unsplash Fetcher |
| `alex_logo.py` | Logo do Alex — substituído por Builder |
| `alex_models.py` | Models do Alex — substituído por LLM Direct |
| `liam_motion.py` | Animações do Liam — substituído por Animation Profile |
| `animation_injector.py` | Versão antiga — substituída pela nova |
| `design_guidelines.py` | Versão antiga — substituída pela nova |
| `design_system.py` | Sistema antigo — substituído por Design Context |

### Builder (OpenUI)

| Arquivo | Descrição |
|---------|-----------|
| `quality_gate_v2/` | Vision QA v2 — pontua design com LLM vision (gpt-4o-mini primary / 9router fallback). Repair loop regenera se score < 7.5. |

> **Nota**: `builder/agent.py` existe apenas na VPS (`/opt/fralib/backend/agents/builder/agent.py`). Não está no disco local.

## backend/endpoints/ — Rotas FastAPI (21 routers)

| Arquivo | Descrição |
|---------|-----------|
| `auth_endpoints.py` | Login, registro, refresh token, 2FA |
| `dashboard_endpoints.py` | KPIs, métricas, gráficos do usuário |
| `pipeline_endpoints.py` | CRUD pipelines, trigger jobs, SSE progresso (1664 linhas — refatorar) |
| `pipeline_edit_endpoints.py` | Edição de pipelines em andamento |
| `sse_endpoints.py` | Server-Sent Events — streaming de progresso em tempo real |
| `credits_endpoints.py` | Consumo e verificação de créditos |
| `users_endpoints.py` | CRUD usuários, perfis, roles |
| `leads_endpoints.py` | CRUD leads, busca, filtros |
| `beta_endpoints.py` | Cadastro e gerenciamento beta |
| `whatsapp_endpoints.py` | Config sessões WhatsApp, status |
| `llm_endpoints.py` | Config providers LLM, modelos |
| `api_usage_endpoints.py` | Métricas de uso de API |
| `superadmin_endpoints.py` | Painel superadmin — tenants, settings globais |
| `provider_keys_endpoints.py` | CRUD API keys dos providers |
| `provider_alerts_endpoints.py` | Alertas e saúde dos providers |
| `agent_config_endpoints.py` | Config de agentes por tenant |
| `falhas_endpoints.py` | Log e visualização de falhas de pipeline |
| `site_editor_endpoints.py` | API do editor visual de sites |
| `tracking_endpoints.py` | Tracking de visitas (site_visitas) |
| `cron_endpoints.py` | Cron endpoints (Bryan outreach scheduling) |
| `blog_endpoints.py` | Gerenciamento de conteúdo do blog |
| `obs_endpoints.py` | Observabilidade — health, métricas, status |
| `queue_endpoints.py` | Status da fila de jobs, throughput |

## backend/utils/ — Utilitários

| Arquivo | Descrição |
|---------|-----------|
| `agente1_hunter_v2.py` | Hunter v2 — coleta dados de leads via scraping Google Maps + Playwright |
| `espionar_concorrencia.py` | Análise de concorrentes — scraping + comparação |
| `google_local_scraper.py` | Scraper do Google Local Results |
| `google_maps_gosom.py` | Google Maps scraper via Gosom (proxy) |
| `password_utils.py` | Hash (bcrypt) + verify de senhas |
| `secrets_crypto.py` | Criptografia de secrets sensíveis |

## backend/ — Arquivos Raiz

| Arquivo | Descrição |
|---------|-----------|
| `agent_router.py` | Dynamic model routing por complexidade do lead. Thread-local router. `calcular_complexidade_lead()` score 0–10. |
| `config.py` | Configuração centralizada — env vars, constants. |

## Root — Arquivos Raiz do Projeto

| Arquivo | Descrição |
|---------|-----------|
| `server.py` | Entrypoint FastAPI. Lifespan: reset pipeline_state, marca jobs interrompidos, migrations Alembic, WhatsApp listener. 21 routers. CORS + security headers. |
| `worker.py` | Entrypoint worker daemon. `_load_job_tipos()` lê WORKER_JOB_TYPES do env. `_run_pipeline_job()` + `_run_supply_job()`. Loop com poll_interval configurável. |
| `Dockerfile` | Node:22-bookworm-slim. Cria venv Python, instala playwright+chromium, user `fralib`. |
| `docker-compose.prod.yml` | 4 services: postgres, redis, app, worker (unificado). |
| `alembic.ini` | Config Alembic migrations. |
| `alembic/` | Migrations versionadas. |

## frontend/ — Interface

| Arquivo | Descrição |
|---------|-----------|
| `admin.html` | Painel admin (build dos partials) |
| `dashboard.html` | Dashboard usuário (KPIs, gráficos) |
| `login.html` | Página de login |
| `landing.html` | Landing page pública |
| `blog/index.html` | Blog |
| `build.py` | Script que concatena partials → HTML final |
| `build_admin.py` | Build do admin.html |
| `partials/admin/_head.html` | Head do admin (meta, CSS, fonts) |
| `partials/admin/_main-header.html` | Header principal |
| `partials/admin/_sidebar.html` | Sidebar de navegação |
| `partials/admin/_modals.html` | Modais (criar tenant, confirmar ação) |
| `partials/admin/_scripts.html` | Scripts JS do admin |
| `partials/admin/_view-overview.html` | View Overview do admin |
| `partials/admin/_view-crm.html` | View CRM do admin |
| `partials/admin/_view-ciclos.html` | View Ciclos do admin |
| `partials/admin/_view-config.html` | View Configurações do admin |
| `partials/admin/_view-perfil.html` | View Perfil do admin |
| `partials/admin/_view-uti.html` | View UTI do admin |
| `partials/dashboard/_head.html` | Head do dashboard |
| `partials/dashboard/_header.html` | Header do dashboard |
| `partials/dashboard/_kpi-cards.html` | Cards de KPI |
| `css/reading.css` | Estilos modo leitura |
| `css/toast.css` | Estilos toast notifications |
| `js/auth-helper.js` | Helper de autenticação JWT no frontend |
| `js/csrf-helper.js` | Helper CSRF token |
| `js/socket-client.js` | Cliente SSE/WebSocket para progresso |
| `js/site-editor.js` | Editor visual de sites (drag & drop) |
| `js/toast.js` | Toast notifications |
| `js/twofa-setup.js` | Setup 2FA TOTP no frontend |
| `js/pixel-office.js` | Pixel tracking (Facebook/Google) |

## tests/ — Testes (pytest)

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| `conftest.py` | — | Fixtures compartilhadas pytest |
| `conftest_temp.py` | — | Fixtures temporárias |
| `test_setup.py` | — | Verificação de setup de teste |
| `unit/test_auth_core.py` | Unit | Testes de autenticação core |
| `unit/test_auth_endpoints.py` | Unit | Testes de endpoints de auth |
| `unit/test_database.py` | Unit | Testes de database/schemas multi-tenant |
| `unit/test_password_utils.py` | Unit | Testes de hash/verify senhas |
| `unit/test_utils.py` | Unit | Testes de utilitários |
| `integration/test_api_auth.py` | Integration | Testes de API auth (login, JWT, refresh) |
| `integration/test_api_pipeline.py` | Integration | Testes de API pipeline (CRUD, trigger) |
| `integration/test_idor_multitenant.py` | Integration | Testes de isolamento multi-tenant (IDOR) |
| `e2e/test_e2e_login.py` | E2E | Teste E2E login (Playwright) |
| `e2e/test_e2e_pipeline.py` | E2E | Teste E2E pipeline completo |

## docs/ — Documentação

| Arquivo | Descrição |
|---------|-----------|
| `ARQUITETURA_DEPLOY.md` | Arquitetura de deploy da VPS |
| `FILE_DICTIONARY.md` | Este arquivo — dicionário completo |
| `ARCHITECTURE.md` | Visão arquitetural do sistema |
| `BRIEF_CLAUDE_VPS_TENANT2.md` | Brief para tenant 2 |
| `BUGS_E_ACERTOS.md` | Log de bugs e acertos |
| `PIPELINE_FIX_PLAN.md` | Plano de fix do pipeline |
| `PLAYBOOK_PIPELINE_VALIDADA.md` | Playbook validado do pipeline |
