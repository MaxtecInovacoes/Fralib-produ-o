# Design

## Data Sources

- `jobs` is the job/run lifecycle source.
- `pipeline_run_spans` is the per-phase timing source.
- `llm_budget_ledger` is the canonical token and cost source.
- `/api/logs/stream` remains the single tenant-scoped live transport.

## API Contract

`GET /api/pipeline/status` returns a `telemetry` object for the current job, or
the latest completed pipeline job when no job is active. It includes job/run
identity, elapsed duration, phase spans, aggregate tokens, cache tokens, cost,
LLM call count and measurement timestamps.

Every query requires `tenant_id` and correlates ledger rows by `job_id`, with
`run_id` as a fallback only inside the same tenant.

## Live Events

Phase tracking emits a JSON `pipeline_telemetry` event through the existing SSE
channel after persistence. The browser treats SSE as the fast path and the
status endpoint as the five-second reconciliation path.

## Admin Behavior

- The elapsed timer derives from `jobs.iniciado_em`.
- Completed spans determine phase completion and duration labels.
- Tokens and cost update from canonical ledger totals.
- No fake phase advancement or invented ETA is shown.
- The log panel is collapsed by default and opens in place, preserving context.
- Reduced-motion users receive state changes without pulsing animation.

## Failure And Rollback

Missing observability tables degrade to an empty telemetry object without
breaking pipeline status. Rollback is one Git revert; no schema migration is
required because the change reads existing canonical tables.

## Verification

- Unit tests cover phase mapping, aggregation and tenant scope.
- Frontend contract tests reject simulated progress and verify telemetry fields.
- A real queued lead for tenant 2 records timestamps, phases, tokens and cost.
- Browser verification confirms the timeline and log panel update after start.
