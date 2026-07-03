# Single Sources of Truth — FraLib

> **Por que este doc existe**: Este projeto já teve 3 "duas verdades" críticas (DV1, DV3, DV4) — lugares onde duas versões do mesmo código rodavam em paralelo e dev perdia tempo consertando a errada. Este doc lista **ONDE** está cada coisa canônica, pra nunca mais criar/atualizar a versão morta.

---

## 🎯 Como usar este doc

**Antes de:**
- Criar arquivo/função nova
- Mover lógica de um lugar pra outro
- Adicionar endpoint, job type, agent, helper
- Dizer "vou refatorar X pra cá"

**Você DEVE:**
1. Procurar neste doc se X já tem "single source"
2. Se sim, **editar X** no caminho listado aqui
3. Se não existir, **adicionar neste doc** ANTES de criar o arquivo novo

**Quando encontrar divergência:**
- Doc diz Y, código tem Y e Z → investigar se Z é duplicação
- Se Z for duplicação: mover pra `_legacy_2026_07/` e atualizar este doc

---

## 📍 Pipeline (Vite/React engine padrão desde Sprint 12.9)

| Fase | Onde mora | Cuidado |
|---|---|---|
| Hunter | `backend/utils/agente1_hunter_v2.py` | Via `HunterProvider` (services/hunter_provider.py) |
| Caio | `backend/agents/caio.py` (506 linhas) | **CANÔNICO** — wrappers NÃO devem duplicar lógica |
| Jina | `backend/agents/jina_research.py` + `backend/utils/jina_intelligence.py` | Único caminho |
| Nicho | `backend/agents/agente_nicho.py` | Único caminho |
| Variação | `backend/agents/agente_variacao.py` | Único caminho |
| **Arquiteto (Fase 8)** | `backend/endpoints/pipeline_orchestrator_service.py:1700-1900` | **ÚNICO. NÃO criar módulo em `services/pipeline_fases/` — foi extraído em 19/junho mas nunca integrado, agora em `_legacy_2026_07/pipeline_fases_extraido/`** |
| Builder (Fase 9) | `backend/services/vite_react_renderer.py` (engine padrão) ou `openui_renderer.py` (alternativa) | Ver `FRALIB_BUILDER_ENGINE` env |
| QA | `backend/agents/html_quality_gate.py` | Único caminho |
| Deploy | `scripts/post-receive` (rodado via git push em master) | Único caminho |
| Franz/SDR | `backend/agents/sdr_langgraph/agent.py` (`iniciar_contato`) | Único entrypoint |

---

## 🤖 SDR/Franz — Validações compartilhadas

| Validação | Onde mora | Usado por |
|---|---|---|
| `_sdr_quality_hold_reason(db, lead_id, tenant_id)` | **`backend/services/sdr_helpers.py`** | worker.py (job queue), cron_endpoints.py (`/despachar-fila-franz`) |
| `evaluate_sdr_output(SdrMessageContext)` | `backend/services/sdr_gateway.py` | worker.py, cron_endpoints.py, leads_crud_sdr.py |
| `_lead_lock_guard(lead_id)` | `backend/agents/sdr_langgraph/lead_lock.py` | worker.py, cron_endpoints.py |
| `has_prior_outbound(conn, lead_id, user_id)` | `backend/services/sdr_gateway.py` | worker.py, cron_endpoints.py |

**REGRA:** Qualquer nova validação que seja usada em mais de um caminho de Franz **DEVE** ir pra `backend/services/sdr_helpers.py` ou `backend/services/sdr_gateway.py`.

---

## 🔍 Lead Supply (Hunter, Caio, Maps, Manual)

| Camada | Onde mora | Função |
|---|---|---|
| **Entry point (compat)** | `backend/services/lead_supply_engine.py` | Re-exporta tudo (mantido por compatibilidade) |
| **Orquestração de jobs** | `backend/services/lead_supply_providers/{hunter,caio,maps,manual}.py` | Função `run_X_job(db, payload, tenant_id)` |
| **Factory/Facade** | `backend/services/lead_providers.py` (`LeadProviderFacade`) | Escolhe provider baseado em config |
| **Trabalho real** | `backend/services/{hunter_provider,maps_provider,manual_provider}.py` | Classes que fazem busca/normalização/deduplicação |

