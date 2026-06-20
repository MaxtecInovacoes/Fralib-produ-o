# Hermes 24h Watchdog Runbook

Hermes is an operational watchdog, not a magic auto-developer. It can monitor,
diagnose and run a small allowlist of safe playbooks. Anything destructive must
be blocked and escalated.

## Operating Model

1. Monitor every cycle in read-only mode.
2. Diagnose probable cause with evidence.
3. Ask Guard to approve any action.
4. Execute only allowlisted, idempotent actions.
5. Record before/after evidence.
6. Escalate if the required action is outside the allowlist.

## Minimum Snapshot

Each cycle should collect:

- `/health` and `/api/version`.
- PM2 status for `fralib`, `fralib-worker`, `fralib-bryan-worker`, `meowhats`.
- Postgres connectivity and key table counts.
- Running/pending/failed jobs grouped by tenant and type.
- Oldest pending job and oldest running heartbeat.
- Recent `jobs` blocked/running states and `/health` payload.
- Provider alerts and LLM ledger anomalies.
- Mercado Pago events in the last 24 hours.
- Redis availability when configured.
- WhatsApp bridge status.

The versioned collector is available as:

```bash
python scripts/hermes_snapshot.py --json
python scripts/hermes_snapshot.py --record --json
python scripts/hermes_daemon.py
```

In production, PM2 runs `fralib-hermes-watchdog` from `ecosystem.config.js`.
The deploy hook starts or reloads it on every master deploy. The default cycle is
5 minutes, with dry-run canary smoke every 12 cycles. `HERMES_AUTOREMEDIATE=1`
enables only Guard-approved playbooks and records `remediation_applied` or
`remediation_failed` incidents with before/after evidence.

If `scripts/post-receive` is correct but `/root/repos/fralib/hooks/post-receive`
is older, run the versioned synchronizer on the VPS:

```bash
cd /root/fralib
python3 scripts/vps_sync_deploy_hook.py --apply
```

The superadmin API exposes the same data at:

- `GET /api/superadmin/hermes/snapshot`
- `POST /api/superadmin/hermes/scan`
- `GET /api/superadmin/hermes/incidents`
- `POST /api/superadmin/hermes/guard/check`
- `POST /api/superadmin/hermes/remediate`

## Severity

| Severity | Meaning | Example |
| --- | --- | --- |
| SEV1 | Revenue/user flow down | login down, payments not credited, all workers stopped |
| SEV2 | Pipeline degraded | jobs stale, Builder timeouts, provider outage |
| SEV3 | Tenant/user isolated | one tenant blocked by cooldown/config/WhatsApp |
| SEV4 | Warning | high latency, low lead supply, retries increasing |

## Allowlisted Actions

- Run read-only diagnostics.
- Run `python pipeline.py smoke --dry-run`.
- Run `python pipeline.py recover-runtime`.
- Run Mercado Pago reconciliation script in dry-run mode.
- Run Mercado Pago reconciliation with `--apply` only for confirmed approved
  payments and idempotent events.
- Restart one PM2 process after Guard approval when evidence shows it is stale:
  `fralib`, `fralib-worker`, `fralib-bryan-worker` or `meowhats`.
- Pause intake through a versioned/admin-safe mechanism when available.

## Denylist

Always block:

- SCP, rsync or direct VPS file edits.
- `pm2 kill`.
- Broad `DELETE`, `TRUNCATE` or `UPDATE`.
- Deleting logs, queues, checkpoints, sites or caches.
- Resetting runtime without explicit human confirmation and versioned script.
- Editing `.env` through chat or commit.
- Moving a lead/job between tenants.
- Publishing uncommitted code.

## Playbook: User Paid But Credits Did Not Arrive

Evidence:

- User id, amount, Mercado Pago payment id if available.
- `mercadopago_events` for the payment id.
- Current user plan/credits.
- Checkout return status from frontend if available.

