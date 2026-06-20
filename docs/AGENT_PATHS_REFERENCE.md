# Agent Paths Reference

This reference lists the active FraLib agents and services by runtime role.

## Lead Supply Hunter

- Purpose: collect candidate leads for a tenant/niche/city.
- Main files: `backend/services/lead_supply_engine.py`,
  `backend/utils/agente1_hunter_v2.py`, `backend/endpoints/lead_supply_endpoints.py`.
- Input: tenant id, niche, city, quantity, score thresholds.
- Output: candidates in `lead_inventory`.
- Success: enough candidates exist for Caio to qualify.
- Failure handling: provider timeout or empty result should not block all
  tenants; retry or switch provider through approved router/playbook.

## Caio Qualification

- Purpose: deterministic lead qualification before spending Builder/LLM budget.
- Main files: `backend/agents/caio.py`, `backend/agents/caio_SKILL.md`.
- Input: candidate lead data.
- Output: score, tier, reason, approved/rejected decision.
- Success: only approved leads move to production queue.
- Failure handling: if rejection rate spikes, inspect reasons before lowering
  score thresholds.

## Production Tick

- Purpose: reserve one approved lead and enqueue a production pipeline.
- Main files: `backend/services/lead_supply_engine.py`, `worker.py`,
  `backend/core/job_queue.py`.
- Input: tenant, approved inventory, plan/cooldown/credit state.
- Output: `pipeline_lead` job.
- Success: one lead moves forward without mixing tenants.
- Failure handling: blocked by no credits, cooldown, plan, missing WhatsApp or
  active tenant job.
- Canonical state: reservation lives in `lead_inventory`; execution lives in
  `jobs`; do not use `pipeline_queue`.

## Jina And Market Intelligence

- Purpose: collect neutral market signals, competitors, PAA and services.
- Main files: `backend/agents/jina_research.py`,
  `backend/agents/keyword_research.py`, `backend/agents/seo_context.py`.
- Input: lead, segment, city, business name and confirmed facts.
- Output: insights for prompt/copy/SEO.
- Success: prompt has factual market context without invented claims.
- Failure handling: use cached or reduced context rather than inventing facts.

## Prompt Agent

- Purpose: create the premium Builder brief while preserving facts.
- Main files: `backend/agents/site_prompt_agent.py`,
  `backend/agents/creative_build_brief.py`,
  `backend/agents/site_build_plan.py`, `backend/agents/niche_resolver.py`.
- Input: qualified lead, market intelligence, design DNA, archetype and media.
- Output: Builder prompt/contract.
- Success: technical instructions may be in English, but all customer-facing
  site copy is pt-BR, niche-specific, factual and leaves Builder free to
  compose the final UI.
- Failure handling: reject mixed language, invented claims or missing required
  site contracts.

## Builder Renderer

- Purpose: run Vite/React Builder and accept the real built artifact.
- Main files: `backend/services/builder_worker.py`,
  `backend/services/vite_react_renderer.py`,
  `backend/services/openui_renderer.py`.
- Input: Builder prompt, tenant id, job id, target.
- Output: `src/`, `dist/index.html`, manifest and public site assets.
- Success: `dist/index.html` compiles and contains required contracts.
- Failure handling: retry from checkpoint or fail with clear phase; do not fall
  back to a simpler renderer that hides missing contracts.

## Visual And HTML Contracts

- Purpose: block regressions in generated sites.
- Main files: `backend/agents/html_quality_gate.py`,
  `backend/agents/visual_contract_gate.py`,
  `tests/unit/test_phase6_contracts.py`.
- Input: generated artifact and expected contract.
- Output: pass/fail with actionable missing marker.
- Success: Fase 6 visual, SEO, a11y, performance and theme markers are present.
- Failure handling: fix root cause or Builder prompt; do not publish a weaker
  site as replacement.

## Deploy

- Purpose: publish the built site and frontend from Git-controlled source.
- Main files: `backend/endpoints/pipeline_orchestrator_service.py`,
  deploy hook on VPS, `frontend/build.py`.
- Input: approved `dist` artifact and tenant/slug.
- Output: public URL and versioned deployment.
- Success: `/api/version` returns deployed commit and generated site is served.
- Failure handling: inspect hook logs and publish path; never copy manually to
  `/var/www/fralib`.

## Franz/SDR

- Purpose: reactive WhatsApp follow-up when the plan allows SDR.
- Main files: `backend/services/sdr_gateway.py`,
  `backend/endpoints/whatsapp_endpoints.py`, SDR LangGraph modules under
  `backend/agents/` or current SDR package when present.
- Input: lead, public site URL, tenant identity and conversation history.
- Output: WhatsApp message/status.
- Success: message is tenant-scoped and the trial credit is consumed only after
  send.
- Failure handling: disconnected WhatsApp blocks or delays SDR; do not consume
  trial lead before the required send event.

## Credits And Plans

- Purpose: enforce payment, credits, cooldown and plan features.
- Main files: `backend/endpoints/credits_endpoints.py`,
  `backend/services/credits_manager.py`, `docs/MERCADO_PAGO_SEGURANCA_PLANO.md`.
- Input: user action, plan, Mercado Pago event or reconciliation.
- Output: credit balance, subscription status, cooldown and plan capabilities.
- Success: credits are idempotent and tenant-scoped.
- Failure handling: reconcile payment by backend script/API; never trust a
  frontend-only payment status.
- Canonical state: permission, cooldown, credit and SDR decisions read
  `users.plano`. `users.plan` is compatibility only.

## Auth And Tenant Isolation

- Purpose: keep sessions, CSRF and tenant boundaries intact.
- Main files: `backend/endpoints/auth_endpoints.py`, `backend/core/auth.py`,
  `backend/core/database.py`, `scripts/tenant_scope_audit.py`.
- Input: login/register/session/API request.
- Output: authenticated user and tenant-scoped access.
- Success: no endpoint returns another tenant's data.
- Failure handling: patch backend filters/tests before adding new UI.

## Hermes Watchdog

- Purpose: monitor and recover safely without taking the pipeline hostage.
- Main docs: `docs/HERMES_AGENT_CONTRACT.md`,
  `docs/HERMES_24H_WATCHDOG_RUNBOOK.md`.
- Main files: `backend/services/hermes_watchdog.py`,
  `backend/endpoints/hermes_endpoints.py`, `scripts/hermes_snapshot.py`,
  `scripts/hermes_canary.py`, `scripts/hermes_daemon.py`.
- Input: health, PM2, jobs, spans, logs, payment events and queue state.
- Output: snapshot, diagnosis, incident and Guard-approved playbook result.
- Success: detects stuck paths and executes only safe idempotent recovery.
- Failure handling: Guard blocks destructive actions and escalates to human.
- Canonical state: health uses `/health`; queue/liveness uses `jobs`, not
  `pipeline_queue`.
- Executor: `auto_remediate_diagnostics` and `execute_guarded_action` in
  `backend/services/hermes_watchdog.py`.
- Hook install helper: `scripts/vps_sync_deploy_hook.py` synchronizes the
  installed Git hook from the versioned `scripts/post-receive` copy.
