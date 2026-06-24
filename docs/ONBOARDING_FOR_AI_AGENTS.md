# Onboarding For AI Agents And Operators

Use this when opening FraLib for the first time or after a long context gap.

## First 10 Minutes

1. Read `AGENTS.md` (especialmente seção 21: Sprints 5-9).
2. Read `docs/ROADMAP_SPRINTS_5_6_7_8_9.md` (visão unificada do salto de maturidade).
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
- WhatsApp bridge: whatsmeow on port 3001.
- Database: PostgreSQL on VPS, SQLite compatibility only for local tests.
- Queue: Postgres table `jobs` via `backend/core/job_queue.py`.
- One-truth contract: `docs/ONE_TRUTH_CANONICAL_STATE.md`.
- Deploy: Git hook publishes from `/root/fralib`, never manual copy.

## Sinais SDK ativos (13/13)

Todos os 13 sinais do roadmap estão implementados. Ver `AGENTS.md` seção 21.

- **Sprint 1**: Memory 3-tier, memory hook, bridge Builder
- **Sprint 2**: Tools dinâmicas site, loop autônomo
- **Sprint 3A**: SDR Tools (4 tools)
- **Sprint 3B**: SDR RAG semântico
- **Sprint 3C**: SDR Telemetria
- **Sprint 5**: Tracing 4 agentes (FRALIB_TRACING=1 ativo na VPS)
- **Sprint 6**: Sub-agentes por estética (6 templates Awwwards)
- **Sprint 7**: RAG Templates (embeddings 64d)
- **Sprint 8**: Auto-melhoria (traces → prompts v2 com gate conservador)
- **Sprint 9**: Edge cases + production hardening (8 helpers)

## What To Run Before Risky Work

Preferred local preflight:

```bash
python pipeline.py smoke --dry-run
```

Release gate (suite consolidada):

```bash
cd C:\fralib
for f in tests/test_anti_regressao_*.py; do
  PYTHONIOENCODING=utf-8 python "$f" 2>&1 | tail -1
done
# Esperado: 130/130 verde
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
6. Builder Renderer (OpenUI padrão, ou 6 sub-agentes Awwwards se FRALIB_USE_SUB_AGENTS=1).
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
