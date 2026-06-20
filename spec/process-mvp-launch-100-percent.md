---
title: FraLib MVP Launch To 100 Percent Readiness
version: 1.0
date_created: 2026-05-26
last_updated: 2026-05-26
owner: Franz/FraLib
tags: [process, launch, mvp, reliability, landing-page, cost-control]
---

# Introduction

This PRD defines what is already ready, what still blocks a safe paid beta,
and what must be improved to reach a near-perfect FraLib launch. The goal is
not to wait for a perfect SaaS, but to launch with controlled risk, real
observability, clear limits, and a landing page that sells professionally.

## 1. Purpose & Scope

This specification covers:

- production pipeline stability;
- multi-tenant queue safety;
- API cost and rate-limit control;
- retry and checkpoint behavior;
- dashboard user experience during pipeline execution;
- public landing page, plans, blog, and docs readiness;
- testing strategy before selling and after selling.

The intended launch mode is a paid controlled beta, not a fully open SaaS.

## 2. Current State Summary

| Area | Status | Launch Meaning |
| --- | --- | --- |
| Reset runtime | Ready | `pipeline.py reset-runtime --confirm` exists. |
| VPS gate | Ready | `pipeline.py pre-release-gate` passes in VPS. |
| Multi-tenant queue | Mostly ready | Tenant isolation and global pipeline limit exist. |
| Duplicate lead handling | Improved | Existing tenant leads are skipped unless discarded. |
| Skill Renderer pipeline | Mostly ready | Renderer HTML preservation and quality gate exist. |
| Worker heartbeat | Mostly ready | Job heartbeat and span heartbeat exist. |
| Failure handling | Mostly ready | `pipeline_failures` and user-facing errors exist. |
| Observability | Good foundation | `pipeline_run_spans` and tenant-aware endpoints exist. |
| API cost/rate control | In progress | Ledger/rate-limit tables and basic LLM ledger write added; enforcement still pending. |
| Checkpoints | Partial | Tenant-scoped, but not strong by tenant + lead + run. |
| Dashboard pipeline UX | Partial | Timeline live replaces noisy terminal; needs real-run QA. |
| Landing page | Locked visual | Old visual preserved; only copy/sections may change. |

## 3. Product Definition

### 3.1 Paid Beta Definition

FraLib can be sold as a paid beta when:

- a user can start one pipeline from the dashboard;
- the system either produces a deployed site or fails with a clear message;
- no tenant can see another tenant's data;
- API usage cannot run uncontrolled;
- support can diagnose a run by `run_id`, tenant, lead, phase, cost, and error;
- the public page accurately explains Trial, Starter, Pro, and Agency.

### 3.2 Near-100 Percent Definition

FraLib is near production-grade when:

- pipeline runs are resumable by tenant + lead + run;
- rate limits are handled before provider failure;
- every LLM call is recorded with cost, model, tenant, job, and phase;
- dashboard shows live phase progress;
- landing/docs/blog are coherent and visually polished;
- 10 real happy-path runs and 3 controlled failure runs pass in production.

## 4. What Is Already Ready

- **READY-001**: `MAX_PIPELINES_GLOBAL=1` prevents shared API overload while one key is used.
- **READY-002**: `claim_next()` uses `FOR UPDATE SKIP LOCKED` and avoids concurrent pipeline jobs for the same tenant.
- **READY-003**: queue ordering provides fairness by tenant and priority.
- **READY-004**: Bryan runs as a separate worker/job after pipeline completion.
- **READY-005**: `pipeline_run_spans` records per-phase observability.
- **READY-006**: tenant-aware observability endpoints exist.
- **READY-007**: `pipeline_failures` exists for dead-letter/failure review.
- **READY-008**: Skill Renderer output is preserved and normalized instead of wrapped blindly.
- **READY-009**: public plans no longer expose BYOK; public model is cooldown based.
- **READY-010**: deploy hook publishes frontend to `/var/www/fralib` and removes legacy landing files.

### 4.1 Execution Log Through 2026-05-26

- Landing visual restored to the old approved direction after a rejected redesign attempt.
- Landing copy simplified: hero, how-it-works, and product mockup text updated.
- Landing scripts hardened: missing `themeToggle` no longer crashes JS; particles target now matches `tsparticles`.
- Landing visual lock added to smoke via `scripts/check_landing_visual_lock.py`.
- Admin Motor FraLib changed from visible Terminal Magico to live pipeline timeline.
- Pixel Office sizing adjusted to stay proportional beside the timeline.
- VPS smoke passed after deploy: env, imports, DB, context, landing lock, ports.
- LLM budget foundation deployed: `llm_budget_ledger`, `provider_rate_limits`, and successful LLM call ledger writes.

