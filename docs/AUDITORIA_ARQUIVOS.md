# FRAUILIB - AUDITORIA COMPLETA DE ARQUIVOS
> Gerado em: 2026-06-XX
> Baseado em: AGENTS.md, CLAUDE.md, README.md
> Objetivo: Identificar arquivos ATIVOS, LEGADO e ÓRFÃOS

---

## 📋 RESUMO EXECUTIVO

### Pipeline Canônica (11 fases)
1. **Hunter** - Captura leads
2. **Caio** - Qualificação determinística
3. **Jina** - Pesquisa de mercado
4. **Inteligência** - Assets consolidados
5. **Fotos** - Unsplash/Pexels
6. **Agente Nicho** - Briefing do nicho
7. **Agente Variação** - Estrutura visual
8. **Arquiteto Mestre** - DesignerPRD
9. **Builder Renderer** - **GERAÇÃO DO SITE**
10. **Quality Gate** - Validação
11. **Franz** - SDR WhatsApp

---

## 🏛️ ARQUITETURA - SERVIÇOS (backend/services/)

### ✅ SERVIÇOS ATIVOS (USADOS NO PIPELINE)

| Arquivo | Função | Status |
|---------|--------|--------|
| `openui_renderer.py` | **GERADOR PADRÃO de sites HTML** | ✅ ATIVO |
| `builder_worker.py` | Orquestra OpenUI vs Vite/React | ✅ ATIVO |
| `pipeline_phases.py` | Enum das 11 fases | ✅ ATIVO |
| `pipeline_executors.py` | Execução das fases | ✅ ATIVO |
| `lgpd_injector.py` | Banner LGPD | ✅ ATIVO |
| `html_sanitizer.py` | Fecha tags órfãs | ✅ ATIVO |
| `html_quality_gate.py` | Quality Gate | ✅ ATIVO |
| `html_builder_repair.py` | Reparos determinísticos | ✅ ATIVO |
| `openui_contracts.py` | 7 contratos injetados | ✅ ATIVO |
| `tracing.py` | Observabilidade (Sprint 5) | ✅ ATIVO |
| `template_loader.py` | Templates estáticos | ✅ ATIVO |
| `template_embeddings.py` | RAG semântico (Sprint 7) | ✅ ATIVO |
| `auto_improve.py` | Auto-melhoria (Sprint 8) | ✅ ATIVO |
| `edge_cases.py` | Hardening (Sprint 9) | ✅ ATIVO |
| `service_manager.py` | Gerencia serviços systemd | ✅ ATIVO |
| `job_queue.py` | Fila PostgreSQL | ✅ ATIVO |
| `llm_direct.py` | Chamadas LLM | ✅ ATIVO |
| `llm_router.py` | Roteamento LLM | ✅ ATIVO |
| `pipeline_state.py` | Estado da pipeline | ✅ ATIVO |
| `pipeline_prd_builder.py` | Constrói PRD | ✅ ATIVO |
| `agent_memory.py` | Memória 3-tier | ✅ ATIVO |

### ⚠️ SERVIÇOS LEGADO (COMPATIBILIDADE)

| Arquivo | Função | Status | Obsoleto desde |
|---------|--------|--------|----------------|
| `vite_react_renderer.py` | Vite/React (ERA padrão) | ⚠️ LEGADO | Sprint 12.9 |
| `vite_config.py` | Config Vite | ⚠️ LEGADO | Sprint 12.9 |
| `vite_config_helpers.py` | Helpers Vite | ⚠️ LEGADO | Sprint 12.9 |
| `vite_facts.py` | Facts Vite | ⚠️ LEGADO | Sprint 12.9 |
| `vite_file_extractor.py` | Extractor Vite | ⚠️ LEGADO | Sprint 12.9 |
| `vite_modules.py` | Módulos Vite | ⚠️ LEGADO | Sprint 12.9 |
| `vite_renderer_models.py` | Models Vite | ⚠️ LEGADO | Sprint 12.9 |
| `vite_validator.py` | Validador Vite | ⚠️ LEGADO | Sprint 12.9 |
| `vite_templates.py` | Templates Vite | ⚠️ LEGADO | Sprint 12.9 |
| `vite_prompts.py` | Prompts Vite | ⚠️ LEGADO | Sprint 12.9 |
| `vite_build_executor.py` | Executor Vite | ⚠️ LEGADO | Sprint 12.9 |
| `vite_block_registry.py` | Registry Vite | ⚠️ LEGADO | Sprint 12.9 |
| `vite_visual_lanes.py` | Visual lanes Vite | ⚠️ LEGADO | Sprint 12.9 |
| `vite_theme_guard.py` | Theme guard Vite | ⚠️ LEGADO | Sprint 12.9 |
| `pipeline_renderer_support.py` | Support de publicação | ⚠️ LEGADO | Renomeado |
| `pipeline_publication_support.py` | Suporte publicação | ⚠️ LEGADO | - |

