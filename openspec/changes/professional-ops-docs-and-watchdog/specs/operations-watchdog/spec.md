# operations-watchdog

## Requirements

### Requirement: Read-Only First

The watchdog SHALL begin every cycle with read-only observation.

#### Scenario: Worker heartbeat is stale

- **WHEN** the monitor sees a stale running job
- **THEN** it records job id, tenant id, type, last phase, heartbeat age and PM2
  state
- **AND** it does not mutate the queue during observation.

### Requirement: Guarded Remediation

The watchdog SHALL execute only allowlisted, idempotent playbooks after Guard
approval.

#### Scenario: Recover runtime is suggested

- **WHEN** diagnosis suggests runtime recovery
- **THEN** Guard checks that `python pipeline.py recover-runtime` is allowlisted
- **AND** the action is recorded with before/after evidence.

#### Scenario: Payment reconciliation is safe to automate

- **WHEN** Mercado Pago webhook errors are detected
- **THEN** Hermes may run the idempotent Mercado Pago reconciliation playbook
- **AND** it must skip already processed payments
- **AND** it must record the command, result and cooldown evidence.

### Requirement: Deny Destructive Operations

The watchdog SHALL deny destructive operations and escalate them to a human.

#### Scenario: A playbook asks to delete queue rows

- **WHEN** an action contains broad delete/update, file deletion, direct VPS edit,
  SCP, rsync, reset runtime or `pm2 kill`
- **THEN** Guard blocks it
- **AND** creates a `blocked_action` incident.
