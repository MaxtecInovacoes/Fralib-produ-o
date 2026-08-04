# FraLib — Dicionário de Arquivos

Índice completo de módulos Python e arquivos do projeto com descrição de cada um.

---

## Convenções

- **Nomeação**: `snake_case.py` para Python, `kebab-case.html` para HTML, `camelCase.js` para JS
- **Tamanho máximo**: 800 linhas (refatorar se exceder)
- **Docstrings**: obrigatórias em módulos públicos
- **Type annotations**: obrigatórias em assinaturas
- **Novo arquivo**: só criar se não existir equivalente. Regra: listar a pasta antes de criar.

> **Legenda "Pode Criar":**
> - `SIM` — criar novo módulo/aquivo quando necessário
> - `NAO` — pasta consolidada, alterar existentes, não criar novos sem justificativa forte

---

## backend/core/ — Infraestrutura (pode criar: NAO)

| Arquivo | Descrição | Pode Criar |
|---------|-----------|
| `__init__.py` | Package marker | NAO |
| `database.py` | SQLAlchemy engine + session factory. `get_db()` dependency para FastAPI. `criar_schema_tenant()` cria schema + tabelas por tenant. Engine compartilhado importado como `_shared_engine` em auth.py. | NAO |
| `auth.py` | JWT decode + HTTPBearer. `get_current_user()` valida token + busca role do banco. SECRET_KEY do `.env`. | NAO |
| `job_queue.py` | Fila persistente Postgres. `enqueue()` com idempotency_key + ON CONFLICT DO NOTHING. `claim_next()` SELECT FOR UPDATE SKIP LOCKED. Backoff exponencial: 30s → 2min → 8min. Estados: pending/running/completed/failed_retriable/failed_permanent. Crash recovery via heartbeat 30s. | NAO |
| `rate_limiter.py` | SlowAPI limiter compartilhado. Chave híbrida: user_id (JWT) ou IP (fallback). | NAO |
| `retry_helper.py` | `@com_retry` decorator. `tentar()` sync + `tentar_async()` async. Backoff exponencial + jitter ±20%. Distingue erros retriáveis (rate limit, timeout, 5xx) de permanentes (ValueError, TypeError, quota). | NAO |

## backend/services/ — Lógica de Negócio (pode criar: NAO)

| Arquivo | Descrição | Pode Criar |
|---------|-----------|
| `__init__.py` | Package marker | NAO |
| `llm_router.py` | Multi-provider LLM router. Cascade Anthropic: opus-5 → opus-4-8 → opus-4-7 → sonnet-5 → sonnet-4-6 → sonnet-4-5 → haiku-5 → haiku-4-5. Suporta OpenAI, Google, Groq. Usa `ia_manager.pick_key()`. | NAO |
| `ia_manager.py` | Round-robin de API keys do banco (`provider_keys` table). Circuit-breaker com cooldown. DAILY_TOKEN_BUDGET=2M, GLOBAL_MAX_CALLS_PER_MIN=30. LRU atômico via DB. | NAO |
| `credits_manager.py` | Sistema de planos (trial/starter/pro/ilimitado/beta). Duplo cadeado: créditos diários + cooldown. Reset lazy por data BRT. CUSTO_POR_CICLO_USD=0.34. | NAO |
| `token_bucket.py` | Rate limiting por token bucket algorithm. | NAO |
| `email_service.py` | Envio de e-mails transacionais (reset senha, welcome). | NAO |
| `site_health_check.py` | Monitoramento de sites publicados — ping + status HTTP. | NAO |
| `lead_supply_engine.py` | Engine central de supply de leads. `run_production_tick()`, `run_caio_job()`, `run_hunter_job()`. `handle_pipeline_job_finished()` atualiza lead_inventory + re-arma próximo tick. `log_pipeline_error()` persiste erro estruturado em `pipeline_error_log`. | NAO |

## backend/agents/ — Agentes IA (pode criar: SIM — agentes do pipeline em desenvolvimento, módulos de suporte consolidados)

### Agentes do Pipeline (ordem de execução)

| # | Arquivo | Agente | Função | Modelo | Pode Criar |
|---|---------|--------|--------|--------|------------|
| 1 | `theo.py` | Theo | Estrategista — briefing inicial, PRD textual | sonnet/haiku → opus | NAO |
| 2 | `designer_prd.py` | Designer PRD | Arquiteto visual — seções, paleta, animações | opus/sonnet | NAO |
| 3 | `arquiteto_mestre.py` | Arquiteto Mestre | Funde Theo + Designer em PRD unificado | opus | NAO |
| 4 | `builder/agent.py` | Builder | Gera HTML chunked via OpenUI (4×18000=64000 tokens) | sonnet-4-6 | NAO |
| 5 | `liz.py` | Liz | Revisora de código — valida HTML gerado | haiku/sonnet | NAO |
| 6 | `caio.py` | Caio | Qualificador — tier MORNO/STANDARD/PREMIUM, score 0-100 | haiku | NAO |
| 7 | `bryan.py` | Franz | SDR WhatsApp — outreach, follow-up, agendamento | haiku | NAO |