### ❌ SERVIÇOS PROIBIDOS (NUNCA USAR)

| Arquivo | Motivo |
|---------|--------|
| `liam_renderer.py` | PROIBIDO - não existe mais |
| `skill_based_renderer.py` | PROIBIDO - não existe mais |

### 🔧 SERVIÇOS AUXILIARES (ATIVOS)

| Arquivo | Função |
|---------|--------|
| `cache_service.py` | Cache |
| `token_bucket.py` | Rate limiting |
| `circuit_breaker.py` | Proteção |
| `error_diagnostics.py` | Diagnóstico |
| `alerting.py` | Alertas |
| `credits_manager.py` | Créditos |
| `email_service.py` | E-mail |
| `whatsapp_automation_service.py` | WhatsApp |
| `outbound_queue.py` | Fila outbound |
| `sdr_gateway.py` | Gateway SDR |
| `retargeting.py` | Retargeting |
| `closer_queue.py` | Fila de fechamento |

---

## 👥 AGENTES (backend/agents/)

### ✅ AGENTES ATIVOS (USAM LLM)

| Arquivo | Fase | LLM | Custo |
|---------|------|-----|-------|
| `agente_nicho.py` | 6 | Sonnet | ~5% |
| `agente_variacao.py` | 7 | Sonnet (fallback) | ~5% |
| `arquiteto_mestre.py` | 8 | Sonnet (orquestrador) | ~20% |
| `openui_renderer.py` | 9 | Sonnet | ~70% |
| `sdr_langgraph/agent.py` | 11 | Sonnet | ~5% |

### ✅ AGENTES DETERMINÍSTICOS (SEM LLM)

| Arquivo | Função |
|---------|--------|
| `caio.py` | Qualificação (scoring) |
| `html_quality_gate.py` | Validação regex |
| `html_builder_repair.py` | Reparos string |
| `site_prompt_agent.py` | Monta prompt (SEM LLM) |

### ⚠️ AGENTES LEGADO

| Arquivo | Status |
|---------|--------|
| `design_director.py` | Substituído por variation |
| `design_context.py` | Substituído |
| `design_tokens.py` | Substituído |
| `design_system_injector.py` | Substituído |
| `design_system_selector.py` | Substituído |
| `design_systems_library.py` | Substituído |
| `design_guidelines.py` | Substituído |
| `design_prompts.py` | Substituído |
| `visual_archetypes.py` | Substituído |
| `visual_contract_gate.py` | Legado |

### ❓ AGENTES AVALIAR (POTENCIALMENTE ÓRFÃOS)

| Arquivo | Necessidade |
|---------|-------------|
| `bloco_copy.py` | Verificar se usado |
| `bloco_estrutura.py` | Verificar se usado |
| `craft_rules.py` | Verificar uso |
| `seo_context.py` | Verificar uso |
| `hero_styles.py` | Verificar uso |
| `sub_nicho.py` | Verificar uso |
| `nicho_data.py` | Verificar uso |
| `prompts_arquiteto.py` | Verificar uso |
| `markdown_prd_parser.py` | Verificar uso |
| `benchmarker.py` | Verificar uso |
| `trend_watcher.py` | Verificar uso |
| `agent_rag.py` | Verificar uso |
| `validation_layer.py` | Verificar uso |
| `validation_enforcer.py` | Verificar uso |

---

## 🗄️ CORE (backend/core/)

### ✅ CORE ATIVO

