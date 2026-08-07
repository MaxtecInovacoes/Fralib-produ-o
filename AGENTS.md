⚠️ INSTRUÇÕES CRÍTICAS PARA IA:
- Servidor oficial Backend: server.py (FastAPI, porta 8000)
- Servidor oficial OpenUI: ghcr.io/wandb/openui (Docker, porta 7878)
- Endpoints Pipeline: backend/endpoints/pipeline_endpoints.py
- Manager: backend/agents/manager/agent.py
- NÃO crie novos arquivos chamados server_v2, server_new, etc. Edite sempre os arquivos oficiais.
- PROIBIDO criar: tmp_*.py, fix_*.py, _debug_*.py, _test_*.py, server_v2*, server_chunked*
- Edição: 100% LOCAL em C:\fralib → git commit → git push → VPS faz git pull + rebuild
- NUNCA edite código direto na VPS via SSH/sed/cat/heredoc
- NUNCA envie scripts genéricos via SSH sem antes usar 'view_file' ou 'sed' com intervalo exato.

# Estado Atual do Sistema (2026-08-05)

## Pipeline REAL em Execução

```
Hunter → Caio → Jina → Unsplash → Arquiteto → Builder(proxy) → Deploy → Franz
```

**Orquestrador:** `backend/agents/manager/agent.py` (FSM, 7 steps)
**Builder atual:** `backend/agents/builder/agent.py` — proxy HTTP para OpenUI service (:7878)
**Orquestrador antigo:** `backend/services/pipeline_executors.py` — NÃO EXISTE MAIS

### Agentes ATIVOS no Pipeline

| Fase | Agente | Arquivo | Modelo | max_tokens | Função |
|------|--------|---------|--------|------------|--------|
| 1 | Hunter | `utils/agente1_hunter_v2.py` | Playwright | — | Captura leads via Google Maps |
| 2 | Caio | `agents/caio.py` | haiku | 2000 | Qualifica lead (tier/score) |
| 3 | Jina | `agents/jina_research.py` | sonnet | 1000 | Pesquisa de mercado + concorrência |
| 4 | Unsplash | `agents/unsplash_fetcher.py` | — | — | Download de fotos do nicho |
| 5 | Arquiteto | `agents/arquiteto_mestre.py` | sonnet | 8000 | Gera PRD (DesignerPRD schema) |
| 6 | Builder | `agents/builder/agent.py` | claude-sonnet-4-6 | 64000 | Gera HTML via OpenUI chunked |
| 7 | QA v2 | `agents/builder/quality_gate_v2/` | gpt-4o-mini | — | Vision QA + repair loop |
| 8 | Deploy | (inline no manager) | — | — | Salva HTML em /var/www/fralib/sites/ |
| 9 | Franz | `agents/franz/` | sonnet | 4000 | SDR WhatsApp outreach |

### Agentes EXISTEM MAS NÃO SÃO CHAMADOS no pipeline principal

- `agente_nicho.py` — análise de nicho (191 linhas)
- `agente_variacao.py` — variação estrutural (130 linhas)
- `backend/services/openui_renderer.py` — engine HTML in-process (853 linhas) — substituída por proxy HTTP
- `backend/services/builder_worker.py` — motion runtime (717 linhas) — não usado
- `backend/services/openui_contracts.py` — 12 animation systems (264 linhas) — não usado
- `backend/services/pipeline_builders.py` — orquestrador (677 linhas) — não usado

### Arquivos REMOVIDOS do código
- `agents/liam.py` — gerador HTML antigo (substituído por Builder)
- `agents/liam_models.py` — definição de modelos
- `agents/liam_seo.py` — SEO
- `agents/liam_tools.py` — tools auxiliares
- `agents/liam_lats.py` — Language Agent Tree Search
- `agents/liam_moa.py` — Mixture of Agents
- `agents/liam_constitutional.py` — Constitutional AI guardrails
- `agents/liam_agent_loop.py` — loop do Liam
- `backend/services/pipeline_executors.py` — orquestrador antigo (566 linhas)

### Schema Canônico: DesignerPRD
- `agents/designer_prd.py` (893 linhas) — **CONTRATO DE SCHEMA**
- Campos: `sections`, `color_palette`, `typography`, `animations`, `visual_dna`, `layout_blueprint`, `site_build_plan`, `visual_contract`
- Usado por: Arquiteto Mestre (gera), Builder (consome)
- **NOTA:** Arquiteto Mestre NÃO preenche todos os campos do DesignerPRD — apenas os básicos

