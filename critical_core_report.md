# FraLib Critical Core Audit
> Read-only. No files modified.

- **Scanned**: 443 .py files
- **Active**: 45
- **Orphaned**: 398
- **Clean**: 13 · **Warning**: 32 · **Critical**: 0

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
- `openui-service-wandb/backend/openui/server.py`

### LAYER_4_LEAD_SUPPLY (5)
- `backend/endpoints/credits_endpoints.py`
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
- `backend/endpoints/whatsapp_endpoints.py`

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

### backend/endpoints/credits_endpoints.py
- Layer: LAYER_4_LEAD_SUPPLY
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/dashboard_endpoints.py
- Layer: LAYER_5_ACTIVE_ROUTES
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/falhas_endpoints.py
- Layer: LAYER_5_ACTIVE_ROUTES
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/franz_insights_endpoints.py
- Layer: LAYER_3_AI_AGENTS
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED

### backend/endpoints/lead_supply_endpoints.py
- Layer: LAYER_4_LEAD_SUPPLY
- Critical: 0 · Warning: 1
- Issues: IMPORT_DUPLICATED


## Orphaned Files (first 100)

- `.git/hooks/check_v11_protection.py`
- `_quarantine_legacy/backend/api_monitor.py`
- `_quarantine_legacy/backend/domain/__init__.py`
- `_quarantine_legacy/backend/eval/__init__.py`
- `_quarantine_legacy/backend/eval/runner.py`
- `_quarantine_legacy/backend/eval/schemas.py`
- `_quarantine_legacy/backend/integration_healthcheck.py`
- `_quarantine_legacy/backend/observability.py`
- `_quarantine_legacy/backend/prd_cache.py`
- `_quarantine_legacy/backend/shared/password.py`
- `_quarantine_legacy/lead-pipeline/outreach/config.py`
- `_quarantine_legacy/lead-pipeline/outreach/config_reply.py`
- `_quarantine_legacy/lead-pipeline/outreach/pitch_sender.py`
- `_quarantine_legacy/lead-pipeline/outreach/reply_checker.py`
- `_quarantine_legacy/lead-pipeline/scraper/apify_scraper.py`
- `_quarantine_legacy/lead-pipeline/scraper/config.py`
- `_quarantine_legacy/lead-pipeline/sheets/google_sheets.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/agent-message/src/agent_message/__init__.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/agent-observe/src/agent_observe/__init__.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/attach-image/src/attach_image/__init__.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/attach-image/src/attach_image/attach_image.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/compact/src/compact/__init__.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/edit/src/edit/__init__.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/goal/src/goal/__init__.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/linear/src/linear/__init__.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/notion/src/notion/__init__.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/refine/src/refine/__init__.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/rlm-heartbeat/src/rlm_heartbeat/__init__.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/websearch/src/websearch/__init__.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/skills/websearch/src/websearch/websearch.py`
- `_quarantine_legacy/prime-agent/packages/coding-agent/test/fixtures/skills/python-skill/src/python_skill/__init__.py`
- `_quarantine_legacy/prime-agent/prime-agent-runtime/src/rlm/__init__.py`
- `_quarantine_legacy/prime-agent/prime-agent-runtime/src/rlm/harness.py`
- `_quarantine_legacy/prime-agent/prime-agent-runtime/src/rlm/mcp_base.py`
- `_quarantine_legacy/prime-agent/prime-agent-runtime/src/rlm/skill.py`
- `_quarantine_legacy/prime-agent/prime-agent-runtime/test/test_agent_message_skill.py`
- `_quarantine_legacy/prime-agent/prime-agent-runtime/test/test_harness.py`
- `_quarantine_legacy/prime-agent/prime-agent-runtime/test/test_mcp_base.py`
- `_quarantine_legacy/prime-agent/prime-agent-runtime/test/test_subagent_registry.py`
- `_quarantine_legacy/prime-agent/scripts/render-logo.py`
- `_quarantine_legacy/run_final_analysis.py`
- `_quarantine_legacy/tmp_reprocess_start_academia.py`
- `_quarantine_legacy/worker.py`
- `_quarantine_orphans.py`
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
- … and 298 more (see JSON)

---
Generated: critical_core_report.json + critical_core_report.md