## 5. Critical Gaps Before Launch

### P0. Real Pipeline Test

- **REQ-P0-001**: Run one real dashboard pipeline for tenant 2.
- **REQ-P0-002**: Run one real dashboard pipeline for a second test tenant, e.g. tenant 31.
- **REQ-P0-003**: Record phase duration, cost, lead status, site URL, and error if any.
- **REQ-P0-004**: Verify no stale jobs remain after each test.

### P0. Landing Page Copy And Visual Lock

Known current defects:

- Fixed on 2026-05-26: removed the broken `particlesJS("particles-js", ...)` call.
- Fixed on 2026-05-26: removed the missing `themeToggle` dependency.
- Fixed on 2026-05-26: visual restored to the old landing direction by product decision.
- Fixed on 2026-05-26: landing visual CSS locked by `scripts/check_landing_visual_lock.py`.

Requirements:

- **REQ-LP-001**: Keep the old landing visual; update only copy and content sections unless Franz explicitly approves visual changes.
- **REQ-LP-002**: Fix all JavaScript runtime errors.
- **REQ-LP-003**: Keep Docs, Blog, Trial, Starter, Pro, Agency aligned with the backend offer.
- **REQ-LP-004**: Add animation QA: particles or motion must either load correctly or be removed.
- **REQ-LP-005**: Verify desktop and mobile screenshots before deploy.
- **REQ-LP-006**: All CTA buttons must route to valid checkout/signup paths.
- **REQ-LP-007**: Smoke must fail if the locked landing visual layer changes unexpectedly.

### P0. API Cost And Rate Control

Progress:

- Done on 2026-05-26: `llm_budget_ledger` added to official DB initialization.
- Done on 2026-05-26: `provider_rate_limits` added to official DB initialization with seed models.
- Done on 2026-05-26: successful LLM calls write tenant, run, agent, model, tokens, cost, and latency.
- Pending: job_id/phase context on each LLM call.
- Pending: hard provider budget enforcement from `provider_rate_limits`.

Requirements:

- **REQ-API-001**: Create `llm_budget_ledger` in `backend/core/database.py`. Status: done.
- **REQ-API-002**: Create `provider_rate_limits` in `backend/core/database.py`. Status: done.
- **REQ-API-003**: Record tenant, job_id, run_id, phase, agent, model, tokens, cost, latency, and status per LLM call. Status: partial, missing job_id/phase.
- **REQ-API-004**: Enforce global provider budget before starting expensive phases.
- **REQ-API-005**: If provider is in cooldown, return a retriable job state instead of losing progress.
- **REQ-API-006**: Superadmin must see cost by tenant, model, phase, and day.

### P1. Strong Checkpoint Identity

Current checkpoint is tenant-scoped by pipeline_id, but should be stronger.

- **REQ-CKP-001**: Use a checkpoint key containing `tenant_id`, `lead_id`, and `run_id`.
- **REQ-CKP-002**: Store checkpoint metadata: lead name, phone, slug, city, segment, phase.
- **REQ-CKP-003**: Before loading a checkpoint, verify that tenant and lead match the current run.
- **REQ-CKP-004**: On successful retry, clear previous queue and lead error state.
- **REQ-CKP-005**: Reuse completed PRD/HTML only when checksum and lead identity match.

### P1. Dashboard Runtime UX

- **REQ-UX-001**: Show current pipeline phase in simple language.
- **REQ-UX-002**: Show "we are searching leads", "qualifying", "creating site", "publishing", "contacting".
- **REQ-UX-003**: Show clear failure messages and recommended next action.
- **REQ-UX-004**: Add "retry from last safe phase" when checkpoint exists.
- **REQ-UX-005**: Show queue position when another pipeline is running globally.

## 6. Launch Plan

### Phase A: Stabilize And Test

1. Fix landing JavaScript and copy without changing the locked visual.
2. Run VPS pre-release gate.
3. Run real tenant 2 pipeline.
4. Run real tenant 31 pipeline.
5. Record results in `docs/PIPELINE_AGENT_TIMING_AND_COSTS.md`.

