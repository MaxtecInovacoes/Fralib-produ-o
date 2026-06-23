# FraLib Docs Index

This is the canonical documentation entry point for operators, developers and
AI agents working inside `C:\fralib`.

## Start Here

- `AGENTS.md`: absolute operating rules and current active pipeline.
- `docs/ONE_TRUTH_CANONICAL_STATE.md`: canonical sources for queue, state,
  leads, plans, LLM cost and health.
- `docs/ONBOARDING_FOR_AI_AGENTS.md`: first 30 minutes for a new human or AI.
- `docs/SYSTEM_OPERATIONS_MAP.md`: end-to-end map of the running system.
- `docs/PIPELINE_HARNESS.md`: safe dry-run harness and controlled production
  runner entrypoints.
- `docs/AGENT_PATHS_REFERENCE.md`: agent, phase, file, input and output map.
- `docs/TRACKED_FILE_CATALOG.md`: generated catalog of tracked files by area.

## Operations

- `docs/HERMES_AGENT_CONTRACT.md`: allowed Hermes agent roles.
- `docs/HERMES_24H_WATCHDOG_RUNBOOK.md`: concrete monitoring and recovery
  playbooks.
- `scripts/hermes_snapshot.py`, `scripts/hermes_canary.py` and
  `scripts/hermes_daemon.py`: versioned watchdog/canary entrypoints outside the
  request path.
- `scripts/pipeline_harness.py`: local dry-run scenarios, test audit and
  guardrails.
- `scripts/controlled_pipeline_run.py`: production controlled runner for an
  existing lead; requires confirmation and skips WhatsApp unless explicitly
  unlocked.
- `scripts/vps_sync_deploy_hook.py`: versioned VPS hook synchronization when the
  installed Git hook is older than `scripts/post-receive`.
- `docs/MERCADO_PAGO_SEGURANCA_PLANO.md`: Mercado Pago, legal acceptance,
  webhook, session and production enablement.
- `docs/SECURITY_SCALABILITY_AUDIT_2026-06-07.md`: security and scalability
  audit snapshot.
- `docs/PROFESSIONAL_SYSTEM_GAPS.md`: professional SaaS gap register.

## Product And Pipeline

- `docs/PRD_MVP_ESTABILIZACAO_FRALIB.md`: stabilization MVP and acceptance
  criteria.
- `docs/PRD_MVP_PIPELINE_MULTIUSUARIO_E_CUSTOS.md`: multi-user pipeline,
  budget ledger and cost control MVP.
- `docs/PRD_MVP_HERMES_GOSOM_RESILIENCE.md`: Hermes/GoSOM resilience plan.
- `docs/PIPELINE_AGENT_TIMING_AND_COSTS.md`: timing and cost analysis.
- `docs/BUILDER_WORKER.md`: Builder worker behavior.
- `docs/OPENUI_BUILDER_PIPELINE.md`: older Builder/OpenUI context. Treat as
  historical unless it matches `AGENTS.md`.
- `docs/pipeline-run-audits/`: production pipeline run audit logs.
- `docs/FRANZ_SDR_ENTERPRISE_PLAN.md`: Franz/SDR enterprise plan details.
- `docs/SDR_STUDIO_10_10.md`: **CURRENT** — arquitetura do Franz SDR 10/10
  (FSM + Intent + Orchestrator, memory 3-tier, tracing, LLM-as-judge,
  streaming SSE). Score 10/10.
- `docs/SDR_STUDIO_USER_GUIDE.md`: **CURRENT** — guia do superadmin
  pra usar o SDR Studio (interface visual, workflow, rollback).
- `docs/SDR_BUGS_FIXED.md`: **CURRENT** — 7 bugs corrigidos que NUNCA
  devem voltar (stage-loop, WHATSMEOW_DB_URL, CRON_SECRET, etc).
- `docs/SDR_ROADMAP_3_QUICKWINS.md`: roadmap 10/10 (10 features Tier 1-2).
- `docs/SDR_DIAGNOSTICO_COMPLETO.md`: SDR diagnostic and evaluation.
- `docs/TEST_AUDIT.md`: test coverage audit.

## Legal

- `docs/TERMOS_USO_FRALIB.md`: FraLib terms of use.
- `docs/POLITICA_PRIVACIDADE_LGPD_FRALIB.md`: LGPD/privacy policy.

## OpenSpec

- `openspec/changes/finalize-runtime-auth-builder-offline/`: runtime, auth and
  offline Builder contracts.
- `openspec/changes/professional-ops-docs-and-watchdog/`: documentation and
  watchdog contract.

## Rule For Conflicts

When documents disagree, use this order:

1. `AGENTS.md`
2. `docs/ONE_TRUTH_CANONICAL_STATE.md`
3. Current code in `backend/`, `frontend/`, `worker.py`, `pipeline.py`
4. OpenSpec changes under active `openspec/changes/*`
5. Current operational docs listed in this index
6. Older audit documents, only as historical evidence
