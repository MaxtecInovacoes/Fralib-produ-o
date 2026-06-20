# Pipeline Harness Spec

## Requirements

### Requirement: Local Dry-Run Harness

FraLib shall provide a local Pipeline Harness that runs controlled scenarios for
the active pipeline without external side effects.

#### Scenario: run a named scenario

- Given a scenario file under `tests/harness/scenarios`
- When the operator runs `python scripts/pipeline_harness.py run --scenario <name> --dry-run`
- Then the harness validates the scenario, guardrails and expected phases
- And the output includes step status, evidence and elapsed time.

#### Scenario: dry-run is mandatory

- Given any harness run command
- When `--dry-run` is missing
- Then the harness exits before running scenario steps.

### Requirement: Production Safety Guardrails

FraLib shall block harness runs that can touch production, paid providers or
mutable external systems.

#### Scenario: production database is blocked

- Given `DATABASE_URL` points to a non-test Postgres database
- When a scenario run starts
- Then the harness fails closed with a production database warning.

#### Scenario: live side effects are blocked

- Given a scenario allows deploy, WhatsApp, live LLM, live Hunter, live Mercado
  Pago, paid scraper or external HTTP
- When a scenario run starts
- Then the harness rejects the scenario unless a future explicit live mode is
  implemented outside this change.

### Requirement: Test Audit

FraLib shall provide a static audit that classifies tests and smoke scripts by
pipeline relevance and operational risk.

#### Scenario: audit classifies every discovered file

- Given files under `tests/` and smoke/contract scripts under `scripts/`
- When the operator runs `python scripts/pipeline_harness.py audit-tests`
- Then every discovered file receives a classification and evidence list.

#### Scenario: legacy and dangerous evidence is explicit

- Given a file mentions legacy agents or live operational capabilities
- When the audit classifies it
- Then the output includes the matching evidence terms.
