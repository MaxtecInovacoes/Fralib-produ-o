# FraLib Critical Core Audit
> Read-only. No files modified.

- **Scanned**: 441 .py files
- **Active**: 45
- **Orphaned**: 396
- **Clean**: 13 · **Warning**: 29 · **Critical**: 3

## Discovered Entrypoints

- `server.py` — ✅
- `backend/agent_router.py` — ✅
- `backend/pipeline_queue_manager.py` — ✅
- `backend/pipeline_ledger.py` — ✅
- `backend/dreaming_job.py` — ✅
- `backend/whatsapp_listener.py` — ✅
- `backend/agents/manager/agent.py` — ✅
- `backend/services/lead_supply_engine.py` — ✅
- `openui-service-wandb/backend/openui/server.py` — ✅
- `backend/endpoints/__init__.py` — ✅
- `backend/endpoints/abtest_endpoints.py` — ✅
- `backend/endpoints/admin_pipeline_control_endpoints.py` — ✅
- `backend/endpoints/agent_config_endpoints.py` — ✅
- `backend/endpoints/agentes_endpoints.py` — ✅
- `backend/endpoints/api_usage_endpoints.py` — ✅
- `backend/endpoints/auth_endpoints.py` — ✅
- `backend/endpoints/beta_endpoints.py` — ✅
- `backend/endpoints/blog_endpoints.py` — ✅
- `backend/endpoints/credits_endpoints.py` — ✅
- `backend/endpoints/cron_endpoints.py` — ✅
- `backend/endpoints/dashboard_endpoints.py` — ✅
- `backend/endpoints/falhas_endpoints.py` — ✅
- `backend/endpoints/franz_insights_endpoints.py` — ✅
- `backend/endpoints/lead_supply_endpoints.py` — ✅
- `backend/endpoints/leads_endpoints.py` — ✅
- `backend/endpoints/llm_endpoints.py` — ✅
- `backend/endpoints/obs_endpoints.py` — ✅
- `backend/endpoints/pipeline_crud.py` — ✅
- `backend/endpoints/pipeline_edit_endpoints.py` — ✅
- `backend/endpoints/pipeline_endpoints.py` — ✅
- `backend/endpoints/pipeline_trigger.py` — ✅
- `backend/endpoints/provider_alerts_endpoints.py` — ✅
- `backend/endpoints/provider_keys_endpoints.py` — ✅
- `backend/endpoints/queue_endpoints.py` — ✅
- `backend/endpoints/site_editor_endpoints.py` — ✅
- `backend/endpoints/sse_endpoints.py` — ✅
- `backend/endpoints/superadmin_endpoints.py` — ✅
- `backend/endpoints/tracking_endpoints.py` — ✅
- `backend/endpoints/users_endpoints.py` — ✅
- `backend/endpoints/whatsapp_endpoints.py` — ✅

## Active Files by Layer

### LAYER_1_CORE_DATABASE (1)
- `backend/endpoints/auth_endpoints.py`

### LAYER_2_PIPELINE_ENGINE (7)
- `backend/endpoints/admin_pipeline_control_endpoints.py`
- `backend/endpoints/pipeline_crud.py`
- `backend/endpoints/pipeline_edit_endpoints.py`
- `backend/endpoints/pipeline_endpoints.py`
- `backend/endpoints/pipeline_trigger.py`
- `backend/pipeline_ledger.py`
- `backend/pipeline_queue_manager.py`

### LAYER_3_AI_AGENTS (7)
- `backend/agent_router.py`
- `backend/agents/__init__.py`
- `backend/agents/manager/agent.py`
- `backend/endpoints/agent_config_endpoints.py`
- `backend/endpoints/agentes_endpoints.py`
- `backend/endpoints/franz_insights_endpoints.py`
- `openui-service-wandb/backend/openui/server.py` 🚩

### LAYER_4_LEAD_SUPPLY (5)
- `backend/endpoints/credits_endpoints.py` 🚩
- `backend/endpoints/lead_supply_endpoints.py`
- `backend/endpoints/provider_alerts_endpoints.py`
- `backend/endpoints/provider_keys_endpoints.py`
- `backend/services/lead_supply_engine.py`

