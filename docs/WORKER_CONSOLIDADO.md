# Arquitetura Worker Consolidado

> Última atualização: 2026-08-04
> Commit: deploy 3 containers → 1 unified worker

## Antes (3 workers + open-seo)

| Container | Função | Status |
|-----------|--------|--------|
| `fralib-worker-pipeline-1` | Consome `pipeline_lead` / `pipeline_multiplos` | running |
| `fralib-worker-cron-1` | `lead_supply_hunter`, `lead_production_tick` | healthy |
| `fralib-worker-franz-1` | SDR WhatsApp outreach | healthy |
| `open-seo` | SEO (morto) | — |

Problemas: 3 processos Python repetindo setup, 3 healthchecks, 3 containers pra gerenciar, código `franz_outreach` legado espalhado.

## Depois (1 worker)

```
┌─────────────────────────────────────────────────┐
│                  fralib-worker-1                  │
│                                                   │
│  python worker.py                                 │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  JOB_TIPOS (env WORKER_JOB_TYPES)           │ │
│  │                                             │ │
│  │  pipeline_lead          → _run_pipeline_job │ │
│  │  pipeline_multiplos     → _run_pipeline_job │ │
│  │  lead_production_tick   → _run_supply_job   │ │
│  │  lead_supply_caio       → _run_supply_job   │ │
│  │  lead_supply_hunter     → _run_supply_job   │ │
│  │  franz_outreach         → _run_franz_job    │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  Fila: SELECT FOR UPDATE SKIP LOCKED (Postgres)  │
│  Backoff: exponencial por tipo                    │
└─────────────────────────────────────────────────┘
```

## Como funciona o dispatch

`worker.py` carrega os tipos de job da env var `WORKER_JOB_TYPES` (comma-separated) via `_load_job_tipos()`.

Cada job na tabela `jobs` tem um campo `tipo`. O worker:

1. Busca jobs pendentes com `SELECT ... FOR UPDATE SKIP LOCKED`
2. Itera sobre os tipos habilitados
3. Despacha pro handler correspondente pelo tipo
4. Tipos desconhecidos → `mark_failure(retriable=False)`

## Escalabilidade

```bash
# 1 worker (default)
docker compose up -d worker

# 4 workers paralelos (cada um consome fila independente)
docker compose up -d --scale worker=4
```

O `SELECT ... SKIP LOCKED` garante que jobs não sejam processados duas vezes.

## Env vars do worker

| Var | Descrição | Default |
|-----|-----------|---------|
| `WORKER_JOB_TYPES` | Tipos habilitados (comma-separated) | `pipeline_lead,lead_production_tick,lead_supply_caio,lead_supply_hunter` |
| `MAX_PIPELINES_GLOBAL` | Max pipelines simultâneos | `4` |
| `OPENUI_SERVICE_URL` | URL do serviço OpenUI | `http://host.docker.internal:3333` |

## docker-compose.prod.yml

```yaml
worker:
  build: .
  environment:
    <<: *common-env
    WORKER_JOB_TYPES: pipeline_lead,pipeline_multiplos,lead_production_tick,lead_supply_caio,lead_supply_hunter,franz_outreach
    MAX_PIPELINES_GLOBAL: "4"
    OPENUI_SERVICE_URL: http://host.docker.internal:3333
  command: ["python", "worker.py"]
```

## Containers restantes

| Container | Função |
|-----------|--------|
| `fralib-app-1` | API FastAPI |
| `fralib-postgres-1` | PostgreSQL |
| `fralib-redis-1` | Redis |
| `fralib-worker-1` | Worker unificado |

`open-seo` removido. Os 3 workers legados são removidos automaticamente pelo `--remove-orphans` no deploy.

## Código removido

- `franz_outreach` — tipo de job, handler, backoff table, mensagens amigáveis
- `_BACKOFF_franz` — tabela de retry específica do Franz
- `tmp_deploy/` — diretório de deploy legado (Dockerfile agora na raiz)

## Pipeline de deploy

```
git push origin master
  → post-receive hook (100.124.56.36 /opt/fralib.git/)
    → git fetch + reset --hard
    → pycache clean
    → pip install
    → frontend publish
    → docker compose up -d --remove-orphans
```
