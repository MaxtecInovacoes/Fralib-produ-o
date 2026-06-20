# Onboarding For AI Agents And Operators

Use this when opening FraLib for the first time or after a long context gap.

## First 10 Minutes

1. Read `AGENTS.md`.
2. Read `docs/DOCS_INDEX.md`.
3. Read `docs/ONE_TRUTH_CANONICAL_STATE.md`.
4. Check repo state with `git -C C:\fralib status --short --branch`.
5. Do not touch unrelated dirty files.
6. Confirm the active pipeline in `docs/SYSTEM_OPERATIONS_MAP.md`.
7. Use `docs/TRACKED_FILE_CATALOG.md` when you need a file-by-file map.
8. If changing behavior, find or create an OpenSpec change.

## Absolute Rules

- Do not SCP, rsync or edit files directly on VPS.
- Use local edit -> git add -> git commit -> git push.
- Do not deploy uncommitted code.
- If code, config, pipeline or docs change, update `AGENTS.md` without exceeding
  80 lines.
- Do not activate old agents or flags unless current code proves they are real.
- Do not paste or echo secrets in logs, docs, commits or frontend.

## Canonical Runtime

- Web/API: FastAPI served by PM2 process `fralib` on port 8000.
- Worker: `worker.py` served by PM2 process `fralib-worker`.
- WhatsApp bridge: Meowhats on port 3001.
- Database: PostgreSQL on VPS, SQLite compatibility only for local tests.
- Queue: Postgres table `jobs` via `backend/core/job_queue.py`.
- One-truth contract: `docs/ONE_TRUTH_CANONICAL_STATE.md`.
- Deploy: Git hook publishes from `/root/fralib`, never manual copy.

## What To Run Before Risky Work

Preferred local preflight:

```bash
python pipeline.py smoke --dry-run
```

Release gate:

```bash
python pipeline.py pre-release-gate
```

If local Postgres or ports are offline, do not fake success. State the local
limit and validate on VPS through the Git/deploy flow.

## How To Read The Pipeline

The request path starts at `POST /api/pipeline/iniciar` in
`backend/endpoints/pipeline_start_endpoints.py`.

Long execution belongs to `worker.py`, not the HTTP request. The worker claims a
job from `backend/core/job_queue.py`, executes a supported job type, records
heartbeat and marks success or failure.

Do not use `pipeline_queue`, `pipeline_state.rodando`, `users.plan` or
`pipeline_token_usage` to decide current behavior. They are legacy or derived
compatibility surfaces.

Site generation flows through:

1. Lead Supply inventory.
2. Caio qualification.
3. Production tick scheduling.
4. Jina and market intelligence.
5. Prompt Agent.
6. Builder Renderer.
7. Deploy.
8. Franz/SDR if the plan allows it.

## How To Avoid Breaking Tenants

- Every user-facing operation must be tenant-scoped.
- Prefer `tenant_id` and `user_id` filters in SQL.
- Never reuse global slugs, sessions, checkpoints or assets across tenants.
- Run `scripts/tenant_scope_audit.py` after touching endpoints, jobs or storage.

## How To Handle Incidents

Start read-only:

1. Gather API health, PM2 status, job rows, spans and recent logs.
2. Classify the symptom.
3. Use `docs/HERMES_24H_WATCHDOG_RUNBOOK.md`.
4. Execute only allowlisted playbooks.
5. If a fix changes code/config/docs, commit and push.

## When In Doubt

Do not invent a missing runtime path. Search the code, inspect tests and prefer
the current implementation over old documents.
