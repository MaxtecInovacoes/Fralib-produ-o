# system-documentation

## Requirements

### Requirement: Canonical Entry Points

FraLib SHALL provide a documentation index that points operators and IAs to the
current source of truth for architecture, agents, billing, security, deploy and
OpenSpec changes.

#### Scenario: New agent opens the repo

- **WHEN** an agent opens `C:\fralib`
- **THEN** it can read `AGENTS.md`
- **AND** follow `docs/DOCS_INDEX.md`
- **AND** identify the active pipeline without relying on old docs.

### Requirement: Active Pipeline Reference

FraLib SHALL document the active pipeline in terms of inputs, outputs, storage,
files and expected result.

#### Scenario: Operator investigates a stuck site generation

- **WHEN** a pipeline is stuck
- **THEN** the operator can find the worker, queue, prompt agent, Builder and
  deploy references
- **AND** can identify which evidence to collect before recovery.

### Requirement: Legacy Isolation

FraLib SHALL mark old paths as legacy and avoid treating them as runnable unless
code proves they are still active.

#### Scenario: A doc mentions an old renderer

- **WHEN** a legacy renderer appears in a historic document
- **THEN** `AGENTS.md` and `SYSTEM_OPERATIONS_MAP.md` remain the deciding source
  for current runtime behavior.
