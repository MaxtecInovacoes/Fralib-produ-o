# Design

## Principles

The harness is additive and local-only. It must not import the full FastAPI app,
claim jobs, send WhatsApp messages, deploy sites, reconcile real payments or call
LLM/provider APIs. It should behave like a bench test: load a scenario, validate
the declared contract, run only allowlisted local checks, and print structured
evidence.

## Architecture

- `scripts/pipeline_harness.py` provides a CLI:
  - `list`
  - `audit-tests`
  - `run --scenario <name> --dry-run`
  - `run --all --dry-run`
- `tests/harness/scenarios/*.json` declares the active pipeline scenario:
  - tenant and plan fixture;
  - fake lead fixture;
  - expected phases;
  - mocked systems;
  - forbidden capabilities;
  - pass/fail criteria.
- `tests/harness/fixtures/*.json` stores small deterministic inputs.
- Unit tests import harness functions directly and verify guardrails without
  subprocess side effects.

## Guardrails

The harness fails closed when:

- `--dry-run` is omitted;
- `DATABASE_URL` looks like production or a non-test Postgres database;
- any live provider key is present without explicit allow flags;
- scenario allows deploy, WhatsApp, live LLM, live Hunter, live Mercado Pago,
  paid scraper or external HTTP;
- scenario phase uses a name outside the active pipeline list;
- a command is outside the local allowlist.

## Test Audit Classification

The audit uses static evidence from file paths and content:

- `ATUAL`: protects active pipeline, security, tenant scope, Builder Vite/React,
  SDR/Franz policy, Mercado Pago contract, Hermes guard or canonical frontend.
- `LEGADO_SEGURO`: references legacy concepts but is isolated and not dangerous.
- `OBSOLETO`: validates removed/deprecated flows such as Bryan-only behavior,
  old HTML gate as active pipeline, OpenUI as primary path, Bolt/Sandbox routes
  or old agent loop files.
- `PERIGOSO`: can touch production, deploy, WhatsApp, real providers, real DB,
  paid APIs or mutable operational scripts.
- `DUPLICADO_FRAGIL`: depends on broad imports, port availability, timing,
  real local services, or duplicates another contract with unstable detail.

The first implementation reports classifications and does not delete tests.
Deletion/removal is a second change after reviewing the report.

Legacy tests that preserve useful SDR/Bryan history must use
`pytest.mark.legacy` so they do not become active pipeline truth by accident.
Integration tests that open a database must reject non-local/non-test
`DATABASE_URL` values before connecting.

## Integration With Existing Smoke

The harness can reference `pipeline.py smoke --dry-run` as a declared safe
command but does not run it automatically in unit tests. This avoids duplicating
the smoke while preserving its role as the official preflight.

Mercado Pago reconciliation can be represented in local harness runs only with
fixtures. Live API reconciliation remains a production-only operation guarded by
`FRALIB_ENV=prod`.

## Success Criteria

- Harness commands run without network access and without external credentials.
- Unit tests prove unsafe environment and unsafe scenarios are blocked.
- Audit output covers tests and smoke/contract scripts with evidence per file.
- Docs explain which matrix layer each test belongs to.