### LAYER_5_ACTIVE_ROUTES (18)
- `backend/endpoints/__init__.py`
- `backend/endpoints/abtest_endpoints.py`
- `backend/endpoints/api_usage_endpoints.py`
- `backend/endpoints/beta_endpoints.py`
- `backend/endpoints/blog_endpoints.py`
- `backend/endpoints/cron_endpoints.py`
- `backend/endpoints/dashboard_endpoints.py`
- `backend/endpoints/falhas_endpoints.py`
- `backend/endpoints/leads_endpoints.py`
- `backend/endpoints/llm_endpoints.py`
- `backend/endpoints/obs_endpoints.py`
- `backend/endpoints/queue_endpoints.py`
- `backend/endpoints/site_editor_endpoints.py`
- `backend/endpoints/sse_endpoints.py`
- `backend/endpoints/superadmin_endpoints.py`
- `backend/endpoints/tracking_endpoints.py`
- `backend/endpoints/users_endpoints.py`
- `backend/endpoints/whatsapp_endpoints.py` 🚩

### LAYER_6_SCHEMAS_CONTRACTS (0)

### LAYER_UNCLASSIFIED (7)
- `backend/__init__.py`
- `backend/core/__init__.py`
- `backend/dreaming_job.py`
- `backend/services/__init__.py`
- `backend/utils/__init__.py`
- `backend/whatsapp_listener.py`
- `server.py`


## Top Priority Fixes

### backend/endpoints/credits_endpoints.py
- Layer: LAYER_4_LEAD_SUPPLY
- Critical: 1 · Warning: 1
- Issues: ASYNC_DB_SYNC_MISMATCH, IMPORT_DUPLICATED

### backend/endpoints/whatsapp_endpoints.py
- Layer: LAYER_5_ACTIVE_ROUTES
- Critical: 1 · Warning: 1
- Issues: ASYNC_DB_SYNC_MISMATCH, IMPORT_DUPLICATED

### openui-service-wandb/backend/openui/server.py
- Layer: LAYER_3_AI_AGENTS
- Critical: 1 · Warning: 1
- Issues: ASYNC_DB_SYNC_MISMATCH, IMPORT_DUPLICATED

### backend/endpoints/pipeline_endpoints.py
- Layer: LAYER_2_PIPELINE_ENGINE
- Critical: 0 · Warning: 3
- Issues: HTML_FRAGILE_REGEX, IMPORT_DUPLICATED, JSON_BLIND_TRUNCATION

### backend/dreaming_job.py
- Layer: LAYER_UNCLASSIFIED
- Critical: 0 · Warning: 2
- Issues: HTML_FRAGILE_REGEX, JSON_BLIND_TRUNCATION

### backend/endpoints/site_editor_endpoints.py
- Layer: LAYER_5_ACTIVE_ROUTES
- Critical: 0 · Warning: 2
- Issues: HTML_FRAGILE_REGEX, IMPORT_DUPLICATED

### backend/endpoints/sse_endpoints.py
- Layer: LAYER_5_ACTIVE_ROUTES
- Critical: 0 · Warning: 2
- Issues: IMPORT_DUPLICATED, JSON_BLIND_TRUNCATION

### backend/endpoints/superadmin_endpoints.py
- Layer: LAYER_5_ACTIVE_ROUTES
- Critical: 0 · Warning: 2
- Issues: IMPORT_DUPLICATED, JSON_BLIND_TRUNCATION

### backend/whatsapp_listener.py
- Layer: LAYER_UNCLASSIFIED
- Critical: 0 · Warning: 2
- Issues: HTML_FRAGILE_REGEX, IMPORT_DUPLICATED

### backend/agents/manager/agent.py
- Layer: LAYER_3_AI_AGENTS
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/abtest_endpoints.py
- Layer: LAYER_5_ACTIVE_ROUTES
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/admin_pipeline_control_endpoints.py
- Layer: LAYER_2_PIPELINE_ENGINE
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/agent_config_endpoints.py
- Layer: LAYER_3_AI_AGENTS
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/agentes_endpoints.py
- Layer: LAYER_3_AI_AGENTS
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/api_usage_endpoints.py
- Layer: LAYER_5_ACTIVE_ROUTES
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/auth_endpoints.py
- Layer: LAYER_1_CORE_DATABASE
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/beta_endpoints.py
- Layer: LAYER_5_ACTIVE_ROUTES
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/blog_endpoints.py
- Layer: LAYER_5_ACTIVE_ROUTES
- Critical: 0 · Warning: 1
- Issues: HTML_FRAGILE_REGEX

### backend/endpoints/dashboard_endpoints.py
- Layer: LAYER_5_ACTIVE_ROUTES
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/falhas_endpoints.py
- Layer: LAYER_5_ACTIVE_ROUTES
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED


## Orphaned Files (first 100)

