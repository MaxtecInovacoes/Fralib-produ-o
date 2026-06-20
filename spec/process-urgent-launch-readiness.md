---
title: FraLib Urgent Launch Readiness Plan
version: 1.0
date_created: 2026-05-26
last_updated: 2026-05-26
owner: Franz/FraLib
tags: [process, launch, reliability, multi-tenant, cost-control]
---

# Introduction

This specification defines the minimum launch plan for selling FraLib as a controlled beta while reducing operational risk, API rate-limit failures, and pipeline instability.

## 1. Purpose & Scope

The purpose is to define what must be fixed, tested, monitored, and constrained before FraLib can be sold to early customers. Scope includes pipeline execution, queue behavior, observability, lead acquisition, site generation, WhatsApp handoff, cost/rate-limit control, and production operations.

## 2. Definitions

- **Beta Vendavel**: Paid early-access launch with limited users and clear support expectations.
- **Happy Path**: A full run that finds a valid lead, qualifies it, generates the site, deploys it, and records observability data.
- **Run ID**: Unique execution identifier used by jobs, spans, heartbeat, ledger, token tracking, and traces.
- **Tenant**: Customer/user account isolated by `tenant_id` or `user_id`.
- **Provider Limit**: API rate, quota, or budget limit from LLM, scraping, image, or WhatsApp provider.

## 3. Requirements, Constraints & Guidelines

- **REQ-001**: Launch must be limited to beta customers until at least 10 full happy-path runs pass in production.
- **REQ-002**: Every pipeline job must have a unique `run_id`.
- **REQ-003**: Jobs with no valid lead must fail clearly, not complete silently.
- **REQ-004**: Queue, jobs, leads, sites, spans, and dashboard data must be tenant-scoped.
- **REQ-005**: Dashboard must expose current status, failures, cost, duration, and bottleneck by run.
- **REQ-006**: API provider usage must have budget, retry, and cooldown controls.
- **REQ-007**: Before launch, at least one real happy-path test must be run for tenant 2.
- **CON-001**: Do not increase parallelism until provider rate limits and budget are measured.
- **CON-002**: Do not sell unlimited usage while only one shared API key exists.
- **GUD-001**: Launch as paid beta with small customer cap, not open public SaaS.

## 4. Interfaces & Data Contracts

- `jobs.run_id`: unique execution id for worker heartbeat and lifecycle.
- `pipeline_run_spans.run_id`: per-phase observability.
- `pipeline_queue.status`: `em_andamento`, `concluido`, or `erro`.
- `pipeline_failures`: user-facing failed jobs that require retry or support.
- `/api/observability/resumo`: tenant-aware dashboard summary.
- `/api/observability/spans/{run_id}`: phase-level drilldown.

## 5. Acceptance Criteria

- **AC-001**: Given a valid fresh lead, when the pipeline runs, then one deployed site URL is produced and a completed job is recorded.
- **AC-002**: Given only duplicate leads, when the pipeline runs, then job status becomes failed and queue status becomes `erro`.
- **AC-003**: Given a running pipeline, when an LLM/scraper call takes longer than 15 seconds, then heartbeat continues updating.
- **AC-004**: Given two tenants, when each requests queue/observability data, then neither sees the other's jobs or spans.
- **AC-005**: Given a pipeline run, when it finishes, then spans show phase duration and cost where available.

## 6. Test Automation Strategy

- **Smoke**: `python pipeline.py smoke --dry-run` locally and in VPS venv.
- **Gate**: `python pipeline.py pre-release-gate` in VPS venv before each release.
- **Real E2E**: Run one happy-path pipeline with a fresh lead and verify site, queue, job, spans, and dashboard.
- **Failure E2E**: Run duplicate/no-lead scenario and verify failed job, queue error, no infinite retry.
- **Tenant Audit**: Keep IDOR and tenant-scope tests in pre-release gate.
- **Load Check**: Simulate 3 tenants queued at once with global LLM limit enforced.

## 7. Rationale & Context

FraLib is close to sellable as a controlled beta, but provider limits and edge cases still create business risk. The correct launch posture is not "perfect product"; it is "paid beta with hard caps, monitoring, and fast support".

## 8. Dependencies & External Integrations

- **SVC-001**: LLM provider API with enough rate limit for expected concurrent pipelines.
- **SVC-002**: Gosom/Maps scraper with predictable timeout and no stuck jobs.
- **SVC-003**: Skill Renderer LLM provider with enough quota for site generation.
- **SVC-004**: Meowhats/WhatsApp service on port 3001.
- **INF-001**: PostgreSQL 5433 with migrations applied.
- **INF-002**: PM2 processes: `fralib`, `fralib-worker`, `fralib-bryan-worker`, `meowhats`, `gosom-scraper`.

## 9. Examples & Edge Cases

- Fresh lead found and qualified: must generate site and record full spans.
- Duplicate-only result: must fail cleanly and not burn retries forever.
- LLM rate limit: must mark retriable with cooldown, not lose progress.
- OD returns static HTML: sanitizer must preserve HTML and inject real contact CTA if missing.
- User lowers score: pipeline must respect dashboard score threshold.

## 10. Validation Criteria

- VPS pre-release gate passes.
- One real happy-path run passes after latest commit.
- One duplicate/no-lead run fails cleanly.
- Observability dashboard shows non-zero runs and phase data for tenant 2.
- No pending/running job remains stale after tests.

## 11. Related Specifications / Further Reading

- `docs/PRD_MVP_ESTABILIZACAO_FRALIB.md`
- `docs/PRD_MVP_PIPELINE_MULTIUSUARIO_E_CUSTOS.md`
- `docs/PIPELINE_AGENT_TIMING_AND_COSTS.md`
