# FraLib — RUNBOOK Operacional

**Propósito:** resposta a incidentes e troubleshooting diário. **Diferente** do `PLAYBOOK_PIPELINE_VALIDADA.md` (que documenta o caminho feliz) e do `ARCHITECTURE.md` (que descreve o sistema). Este aqui é **o que fazer quando algo quebra**.

**Última atualização:** 2026-08-04

---

## 0. Acesso rápido

```bash
# VPS
ssh -i ~/.ssh/id_ed25519 root@100.124.56.36

# Containers
docker ps                       # status atual
systemctl status fralib-api      # API FastAPI (systemd)
docker logs -f fralib-worker-1  # worker unificado (pipeline + supply + Franz)
journalctl -u fralib-openui -f  # OpenUI HTML generation

# Banco
docker exec -it fralib-postgres-1 psql -U fralib_user -d fralib_db
```

---

## 1. Worker travado / não processa jobs

### Sintomas
- `docker logs -f fralib-worker-1` mostra heartbeat parado há > 2min
- Fila `jobs` cresce: `SELECT count(*) FROM jobs WHERE status='pending'`

### Diagnóstico
```sql
-- Jobs travados em running com heartbeat velho (> 5min)
SELECT id, tipo, attempts, last_error, worker_id,
       NOW() - worker_heartbeat AS idade
FROM jobs
WHERE status='running'
ORDER BY worker_heartbeat ASC NULLS FIRST;

-- Reaper ressuscita jobs travados automaticamente (reap_dead_workers).
-- Se nao voltou, forcar:
UPDATE jobs
SET status='pending', worker_heartbeat=NULL, worker_id=NULL,
    next_retry_at=NOW()
WHERE status='running' AND worker_heartbeat < NOW() - INTERVAL '5 minutes';
```

### Causa comum
- Deploy matou worker mid-job (já tratado por `reap_dead_workers` rodando no `lifespan`)
- Container OOM — `docker inspect fralib-worker-1 | grep -i oom`
- DB connection pool esgotado — `last_error: 'connection timeout'`

### Restart seguro
```bash
docker compose -f docker-compose.prod.yml restart fralib-worker-1
# NAO restart fralib-api sem motivo — quebra jobs em_andamento
```

---

## 2. Pipeline falha em uma fase específica

### Identificar fase
```sql
SELECT lead_id, fase, mensagem_amigavel, erro_tecnico,
       tentativas_automaticas, criado_em
FROM pipeline_failures
ORDER BY criado_em DESC LIMIT 20;
```

### Mapa fase → agente
| fase | agente | arquivo |
|------|--------|---------|
| `hunter` | Hunter | `backend/agents/agente1_hunter_v2.py` |
| `caio` | Caio | `backend/agents/caio.py` |
| `theo` | Theo | `backend/agents/theo.py` |
| `arquiteto` | Designer/Arquiteto | `backend/agents/arquiteto_mestre.py` |
| `liam` / `builder` | Builder | `backend/agents/builder/agent.py` |
| `liz` | Liz | `backend/agents/liz.py` |
| `deploy` | Deploy | `backend/endpoints/pipeline_endpoints.py` |

### Erro de LLM (rate limit / 503 / overloaded)
- **Causa:** DeployFlow 9router retornando 429 ou 529
- **Ver:** `last_error` contém `RateLimitError`, `APIError`, `overloaded`
- **Ação:** automática via `job_queue.mark_failure()` com backoff 30s/2min/8min
- **Manual:** se esgotar retries (max_attempts=3), o job vai para `failed_permanent` e vira linha em `pipeline_failures`. Cliente vê mensagem amigável e botão "Tentar de novo"

### Erro de HTML (Builder LiteLLM)
- Sintoma: `last_error: 'JSON decode'`, `'Builder html vazio'`, `'tag não fechada'`
- **Ação:** `repair_loop` regenera (Vision QA v2). Se passar, deploy segue. Se falhar 3x, failed_permanent.

### Erro de timeout
- Sintoma: `TimeoutError`, `ReadTimeout`
- **Ação:** backoff padrão. Se recorrente em escala, ajustar timeout no agent.

---

## 3. OpenUI offline (HTML não gera)

### Sintoma
- Logs: `Connection refused on :7878` ou `OpenUI unavailable`
- Fila trava em `fase=builder`

### Diagnóstico
```bash
systemctl status fralib-openui
journalctl -u fralib-openui -n 50 --no-pager
curl -s http://localhost:7878/v1/models || echo OFFLINE
```

### Restart
```bash
systemctl restart fralib-openui
sleep 3
curl -s http://localhost:7878/v1/models
```

