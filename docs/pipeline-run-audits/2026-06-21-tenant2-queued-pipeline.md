# Tenant 2 Queued Pipeline Observation - 2026-06-21

## Scope

Read-only observation requested for tenant 2. No VPS files, services, queue rows
or database records were changed.

## VPS Sync Check

- VPS `/root/fralib` hash observed before this change: `335cd075f14e3f6e73d6507b769279d3fd2bd0f2`.
- Local/GitHub moved while this work was running through ECC commits up to
  `9b274d7` before this backend telemetry commit.

## Tenant 2 Queue State

Recent tenant 2 `pipeline_lead` jobs observed in `jobs`:

| Job | Status | Run ID | Last phase | Created | Started | Finished |
|---:|---|---|---|---|---|---|
| 2615 | pending | `b984a449d532` | empty | 2026-06-21 02:53:52 | empty | empty |
| 2614 | pending | `ae7e492075d9` | empty | 2026-06-21 02:53:51 | empty | empty |
| 2613 | pending | `48e840cf1aaf` | empty | 2026-06-21 02:53:50 | empty | empty |
| 2612 | pending | `21f25a8f290c` | empty | 2026-06-21 02:53:49 | empty | empty |

Payload keys:

- Job 2612: `_run_id`, `force`.
- Jobs 2613-2615: `_parent_job_id`, `_run_id`, `cidade`, `lead_id`, `nome`,
  `proof`, `rating`, `score_caio`, `segmento`, `site_url`, `telefone`,
  `tenant_id`, `tier`, `whatsapp`.

## Tenant 2 Pipeline State

- `pipeline_state.rodando`: `false`.
- `pipeline_state.pausado`: `false`.
- `pipeline_state.updated_at`: `2026-06-18 21:00:14`.
- `pipeline_state.iniciado_em`: empty.

## Worker State

`ServiceManager` reported `worker` as:

```json
{
  "runtime": "systemd",
  "status": "inactive",
  "pid": 0,
  "restarts": 0,
  "last_error": null
}
```

`ServiceManager logs worker 120` returned `-- No entries --`.

## Measurement Status

No real phase duration, token total or cost total can be measured yet for jobs
2612-2615 because they remain pending and have no `iniciado_em`, spans or ledger
rows. The UI now distinguishes this as queue wait, not execution time.

## Next Observable Condition

When the official deployment hook or an operator-managed runtime action brings
`fralib-worker` back to `running`, the existing pending jobs should be claimed by
the worker. At that point `/api/pipeline/status` will expose:

- `telemetry.elapsed_seconds` from `jobs.iniciado_em` to `concluido_em` or now;
- `telemetry.queued_seconds` from `jobs.criado_em` until claim time;
- per-phase spans from `pipeline_run_spans`;
- total calls/tokens/cost from `llm_budget_ledger`;
- structured phase events on the tenant SSE stream.