### Agentes de Suporte (pode criar: NAO)

| Arquivo | Função | Pode Criar |
|---------|--------|------------|
| `manager/agent.py` | PipelineState dataclass + FSM. Estados: init→hunting→qualifying→designing→building→validating→publishing→outreach→done/failed. Flag USE_QA_V2. | NAO |
| `brain.py` | Orquestração central — coordena agentes. | NAO |
| `memory.py` | Memória episódica + semântica do Franz. | NAO |
| `agent_rag.py` | Retrieval-augmented generation — contexto de conhecimento. | NAO |
| `animation_injector.py` | Injetor de animações CSS/JS no HTML final. | NAO |
| `animation_profile.py` | Perfis de animação por nicho (durações, easings). | NAO |
| `color_extractor.py` | Extrai paleta de cores de referências visuais. | NAO |
| `color_enforcer.py` | Garante consistência de cores no HTML gerado. | NAO |
| `design_context.py` | Tokens OKLch por nicho (cores primárias, secundárias, tipografia). | NAO |
| `design_guidelines.py` | Guidelines de design system (spacing, grid, breakpoints). | NAO |
| `open_design_selector.py` | Seleciona design system para o Builder. | NAO |
| `keyword_research.py` | Pesquisa de palavras-chave SEO para o PRD. | NAO |
| `seo_context.py` | Contexto SEO (meta tags, schema markup, geo). | NAO |
| `liam_seo.py` | SEO engine legado do Liam. | NAO |
| `liam_constitutional.py` | Constitutional AI — guardrails e princípios do Liam. | NAO |
| `liam_lats.py` | Language Agent Tree Search (experimental). | NAO |
| `liam_moa.py` | Mixture of Agents (experimental). | NAO |
| `liam_models.py` | Definição de modelos do Liam (legado). | NAO |
| `liam_tools.py` | Tools auxiliares do Liam (legado). | NAO |
| `liam_agent_loop.py` | Loop de agentes do Liam (legado). | NAO |
| `theo_tools.py` | Tools auxiliares do Theo. | NAO |
| `theo_agent_loop.py` | Loop de agentes do Theo. | NAO |
| `arquiteto_tools.py` | Tools auxiliares do Arquiteto. | NAO |
| `arquiteto_agent_loop.py` | Loop de agentes do Arquiteto. | NAO |
| `bryan_tools.py` | Tools auxiliares do Bryan (agendamento, parse). | NAO |
| `bryan_agent_loop.py` | Loop de agentes do Bryan (SDR conversations). | NAO |
| `liz_rubricas.py` | Rubricas de avaliação da Liz (critérios de qualidade). | NAO |
| `craft_rules.py` | Regras de craft para geração de conteúdo. | NAO |
| `skill_loader.py` | Carrega skills dinâmicas dos agentes. | NAO |
| `token_tracker.py` | Rastreia consumo de tokens por agente + custo USD. | NAO |
| `pipeline_checkpoint.py` | Checkpoints para retomada de pipeline após crash. `limpar_checkpoints_expirados()` remove > 24h. | NAO |
| `unsplash_fetcher.py` | Busca imagens no Unsplash API por nicho/termo. | NAO |
| `markdown_prd_parser.py` | Parseia PRDs em Markdown para estrutura interna. | NAO |

### Agentes Arquivados (`_arquivo/`) — não usados, mantidos para referência (pode criar: NAO)

| Arquivo | Descrição | Pode Criar |
|---------|-----------|
| `alex.py` | Integrador — substituído por Arquiteto Mestre | NAO |
| `alex_cores.py` | Cores do Alex — substituído por Design Context | NAO |
| `alex_fotos.py` | Fotos do Alex — substituído por Unsplash Fetcher | NAO |
| `alex_logo.py` | Logo do Alex — substituído por Builder | NAO |
| `alex_models.py` | Models do Alex — substituído por LLM Direct | NAO |
| `liam_motion.py` | Animações do Liam — substituído por Animation Profile | NAO |
| `animation_injector.py` | Versão antiga — substituída pela nova | NAO |
| `design_guidelines.py` | Versão antiga — substituída pela nova | NAO |
| `design_system.py` | Sistema antigo — substituído por Design Context | NAO |