### Se persiste
1. Verificar env em `/opt/fralib/openui-wandb/backend/.env` (especialmente `ANTHROPIC_API_KEY` e `ANTHROPIC_BASE_URL`)
2. Verificar log: `journalctl -u fralib-openui -f` durante 30s
3. Se `MODULE_NOT_FOUND`: `systemctl restart fralib-openui`

---

## 4. Postgres cheio / lento

### Sintoma
- `docker logs fralib-postgres-1` mostra `disk full`
- Queries > 5s no app

### Diagnóstico
```sql
-- Tamanho das tabelas
SELECT schemaname, relname,
       pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 15;

-- Vacuum status
SELECT relname, last_vacuum, last_autovacuum,
       n_dead_tup, n_live_tup
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 10;
```

### Ação
```bash
# Vacuum manual se autovacuum nao acompanhou
docker exec fralib-postgres-1 vacuumdb -U fralib_user -d fralib_db --analyze

# Limpar checkpoints expirados (>24h) — backend/agents/pipeline_checkpoint.py
systemctl restart fralib-api && sleep 3 && journalctl -u fralib-api --since "1 min ago" | grep "limpar_checkpoints"

# Limpar pipeline_traces > 30 dias
docker exec fralib-postgres-1 psql -U fralib_user -d fralib_db -c \
  "DELETE FROM pipeline_traces WHERE criado_em < NOW() - INTERVAL '30 days'"
```

---

## 5. Redis cheio / evictions

### Sintoma
- Cache miss frequente, app lento
- `docker logs fralib-redis-1` mostra `evicted_keys`

### Diagnóstico
```bash
docker exec fralib-redis-1 redis-cli INFO memory | grep -E 'used_memory_human|maxmemory_human'
docker exec fralib-redis-1 redis-cli INFO stats | grep evicted_keys
```

### Ação
- `maxmemory-policy` deve ser `allkeys-lru` (verificar em docker-compose.prod.yml)
- Se evictions constantes: aumentar `maxmemory` no compose ou reduzir TTL dos caches

---

## 6. Franz (SDR WhatsApp) com bug

### Sintoma
- Mensagens nao saem, leads sem follow-up
- `docker logs fralib-worker-1` mostra erros de meowhats
- Franz agent loop falhou (fallback para Franz legacy)

### Diagnóstico
```bash
# Status da sessao
curl -H "X-API-Key: $MEOWHATS_KEY" http://localhost:3001/api/sessions/1/status

# Mensagens pendentes na fila
SELECT count(*) FROM jobs WHERE tipo='franz_outreach' AND status='pending';

# Agent loop desativado?
journalctl -u fralib-api | grep -i "Franz agent loop"
# Procure por: "Franz agent loop falhou, fallback legacy"
```

### Ação
- Reconectar: `curl -X POST -H "X-API-Key: $MEOWHATS_KEY" http://localhost:3001/api/sessions/1/connect`
- Verificar logs: `docker logs meowhats-1` se container separado
- Verificar se `FRANZ_AGENT_LOOP=1` no .env (ativado por padrão)
- Ver memory: [[handoff-franz-bugs-contexto-transacao.md]] — problemas CoT, transação, LID
- Tool failures: `pipeline_failures` com `fase='franz'` ou `fase='Franz'`

---

## 7. Rollback de deploy

### Quando fazer
- Erro crítico em produção nao resolvido em < 30min
- Vision QA regredindo sistematicamente
- Banco corrompido

### Como
```bash
# 1. Identificar ultimo commit bom
cd /opt/fralib && git log --oneline -20

# 2. Reverter (gera commit de revert)
git revert <commit_hash>
git push origin master

# 3. Hook post-receive dispara redeploy automático
# NAO precisa rebuild manual a menos que Dockerfile tenha mudado
```

### Se HA urgência extrema (rollback sem deploy completo)
```bash
# Checkout do commit anterior
cd /opt/fralib && git checkout HEAD~1 -- backend/
systemctl restart fralib-api fralib-worker

# LEMBRETE: isso é mutação direta na VPS. Só com autorização.
# Regra #7: preferir git push normal.
```

---

## 8. Erros estruturados — onde olhar

### Tabela `pipeline_error_log`
Cada erro de step é logado com:
- `lead_id`, `tenant_id`, `step_name`
- `exception_type`, `message`, `traceback_text`
- `categoria` (TIMEOUT / LLM_ERROR / DB_ERROR / HTML_ERROR / UNKNOWN)
- `criado_em`

```sql
-- Top erros nas últimas 24h
SELECT categoria, exception_type, count(*) AS n,
       max(criado_em) AS ultimo
FROM pipeline_error_log
WHERE criado_em > NOW() - INTERVAL '24 hours'
GROUP BY 1,2
ORDER BY n DESC;
```

### Tabela `pipeline_traces`
Trace completo de cada run do pipeline.

