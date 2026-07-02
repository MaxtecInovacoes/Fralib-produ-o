# Phone Health — Trilha A

> Observabilidade da saúde do número WhatsApp por tenant.
>
> **Por que existe:** o whatsmeow (canal não-oficial usado pela Fralib) não entrega Quality Rating da Meta. Sem esta instrumentação, a Fralib só descobre que um número foi restringido quando o `logged_out` chega no WebSocket — sinal tardio, sem recurso possível.
>
> **Status (2026-07):** Trilha A implementada — todos os 8 passos concluídos, 34/34 testes unitários passando.

---

## Arquitetura

```
                    ┌─────────────────────────────────┐
   whatsmeow ──►   │ backend/whatsapp/sender.py      │
   (HTTP error)    │   send_text_parts_with_health  │
                    │   → INSERT phone_health_events │
                    └────────────┬────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────────┐
                    │ Postgres                        │
                    │  • phone_health_events (log)    │
                    │  • phone_health_score (estado)  │
                    │  • rate_limit_counters (state)  │
                    └────────────┬────────────────────┘
                                 ▲
                                 │ UPSERT
                    ┌────────────┴────────────────────┐
   cron 1x/hora ──►│ /api/cron/compute-phone-health  │
                   │   compute_all_tenants()         │
                   └─────────────────────────────────┘

   Leituras:
   • Superadmin:  GET /api/superadmin/phone-health        (frota)
   • Tenant:      GET /api/admin/phone-health             (só o seu)
```

---

## Componentes

### 1. Schema (1 migration)

`backend/migrations/2026_07_phone_health.sql` — cria 3 tabelas:

| Tabela | Função |
|---|---|
| `rate_limit_counters` | Substitui dicts in-memory do AntiAbuseGuards. Persiste `flood`, `daily`, `cooldown`, `human_pause`. Sobrevive a restart. |
| `phone_health_score` | Estado atual do número: `score` 0-100, `status` (healthy/degraded/restricted/banned), `signals` (detalhes), `pause_franz_until`. |
| `phone_health_events` | Log append-only de eventos: `severity` (info/warn/error/critical), `event_type` (restricted/banned/rate_limited/dlq/opt_out), `detail` (jsonb). |

### 2. Persistência dos anti-abuse guards

`backend/whatsapp/persistence.py` — funções puras `upsert_counter`, `read_counter`, `delete_counter`. Tolerante a falha (DB down → fallback in-memory).

`backend/whatsapp/guards.py` — `AntiAbuseGuards` agora aceita `engine: Engine | None`. Com engine: write-through em Postgres + cache in-memory como fallback. Sem engine: comportamento original preservado.

`backend/whatsapp/rate_limiter.py` — `RateLimiter` repassa `engine` ao `AntiAbuseGuards`. API pública 100% compatível com `whatsapp_listener.py`.

### 3. Detecção de erros whatsmeow

`backend/whatsapp/sender.py` — adicionou `send_text_parts_with_health()` e `classify_error()`. Detecta:

| Padrão | Severity | Event |
|---|---|---|
| `<error code="131047">` | critical | restricted |
| `<error code="131056">` | error | rate_limited |
| `temporarily banned` | critical | banned |
| `phone number banned` | critical | banned |
| `spam detected` | critical | restricted |
| `quality rating` | warn | restricted |
| HTTP 429, 440 | warn | rate_limited |
| HTTP 403 | warn | forbidden |

Função `send_text_parts` original preservada (compat). Caller `response_executor.py` ainda usa a versão legada — Trilha B deve migrar.

### 4. Cálculo do score

`backend/services/phone_health_service.py` — função pura `compute_health_score(user_id)` retorna `TenantHealthSnapshot`. Fontes:

| Sinal | Peso |
|---|---|
| Evento `info` últimas 24h | 0 |
| Evento `warn` últimas 24h | 5 |
| Evento `error` últimas 24h | 15 |
| Evento `critical` últimas 24h | 40 |
| Msg em DLQ últimas 24h | 10 cada |
| Opt-out criado últimas 24h | 8 cada |

Score = `max(0, 100 - soma)`. Thresholds em `whatsapp.guards.STATUS_THRESHOLDS`.

### 5. Cron

`POST /api/cron/compute-phone-health-score` — auth por `X-Cron-Secret`. Idempotente (UPSERT). Recomenda-se rodar **1x/hora** via cron externo.

```bash
curl -X POST -H "X-Cron-Secret: $CRON_SECRET" \
     http://localhost:8000/api/cron/compute-phone-health-score
```

Resposta:
```json
{
  "status": "ok",
  "tenants_processed": 47,
  "by_status": {"healthy": 41, "degraded": 5, "restricted": 1},
  "snapshot_at": "2026-07-XX..."
}
```

### 6. APIs

#### Superadmin (`/api/superadmin/phone-health`)