| Arquivo | Função |
|---------|--------|
| `job_queue.py` | Fila PostgreSQL com claim |
| `database.py` | Conexão DB |
| `auth.py` | Autenticação |
| `access_control.py` | Controle acesso |
| `config.py` | Configuração |
| `proxy_models.py` | Modelos proxy LLM |
| `llm_config.py` | Config LLM |

---

## 🌐 ENDPOINTS (backend/endpoints/)

### ✅ ENDPOINTS PRINCIPAIS (ATIVOS)

| Arquivo | Função |
|---------|--------|
| `pipeline_orchestrator_service.py` | Orquestrador |
| `pipeline_start_endpoints.py` | Iniciar pipeline |
| `pipeline_status_endpoints.py` | Status |
| `pipeline_endpoints.py` | Endpoints pipeline |
| `leads_endpoints.py` | CRUD leads |
| `leads_crud.py` | Operações leads |
| `queue_endpoints.py` | Status fila |
| `health_endpoints.py` | Health check |
| `auth_endpoints.py` | Autenticação |

### ⚠️ ENDPOINTS LEGADO/POTENCIALMENTE ÓRFÃOS

| Arquivo | Status |
|---------|--------|
| `blog_endpoints.py` | Avaliar |
| `facebook_ads_endpoints.py` | Avaliar |
| `dashboard_endpoints.py` | Redirecionar para admin |
| `beta_endpoints.py` | Avaliar |
| `automation_endpoints.py` | Avaliar |
| `competitive_intelligence.py` | Avaliar |
| `retargeting_endpoints.py` | Avaliar |
| `linkedin_outreach.py` | Avaliar |
| `crm_integration.py` | Avaliar |
| `cron_endpoints.py` | Avaliar |
| `cron_outreach_endpoints.py` | Avaliar |

---

## 📁 SCRIPTS (scripts/)

### ✅ SCRIPTS ATIVOS

| Script | Função |
|--------|--------|
| `pipeline_smoke.py` | Diagnóstico dry-run |
| `check_deploy_contract.py` | Bloqueia frontend divergente |
| `verify_frontend_canonical.py` | Verifica frontend |
| `test_regression.py` | Teste E2E |
| `post-receive` | Hook de deploy |
| `builder_worker_job.py` | Job isolado |
| `repair_provider_key.py` | Reparo chave LLM |

### ❓ SCRIPTS LEGADO/AVALIAR

| Script | Status |
|--------|--------|
| `test_build_only.py` | TESTE ÓRFÃO DO VITE |
| `test_builder_llm_only.py` | TESTE ÓRFÃO DO VITE |
| `check_uncommitted.sh` | Legado |

---

## 🧪 TESTES (tests/)

### ✅ TESTES ATIVOS

| Teste | Cobertura |
|-------|-----------|
| `test_regression_patches.py` | 46 patches |
| `test_anti_regressao_v114.py` | v1.14 |
| `test_pipeline_builders_contract.py` | Contrato |
| `test_builder_publication_phase6_contract.py` | Publicação |
| `test_site_editor_security.py` | Segurança |
| `test_pipeline_route_contract.py` | Rotas |
| `test_security_scalability_contract.py` | Segurança |
| `test_html_quality_gate.py` | Quality Gate |
| `test_idor_multitenant.py` | IDOR/Tenant |
| `test_job_queue_concurrency.py` | Concorrência |

### ⚠️ TESTES LEGADO VITE

| Teste | Status |
|-------|--------|
| `unit/test_vite_config.py` | TESTE ÓRFÃO |
| `unit/test_vite_config_helpers.py` | TESTE ÓRFÃO |
| `unit/test_vite_facts.py` | TESTE ÓRFÃO |
| `unit/test_vite_file_extractor.py` | TESTE ÓRFÃO |
| `unit/test_vite_renderer_models.py` | TESTE ÓRFÃO |
| `unit/test_vite_validator.py` | TESTE ÓRFÃO |

---