### Infraestrutura de Deploy
- **API:** roda via systemd (`fralib-api.service`), containerless, porta 8001
- **OpenUI:** roda via systemd (`fralib-openui.service`), porta 7878
- **Worker:** roda via Docker Compose (`docker-compose.prod.yml`), container `fralib-worker-1`
- **Postgres/Redis:** via Docker Compose
- **Frontend build:**
  - `frontend/build.py` — gera `dashboard.html` e `landing.html`
  - `frontend/build_admin.py` — concatena partials em `admin.html` (6554 linhas)
  - Output: `/var/www/fralib/` (nginx serve)
- **StaticFiles server.py:** mount raiz `/` com `StaticFiles(directory="frontend", html=True)` (linha 372)
- **Paths VPS:** base é `/opt/fralib/` (não `/root/fralib/`)

### Observability (SISTEMA ATIVO)
- `backend/observability.py` — módulo principal de traces/spans
- Usado em: `manager/agent.py`, `pipeline_endpoints.py`, `rag_retriever.py`
- Endpoints: `endpoints/obs_endpoints.py` — dashboard em `/api/observability/dashboard`
- Funções: `Trace()`, `salvar_trace()`, `formatar_trace_log()`
- **Status:** ATIVO mas pouco visível — não está documentado na pipeline principal

### Crédito/Planos (SISTEMA ATIVO)
- `backend/services/credits_manager.py` — gerencia créditos
- Funções: `verificar_pode_executar`, `consume_tokens`, `validar_permissao_pipeline`, `consumir_credito_diario`
- Usado em: `pipeline_endpoints.py:68`
- **Status:** ATIVO — deduz créditos por pipeline executada

---

# Histórico: Pipeline Jun 22 (commit a9030deb)

## Pipeline de Geração (ordem de execução)

```
FASE 1  HUNTER           → Hunter captura leads (utils/agente1_hunter_v2.py)
FASE 2  CURADORIA/CAIO   → Qualifica lead — tier MORNO/STANDARD/PREMIUM (agents/caio.py)
FASE 3  JINA             → Pesquisa de mercado Jina AI (agents/jina_research.py)
FASE 4  INTELIGENCIA     → Análise de concorrência
FASE 5  FOTOS            → Download de fotos (agents/unsplash_fetcher.py)
FASE 6  NICHO            → Análise de nicho (agents/agente_nicho.py)
FASE 7  VARIACAO         → Variação estrutural (agents/agente_variacao.py)
FASE 8  ARQUITETO        → Gera DesignerPRD (agents/arquiteto_mestre.py)
FASE 9  BUILDER          → HTML via OpenUI (services/openui_renderer.py)
FASE 10 DEPLOY           → Site salvo em /var/www/fralib/sites/
FASE 11 FRANZ            → SDR outreach WhatsApp (agents/sdr_langgraph/)

Fonte: commit a9030deb (22 jun 2026) — pipeline funcional
Orquestrador: backend/services/pipeline_executors.py
```

## Agentes do Pipeline (ordem de execução)

| # | Agente | Arquivo | Modelo | max_tokens | Função |
|---|--------|---------|--------|------------|--------|
| 1 | Hunter | `utils/agente1_hunter_v2.py` | Playwright scraping | — | Valida/coleta lead_data via Google Maps |
| 2 | Caio | `agents/caio.py` | haiku | 2000 | Qualificador — classifica lead por tier/score |
| 3 | Arquiteto Mestre | `agents/arquiteto_mestre.py` | sonnet | 8000 | Gera PRD completo (seções, paleta OKLch, animações) |
| 4 | Builder (OpenUI) | `agents/builder/agent.py` | claude-sonnet-4-6 | 64000 (4×18000) | Gera HTML chunked via OpenUI (Node.js :7878) |
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
| Pipeline Error Log | `backend/core/pipeline_error_log.py` | Log estruturado de erro por step da pipeline |
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

Cada agente é um módulo Python. Esta tabela é a fonte de verdade para
entender o que cada arquivo faz, qual modelo LLM usa e em que fase do
pipeline ele roda.

## Pipeline de Geração (ordem de execução)

```
FASE 1  HUNTER           → Hunter captura leads (utils/agente1_hunter_v2.py)
FASE 2  CURADORIA/CAIO   → Qualifica lead — tier MORNO/STANDARD/PREMIUM (agents/caio.py)
FASE 3  JINA             → Pesquisa de mercado Jina AI (agents/jina_research.py)
FASE 4  INTELIGENCIA     → Análise de concorrência
FASE 5  FOTOS            → Download de fotos (agents/unsplash_fetcher.py)
FASE 6  NICHO            → Análise de nicho (agents/agente_nicho.py)
FASE 7  VARIACAO         → Variação estrutural (agents/agente_variacao.py)
FASE 8  ARQUITETO        → Gera DesignerPRD (agents/arquiteto_mestre.py)
FASE 9  BUILDER          → HTML via OpenUI (services/openui_renderer.py)
FASE 10 DEPLOY           → Site salvo em /var/www/fralib/sites/
FASE 11 FRANZ            → SDR outreach WhatsApp (agents/sdr_langgraph/)

Fonte: commit a9030deb (22 jun 2026) — pipeline funcional
Orquestrador: backend/services/pipeline_executors.py
```