Steps:

1. Run reconciliation in dry-run for the last 24 hours.
2. Confirm the payment is approved and belongs to FraLib metadata.
3. Confirm no previous event credited the same payment id.
4. Apply reconciliation.
5. Re-query credits.
6. Record incident with payment id redacted except last digits.

Automation:

- Hermes runs the idempotent `mp_reconcile_apply` playbook automatically when
  `HERMES_AUTOREMEDIATE_PAYMENT_APPLY=1`.
- The script only applies approved Mercado Pago payments with FraLib
  `external_reference` and skips payments already processed.
- Cooldown prevents repeated reconciliation loops.

Do not manually update credits unless there is a versioned script and explicit
approval.

## Playbook: Worker Stale

Evidence:

- Job id, tenant id, type, attempts, last phase.
- Heartbeat age.
- PM2 worker state.
- Recent worker log around the job id.

Steps:

1. Run read-only snapshot.
2. Run `python pipeline.py recover-runtime`.
3. Recheck job state.
4. If still stale and PM2 shows unhealthy worker, restart only
   `fralib-worker`.
5. Recheck heartbeat and queue.

Do not delete the job or checkpoint.

## Playbook: Builder Timeout Or Provider Outage

Evidence:

- Phase `builder_renderer`.
- Provider alert.
- LLM ledger tokens/cost.
- Builder artifact path and last error.

Steps:

1. Confirm the issue is provider/model/runtime, not tenant input.
2. Let retry/backoff work if within limit.
3. If queue becomes stale, recover runtime.
4. Escalate provider key/model change to human or approved key repair flow.

Do not replace Builder output with a simpler static template.

## Playbook: Redis Down

Evidence:

- Health endpoint status.
- Redis process/service status.
- Whether auth/session/rate-limit is impacted.

Steps:

1. Confirm if Redis is required in current `FRALIB_ENV`.
2. If production and Redis is configured, restart Redis through infra-approved
   service command.
3. Re-run smoke/health.
4. Escalate if Redis repeatedly fails.

## Playbook: WhatsApp Bridge Down

Evidence:

- Meowhats port 3001 status.
- WhatsApp connection status.
- Pending SDR jobs by tenant.

Steps:

1. Confirm API is up before touching Meowhats.
2. Restart only `meowhats` if process is unhealthy.
3. Recheck connection.
4. Mark user-facing SDR status as pending/reconnect if needed.

Do not consume trial credit before the required WhatsApp send.

## Playbook: Lead Supply Empty

Evidence:

- Inventory count by niche/city/tenant.
- Caio rejection reasons.
- Provider errors.
- Pending production jobs.

Steps:

1. Check if it is no lead, provider timeout or Caio threshold.
2. Run approved Hunter/Caio job if safe.
3. Escalate repeated empty niche/city to capacity/product backlog.

## Playbook: Deploy Version Mismatch

Evidence:

- Local commit.
- Remote `/api/version`.
- Deploy hook output.
- PM2 restart status.

Steps:

1. Do not edit VPS manually.
2. Confirm commit was pushed to the branch hook publishes.
3. Inspect hook/PM2 output.
4. Re-push or fix hook through Git.

## Implementation Backlog

- Read-only snapshot script. Done: `scripts/hermes_snapshot.py`.
- Incident table or append-only log. Done: `hermes_incidents`.
- Guard allowlist/denylist test suite. Done: `tests/unit/test_hermes_watchdog.py`.
- Admin status page for queue, workers, payments and watchdog. Done: Super Admin Hermes tab.
- Scheduled canary that starts no paid external action. Done:
  `scripts/hermes_canary.py` and PM2 `fralib-hermes-watchdog`.
- Guarded auto-remediation. Done: worker stale recovery, critical PM2 restart,
  WhatsApp bridge restart and Mercado Pago idempotent reconciliation.
- Alert channel for SEV1/SEV2.