- `.git/hooks/check_v11_protection.py`
- `alembic/env.py`
- `alembic/versions/b278e17c0c0c_initial_schema.py`
- `alembic/versions/baseline_real_prod.py`
- `alembic/versions/fase4_multitenant_hardening.py`
- `alembic/versions/provider_alerts.py`
- `alembic/versions/provider_keys.py`
- `audit_codebase.py`
- `auto_fix_mechanical.py`
- `backend/agent_memory.py`
- `backend/agents/agent_rag.py`
- `backend/agents/agente_nicho.py`
- `backend/agents/agente_variacao.py`
- `backend/agents/animation_injector.py`
- `backend/agents/animation_profile.py`
- `backend/agents/arquiteto_agent_loop.py`
- `backend/agents/arquiteto_mestre.py`
- `backend/agents/arquiteto_tools.py`
- `backend/agents/artifact_store.py`
- `backend/agents/benchmarker.py`
- `backend/agents/bloco_copy.py`
- `backend/agents/bloco_estrutura.py`
- `backend/agents/brain.py`
- `backend/agents/builder/agent.py`
- `backend/agents/builder/quality_gate_v2/inject.py`
- `backend/agents/builder/quality_gate_v2/seo_geo_enricher.py`
- `backend/agents/builder_contract_utils.py`
- `backend/agents/caio.py`
- `backend/agents/cinematic_post_processor.py`
- `backend/agents/color_enforcer.py`
- `backend/agents/color_extractor.py`
- `backend/agents/component_library.py`
- `backend/agents/craft_rules.py`
- `backend/agents/design_context.py`
- `backend/agents/design_director.py`
- `backend/agents/design_guidelines.py`
- `backend/agents/design_prompts.py`
- `backend/agents/design_system_injector.py`
- `backend/agents/design_system_selector.py`
- `backend/agents/design_systems_library.py`
- `backend/agents/design_tokens.py`
- `backend/agents/designer_prd.py`
- `backend/agents/few_shot_examples.py`
- `backend/agents/franz/__init__.py`
- `backend/agents/franz/agent.py`
- `backend/agents/franz/conversion_axes.py`
- `backend/agents/franz/franz_agent_loop.py`
- `backend/agents/franz/franz_tools.py`
- `backend/agents/handoff_types.py`
- `backend/agents/hero_styles.py`
- `backend/agents/html_builder_repair.py`
- `backend/agents/html_content_validator.py`
- `backend/agents/html_contract_validator.py`
- `backend/agents/html_media_validator.py`
- `backend/agents/html_phase6_repair.py`
- `backend/agents/html_publication_helpers.py`
- `backend/agents/html_quality_gate.py`
- `backend/agents/hunter/__init__.py`
- `backend/agents/hunter/agent.py`
- `backend/agents/jina_research.py`
- `backend/agents/keyword_research.py`
- `backend/agents/lgpd_personalized.py`
- `backend/agents/liam_agent_loop.py`
- `backend/agents/liz.py`
- `backend/agents/liz_rubricas.py`
- `backend/agents/llm_agent_config.py`
- `backend/agents/llm_anthropic.py`
- `backend/agents/llm_client.py`
- `backend/agents/llm_config.py`
- `backend/agents/llm_context.py`
- `backend/agents/llm_direct.py`
- `backend/agents/llm_openai.py`
- `backend/agents/llm_providers.py`
- `backend/agents/llm_router.py`
- `backend/agents/llm_tracking.py`
- `backend/agents/manager/states.py`
- `backend/agents/manager/step_arquiteto.py`
- `backend/agents/manager/step_builder.py`
- `backend/agents/manager/step_caio.py`
- `backend/agents/manager/step_deploy.py`
- `backend/agents/manager/step_design_director.py`
- `backend/agents/manager/step_franz.py`
- `backend/agents/manager/step_hunter.py`
- `backend/agents/manager/step_nicho.py`
- `backend/agents/manager/step_quality_gate.py`
- `backend/agents/manager/step_variacao.py`
- `backend/agents/markdown_prd_parser.py`
- `backend/agents/memory.py`
- `backend/agents/niche_resolver.py`
- `backend/agents/nicho_data.py`
- `backend/agents/open_design_selector.py`
- `backend/agents/pexels_video.py`
- `backend/agents/pipeline_checkpoint.py`
- `backend/agents/pipeline_identity.py`
- `backend/agents/pipeline_learning.py`
- `backend/agents/prompt_agent_builder.py`
- `backend/agents/prompt_agent_context.py`
- `backend/agents/prompt_agent_helpers.py`
- `backend/agents/prompts_arquiteto.py`
- `backend/agents/requirements_contract.py`
- … and 296 more (see JSON)

---
Generated: critical_core_report.json + critical_core_report.md