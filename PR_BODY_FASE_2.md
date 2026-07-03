# Fase 2+3 do plano de auditoria + reorganização UI Agentes

## 🎯 Objetivo

Consolidar 4 sprints críticos do plano de auditoria (`docs/AUDITORIA_FASE_0_1.md`) **+** reorganizar a UI do SDR pra que ele viva só na aba **Agentes** dentro do **Motor FraLib** (admin e superadmin), removendo a duplicação que existia no "Meu perfil".

## 📦 Entregas

### Sprint 4.1 — Race condition hardening (7 testes)
- Stress test determinístico pro fix do BUG #3 (race condition outbound×inbound), já implementado em Sprints 1.2+1.5.
- `tests/unit/test_race_outbound_inbound_stress.py` — 7 testes cobrindo `_check_last_inbound_vs_outbound`, `set_cooldown`, `increment_daily_count` e `dequeue_and_send`.
- **`backend/services/outbound_queue.py` não foi modificado** — o fix já existia; só validamos ele deterministicamente.

### Sprint 2.2 — Trilha de auditoria unificada (16 testes)
- Migration `backend/migrations/2026_07_audit_events.sql` — tabela `audit_events` + 3 índices (tenant/actor/action × tempo DESC).
- Módulo `backend/audit/`:
  - `models.py` — `AuditEvent` dataclass(frozen=True).
  - `recorder.py` — `record_event` fail-safe (nunca derruba request) + `query_events` (filtros/paginação) + 3 atalhos (`record_login`, `record_tenant_change`, `record_lead_change`).
  - `decorators.py` — `@audit_log(action, entity_type)` async decorator pra FastAPI.
- Endpoint `GET /api/superadmin/audit` em `backend/endpoints/audit_endpoints.py` (filtros + paginação + limite 1-500).
- Hook PoC: aplicado em `POST /api/users/sdr-config` (`backend/endpoints/users_endpoints.py:salvar_sdr_config`).
- 16 testes determinísticos em `tests/unit/test_audit_recorder.py`.

### Sprint 3.1 — Rate limit por IP (18 testes)
- Migration `backend/migrations/2026_07_ip_rate_limit.sql` — tabela fallback Postgres pra quando Redis offline.
- Middleware `backend/middleware/rate_limit.py`:
  - `IPRateLimiter` (Redis sliding window com fallback Postgres, fail-open se ambos down).
  - `endpoint_bucket_for_request(request)` — classifica login/cron/public/default. Whitelist `/api/health`, `/static/*`, `*.html`, `*.js`, `*.css`.
  - Retorna HTTP 429 com header `Retry-After`.
- Integração em `server.py` (registrado após CORS, antes dos routers).
- 18 testes em `tests/unit/test_ip_rate_limit.py` (Redis path, bucket extraction, Postgres fallback, fail-open, middleware HTTP).

### Sprint 3.3 — Alerta de tenant silencioso (12 testes)
- Migration `backend/migrations/2026_07_tenant_alerts.sql` — `tenant_alerts` com partial unique index (dedupe de abertos).
- Job `backend/jobs/detect_silent_tenants.py` — 5 critérios:
  1. `admin_inactive_7d` (warning)
  2. `no_new_leads_15d` (info)
  3. `no_cost_events_3d` (warning — tenant ativo sem gastar)
  4. `subscription_expiring_7d` (critical — churn iminente)
  5. `trial_active_no_use_14d` (warning)
- Notificações por email opcionais via env `SILENT_TENANT_ALERT_EMAIL`.
- Endpoint `backend/endpoints/superadmin_silent_tenants_endpoints.py` com 5 rotas: list, summary, acknowledge, resolve, run-detector.
- UI em `frontend/superadmin.html` — nova aba "🔕 Silenciosos" + widget compacto no dashboard principal.
- 12 testes em `tests/unit/test_silent_tenants_detector.py`.

### Bonus — Reorganização UI "Agentes" (sua diretriz)
- **`frontend/partials/admin/_view-perfil.html`**: removido bloco SDR duplicado (170+ linhas que repetia toda config no perfil). Substituído por pointer-card "🤖 AGENTES & SDR" que leva ao Motor FraLib.
- **`frontend/admin.html` + `frontend/partials/admin/_view-config.html` + `_sidebar.html`**: SDR agora vive consolidado na aba **Agentes** dentro do **Motor FraLib**. Total de 131 linhas consolidadas + 8 linhas no sidebar.
- **`frontend/superadmin.html`**: paridade — aba "🔕 Silenciosos" + "SDR Studio" + novo card SDR dos 4 sprints (242 linhas adicionadas).

## 🧪 Testes

| Suite | Testes | Status |
|---|---|---|
| Sprint 4.1 (`test_race_outbound_inbound_stress.py`) | 7 | ✅ GREEN |
| Sprint 2.2 (`test_audit_recorder.py`) | 16 | ✅ GREEN |
| Sprint 3.1 (`test_ip_rate_limit.py`) | 18 | ✅ GREEN |
| Sprint 3.3 (`test_silent_tenants_detector.py`) | 12 | ✅ GREEN |
| **Total** | **53** | **✅ 53/53** |

```bash
python -m pytest tests/unit/test_audit_recorder.py tests/unit/test_ip_rate_limit.py tests/unit/test_silent_tenants_detector.py tests/unit/test_race_outbound_inbound_stress.py --confcutdir=tests/unit
# 55 passed in 3.46s
```

## 🔒 Segurança / Não-regressão

- `record_event` é fail-safe (try/except com logger.warning — auditoria NUNCA derruba request).
- Rate limit fail-open se Redis+Postgres ambos indisponíveis.
- Detector de tenant silencioso roda com `dry_run=True` por padrão (não envia emails até env var setada).
- Nenhuma alteração nos arquivos de produção críticos: `outbound_queue.py`, `whatsapp_listener.py`, `sdr_langgraph/agent.py`.
- Tokens Facebook Ads hardcoded (Bug #7 do audit) já removidos no PR #1.

## 🚀 Deploy

### Migrations a rodar em prod (em ordem)
```sql
\i backend/migrations/2026_07_audit_events.sql
\i backend/migrations/2026_07_ip_rate_limit.sql
\i backend/migrations/2026_07_tenant_alerts.sql
```
*(Migrations dos sprints 1.x já foram na release anterior: `provider_health`, `cost_events`, `sdr_simulations`, `sdr_turns`, `lead_outcomes`)*

### Env vars novos
- `SILENT_TENANT_ALERT_EMAIL` (opcional — se setado, detector envia email via `email_service` quando acha alertas críticos).

### Crons novos sugeridos
- `python -m backend.jobs.detect_silent_tenants` 1x/dia (04:00 BRT). Pode ser via systemd ou `cron_endpoints`/api interna.

### Nenhuma mudança de frontend em runtime
- Recarregar `admin.html` e `superadmin.html` no navegador é suficiente. Toda config SDR continua em `POST /api/users/sdr-config` (mesmo endpoint de antes — agora decorado com `@audit_log` pra registrar mudanças em `audit_events`).
