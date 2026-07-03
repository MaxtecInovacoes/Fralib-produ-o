# RUNBOOK — Plano SDR (Operação 24/7)

> **Quem lê isso**: plantão às 3h da manhã com report "Franz parou de responder".
> **Objetivo**: ter um caminho claro diagnose → recover para os 8 cenários mais comuns.

---

## 📋 TL;DR — diagnóstico rápido

```bash
# 1. Backend ta up?
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/health
# esperado: 200

# 2. WhatsApp conectado?
curl -s http://localhost:8000/api/admin/phone-health | jq '.tenants[].status'
# esperado: "connected" para tenants ativos

# 3. Ultima atividade do Franz
psql $DATABASE_URL -c "SELECT MAX(criado_em) FROM sdr_turns;"
# esperado: <5 min atras
```

Se algum desses falha, vá para o cenário específico abaixo.

---

## 🔴 Cenário 1 — Redis indisponível

**Sintomas**:
- `redis.exceptions.ConnectionError` nos logs
- `whatsapp_listener` loga: "Redis offline para lead X"
- Outbound queue para de processar

**Diagnose**:
```bash
docker ps | grep redis
# OU
systemctl status redis
redis-cli ping
```

**Recover**:
```bash
# Restart Redis
systemctl restart redis
# OU
docker restart fralib-redis

# Verificar:
redis-cli ping  # → PONG

# Limpar locks stale (se houver):
redis-cli --scan --pattern "fralib:lead_lock:*" | xargs -r redis-cli del
```

**Post-mortem**:
- Verificar `journalctl -u redis` para OOM/restart
- Confirmar que `maxmemory-policy` está `allkeys-lru` (evita OOM)

---

## 🟠 Cenário 2 — LLM rate limit (429)

**Sintomas**:
- Logs: `429 Too Many Requests` de Anthropic/OpenRouter
- SDR para de responder após alguns turnos
- `sdr_turns` mostra `error_code = 429`

**Diagnose**:
```sql
SELECT count(*), date_trunc('hour', criado_em) 
FROM sdr_turns 
WHERE error_code = 429 
GROUP BY 2 
ORDER BY 2 DESC LIMIT 6;
```

**Recover**:
- **Curto prazo**: aumentar `LEAD_LOCK_TIMEOUT` para 120s (dar tempo ao backoff)
- **Médio prazo**: implementar fallback de template hardcoded (Sprint 1.5)
- **Longo prazo**: contratar tier maior do provedor

**Escalation**:
- Se > 100 leads esperando > 30 min: ligar para suporte Anthropic

---

## 🟠 Cenário 3 — LLM 5xx (500/503)

**Sintomas**:
- `error_code` em sdr_turns é 500 ou 503
- Franz responde com delay > 30s

**Diagnose**:
```bash
# Status do provedor:
curl -s https://status.anthropic.com/api/v2/status.json | jq '.status.indicator'
# OU
curl -s https://status.openai.com/api/v2/status.json | jq '.status.indicator'
```

**Recover**:
- Imediato: circuit breaker deve estar ativo (verificar `llm_router.py`)
- Backoff: 60s → 120s → 240s
- Se > 5min: switch pra modelo alternativo (Haiku em vez de Sonnet)

---

## 🔴 Cenário 4 — WhatsApp ban/restricted

**Sintomas**:
- `phone_health_score` despencou pra `banned`
- Logs: "phone restricted" ou "429 do WhatsApp"
- Mensagens não saem

**Diagnose**:
```bash
# Verificar status atual:
psql $DATABASE_URL -c "SELECT user_id, status, score, ban_reason FROM phone_health_score WHERE status='banned' ORDER BY updated_at DESC LIMIT 10;"

# Verificar cooldown:
psql $DATABASE_URL -c "SELECT user_id, pause_franz_until FROM phone_health WHERE pause_franz_until > NOW();"
```

**Recover**:
1. **Pare o Franz imediatamente** (já é automático via `pause_franz_until`)
2. **Aguarde 24-48h** antes de tentar reconectar
3. **Não tente forçar** — WhatsApp detecta e bane de novo
4. Após cooldown: rotação de número ou usar número novo

**Prevenção**:
- Respeitar `daily_limit` e `cooldown_seconds`
- Não usar templates duplicados
- Manter humanized_delay entre 1.5s-8s

---

## 🟠 Cenário 5 — Franz travado

