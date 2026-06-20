---
title: FraLib Operation Inspired by Ruflo Patterns
version: 1.0
date_created: 2026-05-27
last_updated: 2026-05-27
owner: FraLib
tags: architecture, process, pipeline, agents, operations
---

# Introduction

This specification defines how FraLib shall adopt proven orchestration patterns
observed in Ruflo-like systems without installing Ruflo as a runtime dependency.
The goal is to professionalize FraLib operations by replacing ad-hoc agent flow
with durable workflows, small worker roles, explicit contracts, operational
memory, visual QA, cost tracking, and recovery-first execution.

## 1. Purpose & Scope

This spec applies to the FraLib local-business site pipeline, Hermes operations,
QA, observability, and future agent tooling. It does not replace the current
PostgreSQL job queue, tenant isolation, cooldown rules, or Skill Renderer.

## 2. Definitions

- **Workflow**: Deterministic orchestration state machine that decides the next
  step but does not perform external calls directly.
- **Activity**: Idempotent external operation such as LLM call, browser QA,
  database write, Skill Renderer call, deploy, or WhatsApp handoff.
- **Agent Contract**: A versioned input/output schema and responsibility boundary
  for one agent or worker.
- **Operational Memory**: Structured record of failures, root causes, fixes,
  costs, timings, and prevention rules.
- **Hermes**: FraLib operations agent responsible for investigation, diagnosis,
  recommendations, and guarded execution.
- **Visual QA**: Browser-based inspection of deployed site quality on desktop and
  mobile, including screenshots and deterministic checks.

## 3. Requirements, Constraints & Guidelines

- **REQ-001**: FraLib shall keep the current Postgres job queue as the production
  source of truth.
- **REQ-002**: Each pipeline phase shall have a clear activity contract:
  input, output, timeout, retry policy, idempotency key, cost fields, and failure
  classification.
- **REQ-003**: Long-running flow shall be resumable from the last successful
  phase and shall not restart Hunter when a qualified lead already exists.
- **REQ-004**: Hermes shall write operational memory after every repeated failure:
  symptom, root cause, fix, prevention rule, affected files, and verification.
- **REQ-005**: Visual QA shall run after deploy and before marking a lead as
  complete.
- **REQ-006**: Cost and timing shall be tracked per phase and per agent.
- **REQ-007**: Agent roles shall remain small and bounded; no generic "do
  everything" agent may own an entire production pipeline.
- **CON-001**: Do not add Ruflo as a runtime dependency before a separate spike.
- **CON-002**: Do not introduce more than one global pipeline worker while the API
  key is shared and rate-limit capacity is not measured.
- **CON-003**: No agent may bypass tenant_id/user_id isolation.
- **GUD-001**: Copy patterns, not branding: workers, memory, plugins, QA, cost
  tracking, and workflow contracts are useful; 100+ agents are not.

## 4. Interfaces & Data Contracts

### 4.1 Pipeline Activity Contract

```json
{
  "activity_id": "open_design.generate_site",
  "job_id": 239,
  "tenant_id": 2,
  "lead_id": "uuid",
  "input_ref": "checkpoint://pipeline_id/phase",
  "output_ref": "checkpoint://pipeline_id/open_design",
  "idempotency_key": "tenant:lead:phase:version",
  "timeout_seconds": 900,
  "max_attempts": 3,
  "cost": {
    "provider": "anthropic|openai|openrouter|none",
    "model": "string",
    "input_tokens": 0,
    "output_tokens": 0,
    "estimated_usd": 0
  },
  "status": "pending|running|succeeded|failed_retryable|failed_permanent",
  "failure_class": "none|provider_timeout|quality_gate|validator_uncertain|worker_died|rate_limit"
}
```

### 4.2 Operational Memory Contract

```json
{
  "incident_id": "uuid",
  "first_seen_at": "2026-05-27T13:31:20Z",
  "symptom": "Validator blocked deploy without concrete problems",
  "root_cause": "LLM validator treated preview uncertainty as hard failure",
  "fix": "Only concrete validator problems block deploy; deterministic gates remain mandatory",
  "prevention_rule": "Uncertainty from partial preview becomes observation, not failure",
  "verification": ["unit_tests", "vps_tests", "controlled_pipeline_job"],
  "related_files": ["backend/agents/validador.py"]
}
```

## 5. Acceptance Criteria

- **AC-001**: Given an existing qualified lead, when the job retries, then Hunter
  is skipped and the pipeline resumes from the next incomplete phase.
- **AC-002**: Given a generated site with placeholder media, when quality gate
  runs, then deploy is blocked with a concrete deterministic error.
- **AC-003**: Given a validator response with no concrete problem, when validation
  completes, then deploy is not blocked only because of uncertainty.
- **AC-004**: Given a deployed site, when Visual QA runs, then screenshots and
  checks are attached to the job before the lead becomes `concluido`.
- **AC-005**: Given any failed job, when Hermes investigates, then operational
  memory is created or updated with root cause and prevention rule.

## 6. Test Automation Strategy

- Unit tests for activity contracts, validator classification, quality gates, and
  cost/timing ledger.
- Integration tests for job retry/resume and tenant isolation.
- Browser tests for desktop and mobile generated sites.
- VPS pre-release gate shall include at least one dry-run and one controlled
  reprocess path that does not contact real customers.

## 7. Rationale & Context

Ruflo's useful pattern is not the number of agents. The useful pattern is a
structured operational layer: specialized workers, durable memory, cost
tracking, workflow contracts, and browser QA. FraLib already has the business
pipeline and tenant model; it needs stronger contracts and better recovery, not
another orchestration runtime in production.

## 8. Dependencies & External Integrations

- **EXT-001**: PostgreSQL job queue and checkpoints.
- **EXT-002**: Skill Renderer LLM route for site generation.
- **EXT-003**: Browser automation for Visual QA.
- **EXT-004**: LLM providers for agent activities.
- **EXT-005**: PM2/VPS runtime for workers.

## 9. Examples & Edge Cases

```text
Case: OD creates HTML, validator cannot inspect full page.
Expected: deterministic gates decide critical safety. Validator uncertainty is
saved as observation. The job does not fail unless a concrete issue exists.

Case: worker restarts during phase.
Expected: heartbeat stale is reaped, job resumes from the last completed
checkpoint with same lead_id and tenant_id.
```

## 10. Validation Criteria

- No global file cache may mix tenant data.
- Each production activity has timeout, retry, idempotency, and checkpoint.
- Each repeated failure creates an operational memory entry.
- Visual QA must fail on placeholders, broken images, missing CTA, missing
  schema, obvious layout overlap, and inaccessible deployed URL.

## 11. Related Specifications / Further Reading

- `docs/HERMES_AGENT_CONTRACT.md`
- `docs/PIPELINE_AGENT_TIMING_AND_COSTS.md`
- `docs/PRD_MVP_ESTABILIZACAO_FRALIB.md`
- `spec/process-mvp-launch-100-percent.md`
