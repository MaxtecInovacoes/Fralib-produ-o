# Add Live Pipeline Telemetry

## Why

The FraLib admin timeline currently shows the current phase, but advances phase
progress and ETA with simulated timers. Operators cannot see which calls ran,
how long each phase took, or the tokens and cost accumulated by one pipeline.

FraLib already stores job correlation, phase spans and the canonical LLM ledger.
The admin should expose those records for the authenticated tenant and reuse the
existing tenant-scoped SSE stream for live updates.

## What Changes

- Enrich pipeline status with job timing, per-phase spans and canonical LLM usage.
- Publish structured telemetry events when phase progress changes.
- Replace simulated timeline progress and ETA with measured values.
- Add an expandable live log panel next to the Fra pipeline timeline.
- Keep all API queries scoped to the authenticated tenant.
- Add backend and frontend contract tests and record one real tenant 2 run.

## Out Of Scope

- A new logging transport, WebSocket service or metrics stack.
- Prometheus, Grafana or Loki.
- Cross-tenant observability in the regular admin.
- Direct file edits or deployment outside the Git push hook.

## Impact

- `backend/endpoints/pipeline_status_endpoints.py`
- `backend/services/pipeline_phase_tracking.py`
- `frontend/js/admin/pipeline-waveform.js`
- `frontend/partials/admin/_scripts.html`
- `frontend/admin.html`
- focused tests and pipeline run audit documentation
- `AGENTS.md`