**Colunas principais:** `trace_id`, `run_id`, `status` (completed/failed), `duracao_total_ms`, `complexidade` (fase final), `total_input_tokens`, `total_output_tokens`, `total_cache_hit`, `custo_total_usd`, `total_chamadas_llm`, `spans_json`.

**Spans JSON** contém array com spans: `step_hunter`, `step_caio`, `step_arquiteto`, `step_builder`, `step_quality_gate`, `step_deploy`, `step_franz` + spans LLM individuais (`llm_{agente}`).

**Instrumentation:** `worker.py` → cria `Trace` + `TokenTracker` → set_tracker() → pipeline executa → llm_direct.py auto-registra chamadas → token data vira spans → `_agregar_metricas()` soma tokens/custo no trace-level → `salvar_trace()` persiste.

**Custo:** Calculado via `_calcular_custo()` em `token_tracker.py` usando PRECOS_POR_MILHAO.

**Consultas úteis:**
```sql
-- Custo médio por lead (último mês)
SELECT lead_nome, COUNT(*) runs, AVG(custo_total_usd) avg_cost, SUM(total_chamadas_llm) llm_calls
FROM pipeline_traces WHERE status = 'completed' AND criado_em > NOW() - INTERVAL '30 days'
GROUP BY 1 ORDER BY avg_cost DESC;

-- Token mais caro (agent bottleneck)
SELECT jsonb_each(spans_json->0) ... -- ver spans_json por run

-- Filtrar por tier/complexidade
SELECT complexidade, COUNT(*), AVG(custo_total_usd) FROM pipeline_traces WHERE status = 'completed' GROUP BY 1;
```

### Tabela `api_usage_snapshots`
Snapshot diário de rate-limits Anthropic. Alertar quando `remaining < 10%`.

---

## 9. Quando escalar para o humano

| Situação | Ação |
|----------|------|
| Deploy quebrou e rollback nao resolve | `git log` + `git diff`, abrir issue |
| VPS inacessível (SSH falha) | Tailscale off? Reiniciar roteador. Painel cloud provider |
| Banco corrompido | NÃO mexer — acionar backup antes |
| LLM rate limit em massa | Pausar jobs: `UPDATE jobs SET status='paused' WHERE tipo IN ('pipeline_lead','pipeline_multiplos')` |
| Vision QA regredindo | Ver [[drama-visual-v1.md]] e [[signature-mecanismo-deterministico.md]] |
| Cliente reclama erro X | Buscar em `pipeline_failures` por `mensagem_amigavel` |

---

## 10. Contatos e referências

- **DeployFlow API:** https://deployflow.com.br — provider LLM (Anthropic proxy)
- **Meowhats (WhatsApp):** container isolado, porta 3001
- **Domínio produção:** https://app.seunegociofralib.site
- **Documentação relacionada:**
  - `docs/ARCHITECTURE.md` — visão geral
  - `docs/PLAYBOOK_PIPELINE_VALIDADA.md` — caminho feliz validado
  - `docs/ARQUITETURA_DEPLOY.md` — deploy e infra
  - `docs/FILE_DICTIONARY.md` — mapa de arquivos
  - `docs/DATA_FLOW.md` — fluxo de dados

## 8. Validar observabilidade (E2E)

### Pré-requisitos
- Feature flag `FRALIB_TRACING=1` no `docker-compose.prod.yml` (já ativo)
- Tabela `pipeline_traces` criada no banco (ver schema em `backend/observability.py`)
- Worker rodando: `docker ps | grep worker`

### Passo 1 — Trigger pipeline
```bash
# Via API (substituir token/lead_id)
curl -X POST https://app.seunegociofralib.site/api/pipeline/start \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"lead_id": <id>}'
```

### Passo 2 — Verificar trace no banco
```sql
SELECT trace_id, lead_nome, status, duracao_total_ms,
       total_input_tokens, total_output_tokens, custo_total_usd,
       total_chamadas_llm, jsonb_array_length(spans_json) as spans_count
FROM pipeline_traces
ORDER BY created_at DESC LIMIT 5;
```

### Passo 3 — Verificar dashboard
```bash
curl -s https://app.seunegociofralib.site/api/observability/dashboard | jq
# Esperado: total_runs > 0
```

### Passo 4 — Verificar spans por agente
```bash
curl -s https://app.seunegociofralib.site/api/observability/por-agente | jq
# Esperado: linhas para hunter, caio, arquiteto, builder, etc.
```

### Troubleshooting
| Sintoma | Causa | Fix |
|---------|-------|-----|
| `total_runs = 0` | Worker sem FRALIB_TRACING=1 | Verificar env var no compose |
| `total_runs = 0` | Nenhum job rodou desde deploy | Trigger manual |
| Trace sem spans | `salvar_trace()` falhou | Verificar logs do worker |
| Tabela não existe | Migration ausente | Criar manualmente ou rodar alembic |