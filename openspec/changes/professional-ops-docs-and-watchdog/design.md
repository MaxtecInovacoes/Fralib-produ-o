# Design

## Principles

1. Git is the operational source of truth.
2. Production fixes must be versioned scripts or commits, never ad-hoc edits.
3. Documentation must describe the active path first and legacy paths only as
   legacy.
4. Every agent description must name input, output, files and expected result.
5. Watchdog automation starts read-only, then can execute only idempotent
   allowlisted playbooks through Guard.

## Documentation Shape

The documentation layer uses four entry points:

- `DOCS_INDEX.md`: where to go for each question.
- `ONBOARDING_FOR_AI_AGENTS.md`: first 30 minutes for a human or AI.
- `SYSTEM_OPERATIONS_MAP.md`: how the system works end to end.
- `AGENT_PATHS_REFERENCE.md`: agent-by-agent runtime reference.

Operational resilience uses:

- `HERMES_AGENT_CONTRACT.md`: high-level Hermes agent contract.
- `HERMES_24H_WATCHDOG_RUNBOOK.md`: concrete playbooks and severity.
- `PROFESSIONAL_SYSTEM_GAPS.md`: gap register for launch/professional maturity.

## Watchdog Safety Model

The 24h agent must run in three layers:

1. Monitor: read-only snapshots from health endpoints, PM2, Postgres, jobs,
   spans, payment events and logs.
2. Diagnose: classify symptom, probable cause, severity, evidence and suggested
   playbook.
3. Execute: only if Guard approves an allowlisted idempotent action.

Denied actions include direct file edits on VPS, broad SQL update/delete,
runtime reset, queue deletion, checkpoint deletion, `pm2 kill`, SCP and rsync.

## Acceptance

- A new operator can identify the current pipeline without reading old docs.
- A new IA can avoid legacy Builder/SDR/Sandbox paths by reading AGENTS and the
  onboarding doc.
- A production incident has a documented severity and first safe playbook.
- The docs name current limits instead of hiding them.
