# Tasks

- [x] Record OpenSpec proposal/design/tasks/spec.
- [x] Add local dry-run Pipeline Harness CLI.
- [x] Add fixture and scenario format.
- [x] Add guardrails for production DB, providers, deploy, WhatsApp, payments and external HTTP.
- [x] Add static test/smoke audit classification.
- [x] Add harness documentation and safe test matrix.
- [x] Add unit tests for harness guardrails and audit classification.
- [x] Update `AGENTS.md` within the 80-line limit.
- [x] Mark Bryan/SDR historical tests as legacy instead of active pipeline truth.
- [x] Block unsafe non-local test database URLs in shared/integration tests.
- [x] Require `FRALIB_ENV=prod` or a fixture before Mercado Pago reconcile queries live API.
- [x] Block Hermes canary incident recording outside `FRALIB_ENV=prod`.
- [x] Block remote production validator URLs unless `--allow-remote-read` is explicit.
- [x] Reduce static-audit false positives for read-only contracts and monkeypatched LLM/API tests.
- [ ] Review audit output and decide a second change for removals/skips of obsolete tests.
- [ ] Optionally add a Dify/AI Ops Lab spec after the harness proves the safe boundaries.
