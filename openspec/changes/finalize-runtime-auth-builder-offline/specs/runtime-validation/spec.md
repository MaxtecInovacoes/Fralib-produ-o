## ADDED Requirements

### Requirement: VPS runtime validation covers local Docker and Postgres gaps
FraLib SHALL validate Docker Compose, Postgres-dependent smoke checks and local service ports on the VPS when the Windows development host lacks Docker CLI or local Postgres.

#### Scenario: VPS compose validation succeeds
- **WHEN** the local host cannot run `docker compose config`
- **THEN** the operator runs `docker compose config --quiet` in `/root/fralib` on the VPS and records a zero exit status

#### Scenario: VPS smoke validates real ports
- **WHEN** local `pipeline.py smoke --dry-run` cannot reach `localhost:5433`
- **THEN** the operator runs the smoke on the VPS and verifies Postgres, FraLib API and Meowhats ports are reported as ready

### Requirement: Smoke remains no-API and no-token
FraLib smoke validation SHALL NOT call LLM providers, Hunter, deploy, or WhatsApp sends.

#### Scenario: Smoke output is dry and token-free
- **WHEN** `pipeline.py smoke --dry-run` finishes
- **THEN** the result reports `tokens_observed` as `0`, `llm_calls` as `0`, deploy as skipped and WhatsApp as skipped

### Requirement: Public deployment health stays observable
FraLib SHALL expose deployed commit identity and the public `llms.txt` artifact after a successful git-flow deploy.

#### Scenario: Public version and llms are available
- **WHEN** the deploy hook publishes a commit to production
- **THEN** `/api/version` returns the deployed commit and `/llms.txt` returns HTTP 200