## Agentes do Pipeline (ordem de execução)

| # | Agente | Arquivo | Modelo | max_tokens | Função |
|---|--------|---------|--------|------------|--------|
| 1 | Hunter | `utils/agente1_hunter_v2.py` | Playwright scraping | — | Valida/coleta lead_data via Google Maps |
| 2 | Caio | `agents/caio.py` | haiku | 2000 | Qualificador — classifica lead por tier/score |
| 3 | Arquiteto Mestre | `agents/arquiteto_mestre.py` | sonnet | 8000 | Gera PRD completo (seções, paleta OKLch, animações) |
| 4 | Builder (OpenUI) | `agents/builder/agent.py` | claude-sonnet-4-6 | 64000 (4×18000) | Gera HTML chunked via OpenUI (Node.js :7878) |
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
| Pipeline Error Log | `backend/core/pipeline_error_log.py` | Log estruturado de erro por step da pipeline |
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

## ⚠️ REGRAS ABSOLUTAS — NÃO REGREDIR

**Último restore funcional:** commit `a9030deb` (22 junho 2026 ~18:22)
**Documento:** `docs/RESTORE_JUNHO22_REFERENCE.md`

### Arquivos QUE NÃO PODEM ser removidos ou reescritos:

1. **`backend/services/pipeline_executors.py`** — Orquestrador das 11 fases. Se precisar mudar, edite este arquivo. NÃO substitua por steps simplificados.
2. **`backend/services/pipeline_phases.py`** — Define FASE_1_HUNTER → FASE_11_FRANZ + FraLibState (15+ campos). NÃO simplifique FraLibState.
3. **`backend/services/openui_renderer.py`** — Motor OpenUI que gera HTML completo. NÃO substitua por prompt genérico.
4. **`backend/services/openui_contracts.py`** — Contratos SEO/LGPD/motion injetados no prompt do OpenUI.
5. **`backend/agents/jina_research.py`** — Pesquisa de mercado Jina AI (Fase 3). NÃO remova.
6. **`backend/agents/arquiteto_mestre.py`** — Gera DesignerPRD via LLM (Fase 8).
7. **`backend/agents/caio.py`** — Qualifica lead (score, tier, paleta) (Fase 2).

### Regras de modificação:

1. **NUNCA remover arquivos da pipeline** sem antes verificar se são usados por `pipeline_executors.py`
2. **NUNCA simplificar FraLibState** — cada campo tem propósito (html_sections, html_final, jina_insights, briefing_theo, prd_arquiteto, etc)
3. **NUNCA substituir pipeline_executors.py** por steps simplificados — a orquestração das 11 fases é essencial
4. **ANTES de remover qualquer arquivo**, executar: `grep -r "arquivo_removido" backend/`
5. **SEMPRE documentar** mudanças na pipeline em `docs/RESTORE_JUNHO22_REFERENCE.md`
6. **SEMPRE testar** pipeline com lead real após mudanças: `POST /api/pipeline/executar?tenant_id=2&lead_id={id}`

### Como verificar integridade da pipeline:

```bash
# 1. Verificar que arquivos críticos existem
ls backend/services/pipeline_executors.py
ls backend/services/pipeline_phases.py
ls backend/services/openui_renderer.py
ls backend/agents/jina_research.py

# 2. Verificar que imports funcionam
python3 -c "from backend.services.pipeline_executors import executar_fase1_hunter"
python3 -c "from backend.services.pipeline_phases import TOTAL_FASES"
python3 -c "from backend.services.openui_renderer import OpenUIRenderer"
python3 -c "from backend.agents.jina_research import clean_json_response"

# 3. Testar pipeline com lead real
curl -N -H "Authorization: Bearer {token}" \
  "http://localhost:8000/api/pipeline/executar?tenant_id=2&lead_id={lead_id}"
```

### Rollback rápido:

Se a pipeline quebrar, restaurar commit de referência:
```bash
cd /root/repos/fralib
git show a9030deb:backend/services/pipeline_executors.py > /tmp/restore/pipeline_executors.py
git show a9030deb:backend/services/pipeline_phases.py > /tmp/restore/pipeline_phases.py
git show a9030deb:backend/services/openui_renderer.py > /tmp/restore/openui_renderer.py
git show a9030deb:backend/agents/jina_research.py > /tmp/restore/jina_research.py
```

