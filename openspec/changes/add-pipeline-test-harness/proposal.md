# Add Pipeline Test Harness

## Why

FraLib has accumulated unit tests, integration tests, smoke scripts and legacy
contract checks across several pipeline generations. Some of those checks still
protect the active production flow, while others can validate old agent names,
old renderer paths or unsafe operational assumptions.

This creates two risks:

- false confidence, where a passing test validates a dead contract;
- operational leakage, where a test or smoke path can accidentally touch real
  providers, production databases, WhatsApp, deploy hooks or paid APIs.

FraLib needs a local, dry-run-first harness that proves the active pipeline
contract without spending external API calls or mutating production state.

## What Changes

- Add a versioned test audit that classifies existing tests and smoke scripts as
  active, legacy safe, obsolete, dangerous or duplicate/fragile with evidence.
- Add a local Pipeline Harness command for controlled scenarios.
- Add fixture-driven harness scenarios for trial, pro/SDR simulation, Builder,
  payment dry-run and worker recovery dry-run.
- Add guardrails that fail closed when production URLs, provider keys, deploy,
  WhatsApp or live payment markers are present.
- Document the harness and the safe test matrix.
- Add unit tests for the harness itself.
- Update `AGENTS.md` with the canonical harness entrypoint without increasing
  the file beyond 80 lines.

## Expected Gains

- Safety: tests and harness runs block production/API/deploy/WhatsApp paths by
  default.
- Speed: developers can run targeted scenarios instead of a broad suite that may
  import the whole app or require Postgres.
- Cost: harness scenarios do not call LLMs, Hunter, Mercado Pago, Jina or paid
  scrapers.
- Latency insight: scenario output records step timings and expected bottleneck
  class without running paid work.
- Concurrency confidence: worker recovery and queue scenarios become explicit
  dry-run contracts before any live worker intervention.

## Out Of Scope

- Replacing `worker.py`, PM2, Hermes or the production pipeline orchestrator.
- Calling live LLM, Hunter, WhatsApp, deploy, Mercado Pago or scraper providers.
- Removing tests in bulk before the audit identifies a safe deletion set.
- Installing Dify or adding a new external orchestrator.

## Impact

- `scripts/pipeline_harness.py`
- `tests/unit/test_pipeline_harness.py`
- `tests/harness/fixtures/*`
- `tests/harness/scenarios/*`
- `docs/PIPELINE_HARNESS.md`
- `docs/TEST_AUDIT.md`
- `openspec/changes/add-pipeline-test-harness/*`
- `AGENTS.md`
