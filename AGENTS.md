# Agentes FraLib — Mapa de Responsabilidades

Cada agente é um módulo Python. Esta tabela é a fonte de verdade para
entender o que cada arquivo faz, qual modelo LLM usa e em que fase do
pipeline ele roda.

## Pipeline de Geração (ordem de execução)

```
[1] BANCO       Carrega lead direto do Postgres (manager/agent.py)
[2] HUNTER      Valida/coleta lead_data (utils/agente1_hunter_v2.py)
[3] CAIO        Qualifica lead — tier MORNO/STANDARD/PREMIUM, score 0-100 (agents/caio.py)
[4] ARQUITETO   PRD com seções, paleta OKLch, animações (agents/arquiteto_mestre.py)
[5] BUILDER     HTML via OpenUI chunked (agents/builder/agent.py — existe só na VPS)
[6] QA v2       Vision QA score 7.9/10 PASSED (agents/builder/quality_gate_v2/)
[7] DEPLOY      Site salvo em /var/www/fralib/sites/
[8] FRANZ       Lead marcado para outreach WhatsApp (agents/bryan.py)
```

## Agentes do Pipeline

| # | Agente | Arquivo | Modelo | max_tokens | Função |
|---|--------|---------|--------|------------|--------|
| 1 | Theo | `agents/theo.py` | sonnet (simples) / opus (complexo) | 6000 | Estrategista — briefing inicial, PRD textual |
| 2 | Designer PRD | `agents/designer_prd.py` | opus (complexo) / sonnet | 8000 | Arquiteto visual — define seções, paleta, animações |
| 3 | Arquiteto Mestre | `agents/arquiteto_mestre.py` | opus (todos níveis) | 8000 | Funde Theo + Designer em PRD unificado |
| 4 | Builder (OpenUI) | `agents/builder/agent.py` | claude-sonnet-4-6 | 64000 (4×18000) | Gera HTML chunked via OpenUI (Node.js port 3333) |
| 5 | Liz | `agents/liz.py` | haiku (simples) / sonnet (complexo) | 4000–8000 | Revisora de código — valida HTML gerado |
| 6 | Caio | `agents/caio.py` | haiku | 2000 | Qualificador — classifica lead por tier/score |
| 7 | Franz | `agents/bryan.py` | haiku | 4000 | SDR WhatsApp — outreach, follow-up, agendamento |
| — | Theo Tools | `agents/theo_tools.py` | — | — | Tools auxiliares do Theo |
| — | Bryan Tools | `agents/bryan_tools.py` | — | — | Tools auxiliares do Bryan (agendamento, etc.) |
| — | Arquiteto Tools | `agents/arquiteto_tools.py` | — | — | Tools auxiliares do Arquiteto |
| — | Agent RAG | `agents/agent_rag.py` | — | — | Retrieval-augmented generation context |
| — | Keyword Research | `agents/keyword_research.py` | — | — | Pesquisa de palavras-chave SEO |
| — | Liam | `agents/liam.py` | — | — | Gerador HTML legado — SUBSTITUÍDO pelo Builder OpenUI |

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
| Bryan Agent Loop | `agents/bryan_agent_loop.py` | Loop de agentes do Bryan |
| Liam Agent Loop | `agents/liam_agent_loop.py` | Loop de agentes do Liam (legado) |
| Theo Agent Loop | `agents/theo_agent_loop.py` | Loop de agentes do Theo |
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
| Token Tracker | `agents/token_tracker.py` | Rastreia consumo de tokens por agente |
| Pipeline Checkpoint | `agents/pipeline_checkpoint.py` | Checkpoints para retomada de pipeline |
| Unsplash Fetcher | `agents/unsplash_fetcher.py` | Busca imagens no Unsplash |
| Markdown PRD Parser | `agents/markdown_prd_parser.py` | Parseia PRDs em Markdown |
| LLM Direct | `agents/llm_direct.py` | Chamada direta a LLM (bypass router) |

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

Agentes são roteados dinamicamente por complexidade do lead:

| Complexidade | Score | Liam | Arquiteto | Theo | Liz | Bryan |
|-------------|-------|------|-----------|------|-----|-------|
| SIMPLES | 0–2 | sonnet | haiku | haiku | haiku | haiku |
| MÉDIO | 3–6 | opus | sonnet | haiku | haiku | haiku |
| COMPLEXO | 7+ | opus | sonnet | sonnet | haiku | haiku |

Nichos premium (restaurante, hotel, clínica, arquitetura, imobiliária, advocacia, odontologia) somam +3 no score.
Tier PREMIUM soma +3, STANDARD soma +1.

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
| Cron | `endpoints/cron_endpoints.py` | Cron endpoints (Bryan outreach) |
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