### Builder (OpenUI) (pode criar: NAO)

| Arquivo | Descrição | Pode Criar |
|---------|-----------|------------|
| `quality_gate_v2/` | Vision QA v2 — pontua design com LLM vision (gpt-4o-mini primary / 9router fallback). Repair loop regenera se score < 7.5. | NAO |

> **Nota**: `builder/agent.py` existe apenas na VPS (`/opt/fralib/backend/agents/builder/agent.py`). Não está no disco local.

## backend/endpoints/ — Rotas FastAPI (21 routers) (pode criar: SIM)

| Arquivo | Descrição | Pode Criar |
|---------|-----------|------------|
| `auth_endpoints.py` | Login, registro, refresh token, 2FA | NAO |
| `dashboard_endpoints.py` | KPIs, métricas, gráficos do usuário | NAO |
| `pipeline_endpoints.py` | CRUD pipelines, trigger jobs, SSE progresso (1664 linhas — refatorar) | NAO |
| `pipeline_edit_endpoints.py` | Edição de pipelines em andamento | NAO |
| `sse_endpoints.py` | Server-Sent Events — streaming de progresso em tempo real | NAO |
| `credits_endpoints.py` | Consumo e verificação de créditos | NAO |
| `users_endpoints.py` | CRUD usuários, perfis, roles | NAO |
| `leads_endpoints.py` | CRUD leads, busca, filtros | NAO |
| `beta_endpoints.py` | Cadastro e gerenciamento beta | NAO |
| `whatsapp_endpoints.py` | Config sessões WhatsApp, status | NAO |
| `llm_endpoints.py` | Config providers LLM, modelos | NAO |
| `api_usage_endpoints.py` | Métricas de uso de API | NAO |
| `superadmin_endpoints.py` | Painel superadmin — tenants, settings globais | NAO |
| `provider_keys_endpoints.py` | CRUD API keys dos providers | NAO |
| `provider_alerts_endpoints.py` | Alertas e saúde dos providers | NAO |
| `agent_config_endpoints.py` | Config de agentes por tenant | NAO |
| `falhas_endpoints.py` | Log e visualização de falhas de pipeline | NAO |
| `site_editor_endpoints.py` | API do editor visual de sites | NAO |
| `tracking_endpoints.py` | Tracking de visitas (site_visitas) | NAO |
| `cron_endpoints.py` | Cron endpoints (Bryan outreach scheduling) | NAO |
| `blog_endpoints.py` | Gerenciamento de conteúdo do blog | NAO |
| `obs_endpoints.py` | Observabilidade — health, métricas, status | NAO |
| `queue_endpoints.py` | Status da fila de jobs, throughput | NAO |

## backend/utils/ — Utilitários (pode criar: SIM)

| Arquivo | Descrição | Pode Criar |
|---------|-----------|------------|
| `agente1_hunter_v2.py` | Hunter v2 — coleta dados de leads via scraping Google Maps + Playwright | NAO |
| `espionar_concorrencia.py` | Análise de concorrentes — scraping + comparação | NAO |
| `google_local_scraper.py` | Scraper do Google Local Results | NAO |
| `google_maps_gosom.py` | Google Maps scraper via Gosom (proxy) | NAO |
| `password_utils.py` | Hash (bcrypt) + verify de senhas | NAO |
| `secrets_crypto.py` | Criptografia de secrets sensíveis | NAO |

## backend/ — Arquivos Raiz (pode criar: NAO)

| Arquivo | Descrição | Pode Criar |
|---------|-----------|------------|
| `agent_router.py` | Dynamic model routing por complexidade do lead. Thread-local router. `calcular_complexidade_lead()` score 0–10. | NAO |
| `config.py` | Configuração centralizada — env vars, constants. | NAO |

## Root — Arquivos Raiz do Projeto (pode criar: NAO)

| Arquivo | Descrição | Pode Criar |
|---------|-----------|------------|
| `server.py` | Entrypoint FastAPI. Lifespan: reset pipeline_state, marca jobs interrompidos, migrations Alembic, WhatsApp listener. 21 routers. CORS + security headers. | NAO |
| `worker.py` | Entrypoint worker daemon. `_load_job_tipos()` lê WORKER_JOB_TYPES do env. `_run_pipeline_job()` + `_run_supply_job()`. Loop com poll_interval configurável. | NAO |
| `Dockerfile` | Node:22-bookworm-slim. Cria venv Python, instala playwright+chromium, user `fralib`. | NAO |
| `docker-compose.prod.yml` | 4 services: postgres, redis, app, worker (unificado). | NAO |
| `alembic.ini` | Config Alembic migrations. | NAO |
| `alembic/` | Migrations versionadas. | NAO |