**REGRA:** Lead Supply está em 4 camadas INTENCIONAIS. Cada camada tem papel. **NÃO MESCLAR** — está funcionando. Só mexe se algo quebrar com evidência.

---

## 🗃️ Worker — Tipos de Job

`WORKER_JOB_TYPES` (env var, default em `worker.py:63-68`):

| Job Type | Quem processa | Service dedicado |
|---|---|---|
| `pipeline_lead` | `fralib-worker.service` | NÃO |
| `pipeline_multiplos` | `fralib-worker.service` | NÃO |
| `lead_supply_hunter` | `fralib-worker.service` | NÃO |
| `lead_supply_caio` | `fralib-worker.service` | NÃO |
| `lead_production_tick` | `fralib-worker.service` | NÃO |
| **`franz_outreach`** | **`fralib-franz.service`** | **SIM — dedicado** |

**REGRA:** Não adicionar `franz_outreach` no default do worker geral. Se precisar testar Franz manualmente, defina env `WORKER_JOB_TYPES` incluindo `franz_outreach`.

---

## 🔧 Banco de dados — Migrations

| Sistema | Onde mora | Status |
|---|---|---|
| Alembic | `alembic/versions/*.py` | **CANÔNICO** (24 migrations, 1 raiz) |
| SQL manual | `backend/migrations/*.sql` | Idempotente, rodar manualmente |
| DDL Python runtime | `backend/core/database.py:inicializar_database()` | **DESABILITADO** em server.py (Sprint 14.x). NÃO REMOVER — fallback de emergência |

**REGRA:** Nova migration vai **SEMPRE** em `alembic/versions/`, formato `op.create_table()` (não `DO $$`). Adicionar `down_revision` correto.

---

## ⚙️ Workers systemd (VPS)

| Service | Função | Roda jobs Franz? |
|---|---|---|
| `fralib-api.service` | API FastAPI (server.py) | N/A |
| `fralib-worker.service` | Pipeline + Lead Supply | **NÃO** (default sem franz_outreach) |
| `fralib-worker@.service` | Workers adicionais sob demanda | NÃO |
| `fralib-franz.service` | SDR/Franz dedicado | **SIM** |
| `fralib-wpp-listener.service` | WhatsApp listener | N/A |
| `fralib-hermes.service` | Watchdog | N/A |
| `fralib-meowhats.service` | Bridge Go whatsmeow | N/A (opcional, ainda não instalado) |

**REGRA:** Se for criar novo service, adicionar em `infra/systemd/` E em `infra/systemd/README.md`.

---

## 🚫 LEGACY (não usar mais)

| Item | Onde está | Por que é legacy |
|---|---|---|
| `backend/services/dreamer.py` | Já removido | Substituído por `sdr_langgraph/learning.py` |
| `backend/services/pipeline_fases/` | Movido pra `_legacy_2026_07/pipeline_fases_extraido/` | Nunca foi integrado |
| `backend/agents/langgraph_backup/` | Movido pra `_legacy_2026_07/agents_orfaos/` | Código pré-LangGraph |
| `_legacy_2026_07/` (geral) | Não versionado (no .gitignore) | Backup de 30 dias antes de apagar definitivamente |
| PM2 | `/usr/bin/pm2` na VPS | Migrado pra systemd em 2026-06 |
| `Y/` | Movido pra `_legacy_2026_07/Y_residual_pm2/` | Resíduo de instalação PM2 |

---

## 📋 Como adicionar uma nova "verdade"

1. **Procura neste doc** se já existe single source
2. **Se sim:** edita no caminho listado
3. **Se não:** adiciona entrada neste doc ANTES de criar
4. **Cuidado:** se for parecida com algo que já existe, é duplicação → investigar

## 📋 Como reportar duplicação encontrada

1. Cria task em TaskCreate com prefixo "DV" (ex: "DV6 - encontrar duas verdades em X")
2. Documenta: arquivo:linha de cada versão + quem chama cada uma
3. Decide qual é canônica (a mais usada / mais recente / com mais features)
4. Move a outra pra `_legacy_2026_07/`
5. Atualiza este doc com a single source escolhida
6. Commit + push

---

*Última atualização: 2026-07-03 — auditoria completa + 3 DVs resolvidas*