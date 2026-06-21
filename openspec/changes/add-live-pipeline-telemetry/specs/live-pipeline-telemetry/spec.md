# Live Pipeline Telemetry Spec

## Requirements

### Requirement: Tenant-Scoped Run Telemetry

FraLib shall expose measured telemetry for the authenticated tenant's current or
latest pipeline job.

#### Scenario: active job telemetry

- Given a tenant has an active pipeline job with spans and ledger rows
- When the tenant requests `/api/pipeline/status`
- Then the response identifies the job and run
- And reports elapsed time, phase spans, tokens, calls and cost.

#### Scenario: tenant isolation

- Given another tenant has spans or ledger rows with similar timestamps
- When the authenticated tenant requests pipeline status
- Then no row from the other tenant contributes to the response.

### Requirement: Real Timeline State

The Fra pipeline timeline shall render persisted state without inventing phase
completion or ETA.

#### Scenario: refresh during execution

- Given a pipeline is running
- When the operator refreshes `admin.html`
- Then the current phase, completed spans, elapsed time, tokens and cost are
  reconstructed from `/api/pipeline/status`.

#### Scenario: no measurements available

- Given a job has no spans or ledger rows yet
- When the timeline renders
- Then it shows awaiting measurements and does not advance phases automatically.

### Requirement: Live Tenant Logs

FraLib shall display pipeline logs in real time next to the timeline using the
existing authenticated SSE channel.

#### Scenario: phase event received

- Given the operator has started a pipeline
- When a structured phase event arrives over SSE
- Then the current timeline state updates immediately
- And the event appears in the expandable live log panel.

### Requirement: Real Run Evidence

The change shall be validated with one queued tenant 2 lead after deployment.

#### Scenario: complete audit record

- Given a tenant 2 lead is already queued for production
- When its pipeline completes or reaches a terminal failure
- Then an audit records the job/run, each observed phase, total elapsed time,
  total tokens, cost and any missing telemetry.