Exit criteria:

- 2 real runs completed or failed cleanly.
- No stuck jobs.
- No stale queue rows.
- User-facing status is understandable.

### Phase B: Cost Control

1. Add DB tables for API ledger and provider limits.
2. Wire LLM calls to ledger.
3. Add provider cooldown behavior.
4. Add superadmin cost panel.
5. Test rate-limit simulation.

Exit criteria:

- Every LLM call is traceable.
- Daily spend can be estimated.
- System can pause expensive work before provider failure.

### Phase C: Paid Beta

1. Invite 3 to 10 users max.
2. Keep `MAX_PIPELINES_GLOBAL=1` while using one shared API key.
3. Starter cooldown: 60 minutes.
4. Pro cooldown: 30 minutes.
5. Agency: no public self-serve until cost data is validated.

Exit criteria:

- 10 happy-path production runs.
- 3 clean failure-path runs.
- Cost per run known by median and worst case.

### Phase D: Near-100 Percent

1. Strong checkpoint identity by tenant + lead + run.
2. Load/concurrency testing.
3. Payment/plan entitlement audit.
4. Full landing/docs/blog refresh.
5. Support playbook and incident checklist.

## 7. Test Matrix

| Test | Tenant | Scenario | Expected Result |
| --- | --- | --- | --- |
| Gate | VPS | `pipeline.py pre-release-gate` | All pass. |
| Happy path | 2 | Fresh niche/city, 1 lead | Site deployed, spans recorded. |
| Tenant isolation | 31 | Fresh niche/city, 1 lead | No tenant 2 data visible. |
| Duplicate path | 2 | Previously used niche/city | Clear failure or next valid lead. |
| Rate limit | any | Simulated cooldown | Job retriable, no progress lost. |
| Landing desktop | public | 1365x768 viewport | No broken JS, polished hero. |
| Landing mobile | public | 390x844 viewport | No overflow, buttons fit. |

## 8. Acceptance Criteria

- **AC-001**: Given a user starts one pipeline, when it is running, then dashboard shows current phase within 15 seconds.
- **AC-002**: Given no qualified lead exists, when pipeline ends, then the user sees a clear message and the job is not stuck.
- **AC-003**: Given two tenants request runs, when data is returned, then each sees only their own jobs, leads, sites, and spans.
- **AC-004**: Given a provider cooldown, when an expensive phase is requested, then the system queues or retries instead of burning the run.
- **AC-005**: Given the public landing page loads, when JS executes, then no console error is thrown from missing elements or wrong IDs.
- **AC-006**: Given a visitor clicks a CTA, then it opens the correct signup or contact path for the plan.

## 9. Immediate Task Backlog

### Must Finish Before Selling

- **TASK-001**: Fix landing script mismatch: `tsparticles` vs `particles-js`. Status: done.
- **TASK-002**: Remove or implement `themeToggle`. Status: done.
- **TASK-003**: Preserve old landing visual and simplify copy. Status: done; screenshot QA pending.
- **TASK-004**: Run real pipeline from dashboard for tenant 2.
- **TASK-005**: Run real pipeline from dashboard for tenant 31.
- **TASK-006**: Implement LLM budget ledger tables. Status: done.
- **TASK-007**: Implement provider rate limit table and checks. Status: table done; checks pending.

### Can Improve During Paid Beta

- **TASK-008**: Strong checkpoint key by tenant + lead + run.
- **TASK-009**: Better dashboard live phase copy.
- **TASK-010**: Superadmin cost charts.
- **TASK-011**: Full blog/docs content cleanup.
- **TASK-012**: Split large orchestrator by phase.

## 10. Risks

- **RISK-001**: One shared API key can still bottleneck all users.
- **RISK-002**: Landing visual quality can reduce conversion even if product works.
- **RISK-003**: Checkpoint reuse without lead identity can cause confusing retries.
- **RISK-004**: Old static files can reappear if deploy hook is bypassed.
- **RISK-005**: Dashboard user may abandon run if progress/status is unclear.

## 11. Recommended Next Action

The next implementation sprint should be:

1. Run screenshot QA on landing and admin timeline without changing the locked visual.
2. Run two real dashboard pipelines: tenant 2 and tenant 31.
3. Finish provider cooldown enforcement from `provider_rate_limits`.
4. Start paid beta with a small cap and manual monitoring.