## frontend/ — Interface (pode criar: NAO)

| Arquivo | Descrição | Pode Criar |
|---------|-----------|------------|
| `admin.html` | Painel admin (build dos partials) | NAO |
| `dashboard.html` | Dashboard usuário (KPIs, gráficos) | NAO |
| `login.html` | Página de login | NAO |
| `landing.html` | Landing page pública | NAO |
| `blog/index.html` | Blog | NAO |
| `build.py` | Script que concatena partials → HTML final | NAO |
| `build_admin.py` | Build do admin.html | NAO |
| `partials/admin/_head.html` | Head do admin (meta, CSS, fonts) | NAO |
| `partials/admin/_main-header.html` | Header principal | NAO |
| `partials/admin/_sidebar.html` | Sidebar de navegação | NAO |
| `partials/admin/_modals.html` | Modais (criar tenant, confirmar ação) | NAO |
| `partials/admin/_scripts.html` | Scripts JS do admin | NAO |
| `partials/admin/_view-overview.html` | View Overview do admin | NAO |
| `partials/admin/_view-crm.html` | View CRM do admin | NAO |
| `partials/admin/_view-ciclos.html` | View Ciclos do admin | NAO |
| `partials/admin/_view-config.html` | View Configurações do admin | NAO |
| `partials/admin/_view-perfil.html` | View Perfil do admin | NAO |
| `partials/admin/_view-uti.html` | View UTI do admin | NAO |
| `partials/dashboard/_head.html` | Head do dashboard | NAO |
| `partials/dashboard/_header.html` | Header do dashboard | NAO |
| `partials/dashboard/_kpi-cards.html` | Cards de KPI | NAO |
| `css/reading.css` | Estilos modo leitura | NAO |
| `css/toast.css` | Estilos toast notifications | NAO |
| `js/auth-helper.js` | Helper de autenticação JWT no frontend | NAO |
| `js/csrf-helper.js` | Helper CSRF token | NAO |
| `js/socket-client.js` | Cliente SSE/WebSocket para progresso | NAO |
| `js/site-editor.js` | Editor visual de sites (drag & drop) | NAO |
| `js/toast.js` | Toast notifications | NAO |
| `js/twofa-setup.js` | Setup 2FA TOTP no frontend | NAO |
| `js/pixel-office.js` | Pixel tracking (Facebook/Google) | NAO |

## tests/ — Testes (pytest) (pode criar: SIM)

| Arquivo | Tipo | Descrição | Pode Criar |
|---------|------|-----------|------------|
| `conftest.py` | — | Fixtures compartilhadas pytest | NAO |
| `conftest_temp.py` | — | Fixtures temporárias | NAO |
| `test_setup.py` | — | Verificação de setup de teste | NAO |
| `unit/test_auth_core.py` | Unit | Testes de autenticação core | NAO |
| `unit/test_auth_endpoints.py` | Unit | Testes de endpoints de auth | NAO |
| `unit/test_database.py` | Unit | Testes de database/schemas multi-tenant | NAO |
| `unit/test_password_utils.py` | Unit | Testes de hash/verify senhas | NAO |
| `unit/test_utils.py` | Unit | Testes de utilitários | NAO |
| `integration/test_api_auth.py` | Integration | Testes de API auth (login, JWT, refresh) | NAO |
| `integration/test_api_pipeline.py` | Integration | Testes de API pipeline (CRUD, trigger) | NAO |
| `integration/test_idor_multitenant.py` | Integration | Testes de isolamento multi-tenant (IDOR) | NAO |
| `e2e/test_e2e_login.py` | E2E | Teste E2E login (Playwright) | NAO |
| `e2e/test_e2e_pipeline.py` | E2E | Teste E2E pipeline completo | NAO |

## docs/ — Documentação (pode criar: SIM)

| Arquivo | Descrição | Pode Criar |
|---------|-----------|------------|
| `ARQUITETURA_DEPLOY.md` | Arquitetura de deploy da VPS | NAO |
| `FILE_DICTIONARY.md` | Este arquivo — dicionário completo | NAO |
| `ARCHITECTURE.md` | Visão arquitetural do sistema | NAO |
| `BRIEF_CLAUDE_VPS_TENANT2.md` | Brief para tenant 2 | NAO |
| `BUGS_E_ACERTOS.md` | Log de bugs e acertos | NAO |
| `PIPELINE_FIX_PLAN.md` | Plano de fix do pipeline | NAO |
| `PLAYBOOK_PIPELINE_VALIDADA.md` | Playbook validado do pipeline | NAO |
