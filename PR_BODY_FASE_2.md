# Fase Completa: Fase 1 (Sprints 1.1-1.5) + Fase 2 (Auditoria + UI Agentes) + Hardening Pós-Auditoria

## 🎯 Objetivo

Entrega das **Sprints 0.1-1.5** do plano de auditoria (`docs/AUDITORIA_FASE_0_1.md`), **+ 4 sprints Fase 2** (4.1, 2.2, 3.1, 3.3) **+ reorganização UI Agentes no admin** **+ hardening pós-adversarial** com 16 bugs consertados (1 P0 segurança + 6 P1 funcionais + 4 P2 qualidade + 5 melhorias) e **66 testes** dos 4 sprints Fase 2 passando 100%.

## 📦 Entregas por sprint

### Sprint 4.1 — Race condition hardening (7 testes)
- `tests/unit/test_race_outbound_inbound_stress.py` valida determinísticamente o fix das Sprints 1.2+1.5 já existente em `backend/services/outbound_queue.py`.

### Sprint 2.2 — Trilha de auditoria unificada (24 testes)
- Migration `2026_07_audit_events.sql` (tabela + 3 índices).
- Módulo `backend/audit/` (4 arquivos): `models.py`, `recorder.py` (fail-safe), `decorators.py` (`@audit_log` + `entity_id_from`).
- Endpoint `GET /api/superadmin/audit` com validação ISO 8601 em `since`/`until`.

### Sprint 3.1 — Rate limit por IP (23 testes)
- Migration `2026_07_ip_rate_limit.sql` (fallback Postgres).
- `backend/middleware/rate_limit.py` com Redis pipeline (atomic) + Postgres fallback + **XFF spoof protection** via `TRUSTED_PROXIES` env.

### Sprint 3.3 — Alerta de tenant silencioso (12 testes)
- Migration `2026_07_tenant_alerts.sql` (partial unique index).
- `backend/jobs/detect_silent_tenants.py` (5 critérios + trial_no_use que cobre quem logou uma vez e parou).
- Endpoint `superadmin_silent_tenants_endpoints` (5 rotas).

### Hardening pós-adversarial (commit `2bf248b`)
| Bug | Severidade | Fix |
|---|---|---|
| **P0** Rate limit aceita XFF spoof | segurança | `_client_ip` ignora XFF a menos que `TRUSTED_PROXIES` configurado |
| **P1** `record_event` deixa transação pendurada | funcional | troca `engine.connect()` por `engine.begin()` |
| **P1** `@audit_log` entity_id sempre=user | funcional | novo kwarg `entity_id_from` |
| **P1** `audit_endpoints` bypass com email vazio | segurança | valida email antes de `is_superadmin()` |
| **P1** `audit_endpoints` since/until sem validar | UX | 422 em ISO inválido (em vez de 500) |
| **P1** `trial_no_use_14d` só pega never-logged | funcional | agora cobre quem logou e parou |
| **P1** `run_detector` INSERT com schema errado | funcional | usa `record_event()` correto |
| **P2** Redis `incr` + `expire` não-atômicos | qualidade | pipeline |
| **P2** `_check_postgres` não tem teste real | qualidade | adicionado |
| **P2 UX** Simulador Franz dispara 429 em dev | UX | bucket dedicado `simulador.*` 600/min + `RATE_LIMIT_DEV_OPEN=1` para loopback |
| **🔴 UX** Simulador dispara 403 CSRF | UX | `sdr-simulator.js` agora usa `CSRFHelper.fetch` que injeta `X-CSRF-Token` |
| **🔴 UX** Browser servia `csrf-helper.js` cacheado pré-fix | UX | bump `?v=` em `admin.html:25` pra `20260702-sprint11` |
| **🔴 UX** Card simulador escondido, sem link no sidebar | UX | novo link âncora "🧪 Simulador" com `scrollIntoView` |
| **🟡 UX** Textarea sem `maxlength` | UX | `maxlength=4000` + contador `N/4000` em tempo real |
| **🟡 UX** Erros HTTP crus ("HTTP 403 — {...}") | UX | `friendlyError()` mapeia 401/403/422/429/5xx pra PT-BR com dica |
| **🟡 UX** Badge `sdrSimulatorSync` mentia "pronto" | UX | estados idle/warn/ok/err com cor por estado |
| **P2 UX** Simulador Franz dispara 403 CSRF | UX | `sdr-simulator.js` trocou `fetch()` por `CSRFHelper.fetch()` (helper já existia em `csrf-helper.js`, só não estava sendo usado) |

### UI — SDR consolidado na aba Agentes (commit `01d24965` + `a9d4aec4`)
- `_view-perfil.html`: removido bloco SDR duplicado (170+ linhas). Substituído por pointer-card 🤖 AGENTES → Motor FraLib.
- `_view-config.html` + admin.html: SDR consolidado em view única.
- superadmin.html: paridade (SDR Studio + aba Silenciosos).

## 🧪 Testes

| Sprint | Testes | Status |
|---|---|---|
| 4.1 race stress | 7 | ✅ |
| 2.2 audit (16 originais + 8 novos pós-hardening) | **24** | ✅ |
| 3.1 rate limit (18 originais + 5 novos XFF spoof) | **23** | ✅ |
| 3.3 silent tenants | 12 | ✅ |
| **TOTAL Fase 2** | **66** | ✅ **66/66 GREEN** |

Adicional: 5 melhorias de qualidade (XFF spoof protection testado, decorator entity_id_from coberto, decorator pipelined).

## 🚀 Deploy

Migrations em prod (em ordem):
```sql
\i backend/migrations/2026_07_audit_events.sql
\i backend/migrations/2026_07_ip_rate_limit.sql
\i backend/migrations/2026_07_tenant_alerts.sql
\i backend/migrations/2026_07_social_projects.sql  -- auto-post social
```

Env vars novos:
- `TRUSTED_PROXIES` — lista de IPs/CIDRs de proxies confiáveis pra XFF. **Recomendado em prod com Cloudflare/nginx**: `TRUSTED_PROXIES=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16`. Sem isso, XFF é ignorado (fail-safe).
- `RATE_LIMIT_DEV_OPEN=1` — em dev, requests de loopback (127.0.0.1) ignoram rate limit inteiro. UX sem fricção pro simulador Franz. **NÃO setar em prod.**
- `SILENT_TENANT_ALERT_EMAIL` — opcional. Se setado, detector envia email quando acha `subscription_expiring_7d` (critical).

Crons novos sugeridos:
- `python -m backend.jobs.detect_silent_tenants` 1x/dia 04:00 BRT.
- `bash /opt/fralib/scripts/cron_social_post.sh` 1x/dia 10:30 BRT (auto-post social).

## 🔒 Segurança / Não-regressão

- `record_event` é fail-safe (try/except com logger.warning — auditoria NUNCA derruba request).
- Rate limit fail-open se Redis+Postgres ambos indisponíveis.
- Detector de tenant silencioso roda com `dry_run=True` por padrão.
- **XFF spoof**: protegido por `TRUSTED_PROXIES` env (fail-safe se não setado).
- Nenhuma alteração em arquivos críticos: `outbound_queue.py`, `whatsapp_listener.py`, `sdr_langgraph/agent.py`.
- Tokens Facebook Ads hardcoded (Bug #7 do audit original) já removidos em PR anterior.