**Sintomas**:
- Lead mandou msg, mas sdr_turns não atualiza há > 10min
- Logs param de aparecer

**Diagnose**:
```sql
-- Ultimo turno:
SELECT MAX(criado_em) FROM sdr_turns;

-- Turnos travados em 'processing':
SELECT * FROM sdr_turns WHERE status='processing' AND criado_em < NOW() - INTERVAL '5 minutes';
```

**Recover**:
```bash
# Restart do worker (sem perder dados):
systemctl restart fralib-sdr-worker

# Limpar turnos travados:
psql $DATABASE_URL -c "UPDATE sdr_turns SET status='failed', error='worker_restart' WHERE status='processing' AND criado_em < NOW() - INTERVAL '5 minutes';"
```

**Post-mortem**:
- Verificar se Redis lock está stale
- Se recorrente: implementar watchdog que mata worker travado

---

## 🟡 Cenário 6 — Tenant silencioso

**Sintomas**:
- Tenant com `status='active'` mas 0 atividade em 7+ dias
- Detector já identificou (`tenant_alerts` table)

**Diagnose**:
```sql
SELECT user_id, criado_em, ultimo_acesso 
FROM users 
WHERE status='active' 
  AND (ultimo_acesso IS NULL OR ultimo_acesso < NOW() - INTERVAL '14 days')
ORDER BY criado_em DESC;
```

**Recover**:
- **Email automático** (já implementado no `detect_silent_tenants.py`)
- **Ação manual**: superadmin envia email "ainda usando?"
- Se não responder em 30d: marcar trial expirado

**Prevenção**:
- Onboarding wizard com WhatsApp connection no passo 1
- Re-engagement push após 5 dias sem uso

---

## 🟡 Cenário 7 — Pipeline jobs estagnados

**Sintomas**:
- `pipeline_jobs` table com jobs `running` há > 1h
- Sites não estão sendo gerados

**Diagnose**:
```sql
SELECT id, tenant_id, started_at, EXTRACT(EPOCH FROM (NOW() - started_at)) as age_sec
FROM pipeline_jobs
WHERE status='running' AND started_at < NOW() - INTERVAL '1 hour'
ORDER BY started_at;
```

**Recover**:
```bash
# Marcar como failed (vai ser reprocessado):
psql $DATABASE_URL -c "UPDATE pipeline_jobs SET status='failed', error='stale_cleanup' WHERE status='running' AND started_at < NOW() - INTERVAL '1 hour';"

# Trigger reprocess:
python -m backend.jobs.reprocess_failed_pipeline_jobs
```

---

## 🟡 Cenário 8 — Outbound queue DLQ

**Sintomas**:
- Outbound queue parou de processar
- Mensagens acumulando em status `failed`

**Diagnose**:
```sql
SELECT count(*), error 
FROM outbound_queue 
WHERE status='failed' 
GROUP BY error 
ORDER BY count DESC LIMIT 10;
```

**Recover**:
```bash
# Inspect:
psql $DATABASE_URL -c "SELECT id, lead_id, error, attempts, created_at FROM outbound_queue WHERE status='failed' ORDER BY created_at DESC LIMIT 20;"

# Reprocessar (reset pra pending):
psql $DATABASE_URL -c "UPDATE outbound_queue SET status='pending', scheduled_at=NOW(), error=NULL WHERE status='failed' AND attempts < 3;"

# Descartar definitivamente:
psql $DATABASE_URL -c "UPDATE outbound_queue SET status='discarded' WHERE status='failed' AND attempts >= 3;"
```

---

## 📞 Contatos de escalation

- **Anthropic support**: https://support.anthropic.com
- **WhatsApp/Meta support**: via developer dashboard
- **VPS hosting**: provider support
- **On-call dev**: ver `docs/CONTACTS.md` (criar)

---

## 🛠️ Comandos úteis

```bash
# Conectar no DB
psql $DATABASE_URL

# Ver últimas 50 linhas de log
journalctl -u fralib-sdr-worker -n 50 --no-pager

# Restart sem downtime
systemctl reload fralib-sdr-worker  # ou restart se reload não funciona

# Forçar reprocess de um lead específico
python -c "from backend.agents.sdr_langgraph.agent import reprocess_lead; reprocess_lead(lead_id=123)"
```

---

**Última atualização**: Sprint 1.3 (atomicidade + LGPD + redis + debounce + tx + budget)
**Owner**: @codex
**Review**: mensal