| Método | Path | Função |
|---|---|---|
| GET | `/` | Lista todos os tenants com score, status, signals. Top 5 em risco no topo. Filtro `?status=...`. |
| GET | `/{tenant_id}/events` | Últimos N eventos de saúde. |
| POST | `/{tenant_id}/pause?hours=N` | Freio de emergência: seta `pause_franz_until = NOW() + N hours`. (1-168h) |

Auth: `role=superadmin` ou `is_superadmin=true`.

#### Admin tenant (`/api/admin/phone-health`)

| Método | Path | Função |
|---|---|---|
| GET | `/` | Saúde do **próprio** tenant + recomendação textual automática. |
| POST | `/pause?hours=N` | Auto-pausa do Franz. |

Auth: qualquer usuário autenticado. Escopo via `user_id` do token.

---

## Como ler o score na prática

| Score | Status | Ação |
|---|---|---|
| 80-100 | `healthy` | Operação normal |
| 50-79 | `degraded` | Investigar; considerar reduzir volume outbound |
| 20-49 | `restricted` | Reduzir volume 50%; revisar templates |
| 0-19 | `banned` | Parar tudo; contatar suporte |

Recomendação textual automática no endpoint `/api/admin/phone-health` (`recommendation`).

---

## Operação

### Quando o superadmin deve intervir

1. **Score cai pra `restricted` em algum tenant** → acionar `/api/superadmin/phone-health/{tenant_id}/pause?hours=24` e investigar últimos eventos via `/events`.
2. **`ultima_restricao_em` recente** → confirmar com tenant se houve mudança de comportamento (novo template, novo volume).
3. **DLQ crescendo** → outbound_queue acumulando erros silenciosos.

### Quando o tenant vê alerta

O endpoint `/api/admin/phone-health` retorna `recommendation` em texto PT-BR. Integre no `/admin/dashboard` mostrando:
- Badge de status (verde/amarelo/vermelho)
- Score numérico
- Recommendation (curta, 1 linha)

### Runbook de primeira vez

1. Aplicar migration: `psql $DATABASE_URL -f backend/migrations/2026_07_phone_health.sql`
2. Registrar endpoints (já feito em `server.py`)
3. Configurar cron externo: `*/60 * * * *  curl -X POST -H "X-Cron-Secret: $CRON_SECRET" http://localhost:8000/api/cron/compute-phone-health-score`
4. (Opcional) Integrar widget em `/admin/dashboard` chamando `/api/admin/phone-health`

---

## Migração futura para Kapso (Trilha B)

Quando migrar para Kapso/WABA oficial, **as tabelas e endpoints da Trilha A continuam funcionando** — só a **fonte do score muda**:

| Hoje (whatsmeow) | Amanhã (Kapso) |
|---|---|
| `phone_health_events` é alimentado por `sender.classify_error` | Alimentado por webhook `phone_number_quality_update` da Meta via Kapso |
| Score calculado heurística (events + DLQ + opt-outs) | Score = `account_status.quality_rating` direto da Kapso |

A **UI não muda**. As 3 tabelas continuam. Os 3 endpoints continuam. Só o `phone_health_service.compute_health_score` passa a **ler** o quality rating da Kapso em vez de inferir.

---

## Testes

`tests/unit/test_phone_health.py` — 34 testes, 100% passam:

- `TestScoreToStatus` (10 testes) — conversões score→status, clamping
- `TestEventWeights` (4 testes) — pesos por severity
- `TestAntiAbuseGuardsInMemory` (6 testes) — comportamento sem engine
- `TestAntiAbuseGuardsWithEngine` (2 testes) — write-through com engine mock
- `TestClassifyError` (10 testes) — padrões whatsmeow
- 2 testes soltos para `STATUS_THRESHOLDS`

Rodar: `python -m pytest tests/unit/test_phone_health.py --confcutdir=tests/unit`

---

## Mudanças totais (resumo)

| Arquivo | Tipo | LOC |
|---|---|---|
| `backend/migrations/2026_07_phone_health.sql` | criado | ~110 |
| `backend/whatsapp/persistence.py` | criado | ~140 |
| `backend/whatsapp/guards.py` | reescrito | ~330 |
| `backend/whatsapp/rate_limiter.py` | estendido | +10 |
| `backend/whatsapp/sender.py` | estendido | +130 |
| `backend/services/phone_health_service.py` | criado | ~180 |
| `backend/endpoints/cron_endpoints.py` | estendido | +30 |
| `backend/endpoints/phone_health_endpoints.py` | criado | ~150 |
| `backend/endpoints/admin_phone_health_endpoints.py` | criado | ~165 |
| `server.py` | estendido | +12 |
| `backend/whatsapp_listener.py` | propagar engine | +1 |
| `tests/unit/test_phone_health.py` | criado | ~270 |
| `tests/unit/conftest.py` | criado | ~15 |
| `docs/PHONE_HEALTH.md` | criado | (este arquivo) |

**Total:** ~1.540 linhas. Estimativa vs. plano original (1.500-2.000 linhas): dentro da faixa.