## 📊 FLUXO CANÔNICO (Hunter → Deploy)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PIPELINE CANÔNICA                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [1] HUNTER (utils/agente1_hunter_v2.py)                               │
│      └─ Scraping Google Maps                                             │
│      └─ Captura leads                                                    │
│                                                                          │
│  [2] CAIO (agents/caio.py)                                              │
│      └─ Scoring determinístico                                           │
│      └─ Qualifica lead                                                   │
│                                                                          │
│  [3] JINA (utils/jina_intelligence.py)                                  │
│      └─ Web scraping + LLM                                              │
│      └─ Pesquisa concorrência                                           │
│                                                                          │
│  [4] INTELIGÊNCIA (endpoints/pipeline_lead_flow_helpers.py)            │
│      └─ Consolida assets                                                  │
│                                                                          │
│  [5] FOTOS (agents/unsplash_fetcher.py, pexels_video.py)                │
│      └─ Baixa fotos/vídeos                                              │
│                                                                          │
│  [6] AGENTE NICHO (agents/agente_nicho.py)                              │
│      └─ Gera NichoBriefing via LLM Sonnet                              │
│                                                                          │
│  [7] AGENTE VARIAÇÃO (agents/agente_variacao.py)                        │
│      └─ Template por subnicho (8 mapeados)                              │
│      └─ Fallback LLM                                                    │
│                                                                          │
│  [8] ARQUITETO MESTRE (services/pipeline_fases/fase_08_arquiteto.py)   │
│      └─ Orquestrador: 1 call + 2 bloco_estrutura + 4 bloco_copy        │
│      └─ ~7 calls LLM/lead                                               │
│                                                                          │
│  [9] BUILDER RENDERER                                                    │
│      ├─ PADRÃO: openui_renderer.py → HTML estático                      │
│      └─ FALLBACK: vite_react_renderer.py → React (LEGADO)              │
│                                                                          │
│  [9b] QUALITY GATE (agents/html_quality_gate.py)                        │
│      └─ Loop ≤ 3 retries                                                │
│      └─ Validação determinística (regex + lxml)                         │
│                                                                          │
│  [10] DEPLOY (endpoints/pipeline_phase_helpers.py)                       │
│      └─ Publica em /var/www/fralib/sites/<tenant>/<slug>/             │
│      └─ Git post-receive hook                                           │
│                                                                          │
│  [11] FRANZ (agents/sdr_langgraph/agent.py)                            │
│      └─ SDR WhatsApp via LangGraph                                      │
│      └─ 2 calls/turno                                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔴 PROBLEMAS IDENTIFICADOS

### 1. CACHE GLOBAL SEM TENANT (CRÍTICO)
- `keyword_cache` - global (deveria ser por tenant)
- `jina_cache` - global
- `design_director_cache` - global
- `unsplash_cache` - global
- `pexels_cache` - global
- `prd_cache` - global

### 2. ARQUIVOS VITE LEGADO (AVALIAR)
- 14 arquivos em `backend/services/vite_*.py`
- 6 testes unitários em `tests/unit/test_vite_*.py`
- 2 scripts de teste em `scripts/test_*.py`

### 3. DIVERGÊNCIA UI
- `admin.html` - canônico
- `dashboard.html` - LEGADO (deve redirecionar)
- `/dashboard` - LEGADO (deve redirecionar)

### 4. 74 AGENTES? MITO!
- São 11 módulos-agente de verdade
- 5 usam LLM
- 6 são determinísticos
- O resto são helpers/utilitários

---

## ✅ AÇÕES RECOMENDADAS

### PRIORIDADE ALTA
1. ✅ Manter OpenUI como padrão (funcionando)
2. ✅ Manter Quality Gate (bloqueia publish ruim)
3. ✅ Manter 46 patches aplicados
4. ⚠️ Avaliar se Vite/React legado pode ser removido
5. ⚠️ Corrigir caches globais para escopo tenant

### PRIORIDADE MÉDIA
1. 🔧 Verificar 20+ arquivos de agentes não utilizados
2. 🔧 Consolidar endpoints duplicados
3. 🔧 Limpar testes órfãos Vite

### PRIORIDADE BAIXA
1. 📝 Documentar melhor cada agente
2. 📝 Criar mapa de dependências

---

## 📈 MÉTRICAS DO SISTEMA

| Métrica | Valor |
|---------|-------|
| Total arquivos .py backend | 206 |
| Arquivos em agents/ | 74 + sdr_langgraph/ |
| Módulos-agente reais | 11 |
| Agentes com LLM | 5 |
| Agentes determinísticos | 6 |
| Custo LLM dominado por | OpenUI (~70%) |
| 46 patches aplicados | ✅ Ativos |
| Testes verdes | 130+ |
