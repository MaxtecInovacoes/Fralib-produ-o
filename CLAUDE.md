# FraLib — CLAUDE.md

## REGRAS ABSOLUTAS DE DEPLOY

1. NUNCA usar SCP, rsync ou editar arquivos direto na VPS
2. SEMPRE: editar local → git add → git commit → git push (deploy automatico)
3. NUNCA deployar codigo nao commitado
4. Se fez alteracao, DEVE commitar antes de encerrar sessao

## Visao Geral do Projeto

FraLib e um SaaS de geracao de landing pages via pipeline de agentes IA.
O pipeline recebe um briefing e produz HTML completo, animado e responsivo.
Modulo paralelo de SDR via WhatsApp (Franz + meowhats).

## Pipeline de Agentes (ordem de execucao)

Fonte autoritativa: PLAYBOOK_PIPELINE_VALIDADA.md na VPS (/opt/fralib/docs/)

### Cadeia completa (8 estagios)
```
[1] BANCO       Carrega lead direto do Postgres
[2] HUNTER      Valida lead_data
[3] CAIO        Qualificacao (tier=MORNO/STANDARD/PREMIUM, score 0-100)
[4] ARQUITETO   PRD com secoes, paleta OKLch, animacoes (~35s via LLM)
[5] BUILDER     HTML via OpenUI chunked (4 chunks LLM, ~200s)
[6] QA v2       Vision QA score 7.9/10 PASSED (~111s)
[7] DEPLOY      Site salvo em /var/www/fralib/sites/...
[8] FRANZ       Lead marcado para outreach WhatsApp
```

### Agentes
| # | Agente | Funcao | max_tokens |
|---|--------|--------|------------|
| 1 | Theo | Estrategista / PRD | 6000 (PRD), 4000 (briefing) |
| 2 | Designer PRD | Arquiteto visual | 8000 |
| 3 | Arquiteto Mestre | Funde Theo + Designer em PRD unico | 8000 |
| 4 | Builder (OpenUI) | Gerador HTML chunked | 64000 total (4x 18000) |
| 5 | Liz | Revisora de codigo | 4000 / 8000 |
| 6 | Caio | Otimizador | 2000 |
| 7 | Franz | Finalizador / SDR WhatsApp | 4000 |

Nota: Alex (Integrador) arquivado em backend/agents/_arquivo/.
Liam (gerador HTML antigo) removido — substituido por Builder OpenUI chunked.

## Infraestrutura (VPS Nova)

### Acesso
```
SSH:      ssh -i ~/.ssh/id_ed25519 root@100.124.56.36 (via Tailscale)
Projeto:  /opt/fralib/
OpenUI:   /root/fralib/openui-service/ (servico systemd)
Dominio:  https://app.seunegociofralib.site
```

### Containers Docker
| Container | Funcao | Porta | Status |
|-----------|--------|-------|--------|
| fralib-app-1 | API FastAPI | 8001→8000 | healthy |
| fralib-worker-1 | Worker unificado (pipeline + supply + Franz) | - | running |
| fralib-postgres-1 | PostgreSQL | 15434→5432 | healthy |
| fralib-redis-1 | Cache | 16379→6379 | healthy |
| fralib-openui | Node.js HTML generation (systemd) | 3333 | active |

**Worker unificado:** `WORKER_JOB_TYPES=pipeline_lead,pipeline_multiplos,pipeline_main,lead_production_tick,lead_supply_caio,lead_supply_hunter,franz_outreach` (env var no docker-compose.prod.yml). 3 workers antigos consolidados em 1 (commit f47bd586).

### Variaveis de ambiente
**/opt/fralib/.env:**
```
DATABASE_URL=postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db
ANTHROPIC_API_KEY=dh-live-5MI2EvgUoAuoLAnP4jn0
ANTHROPIC_BASE_URL=https://deployflow.com.br/api/public/v1
LLM_BASE_URL=https://deployflow.com.br/api/public/v1
DEPLOYFLOW_API_KEY=dh-live-5MI2EvgUoAuoLAnP4jn0
DEPLOYFLOW_BASE_URL=https://deployflow.com.br/api/public/v1
FRALIB_PUBLIC_URL=https://app.seunegociofralib.site
FRALIB_SKIP_HTML_QUALITY_GATE=0
```

**/root/fralib/openui-service/.env:**
```
ANTHROPIC_API_KEY=dh-live-5MI2EvgUoAuoLAnP4jn0
ANTHROPIC_BASE_URL=https://deployflow.com.br/api/public/v1
MODEL=claude-sonnet-4-6
MAX_TOKENS=64000
PORT=3333
NODE_ENV=production
```

## Deploy

- Push: `git push origin master` → post-receive hook na VPS
- Nao rebuildar containers sem necessidade — volumes persistem mudancas em /opt/fralib/backend/
- OpenUI: restart `fralib-openui` (systemd) apos mudancas em openui-service/
- Backend: rebuild `fralib-app` + `fralib-worker-1` apos mudancas em backend/

## Logs

- Worker unificado: `docker logs -f fralib-worker-1`
- OpenUI: `journalctl -u fralib-openui -f`
- App: `docker logs -f fralib-app-1`

## Arquivos Principais

**Pipeline ativa (VPS /opt/fralib/):**
```
backend/agents/arquiteto_mestre.py      PRD designer + copywriter
backend/agents/builder/agent.py         Builder HTML (chunked OpenUI)  ← existe na VPS
backend/agents/caio.py                   Qualificacao
backend/agents/bryan.py                  Finalizador / SDR
backend/agents/theo.py                   Estrategista
backend/agents/liz.py                    Revisora codigo
backend/agents/designer_prd.py           PRD designer (legado)
backend/agents/design_context.py         Tokens OKLch por nicho
backend/agents/animation_injector.py     Injetor animacoes
backend/agents/open_design_selector.py   Selecao design system
backend/endpoints/pipeline_endpoints.py  Rotas pipeline
backend/endpoints/leads_endpoints.py     CRUD leads
backend/endpoints/cron_endpoints.py      Cron Bryan
backend/whatsapp_listener.py             WebSocket meowhats
```

**Legado local (nao deployado, manter referencia):**
```
backend/agents/liam.py                  1373 linhas — substituido por builder/
backend/agents/_arquivo/alex.py          ARQUIVADO
backend/agents/_arquivo/liam_motion.py   ARQUIVADO
backend/agents/_arquivo/animation_injector.py  ARQUIVADO (versao antiga)
backend/agents/_arquivo/design_guidelines.py   ARQUIVADO
```

**IMPORTANTE:** `backend/agents/builder/` NAO existe no disco local ainda — existe apenas na VPS (/opt/fralib/backend/agents/builder/). Para editar o Builder, fazer via VPS ou pull do repo.

## Alertas

- pipeline_endpoints.py tem 1664 linhas — quebrar em modulos
- bryan.py tem 1362 linhas — proximo do limite
- websocket.go:166 (meowhats): filtro tenantId sem autorizacao — registrar como divida

## WhatsApp LID Protocol (whatsmeow)

O WhatsApp Web/whatsmeow usa o protocolo **LID** (Linked ID) internamente para multi-device. Mensagens chegam com JIDs no formato `234754607685703@lid`.

**Como funciona:**
- Cada numero tem um LID unico atribuido pelo WhatsApp
- A tabela `whatsmeow_lid_map` (DB whatsmeow, porta 5433) mapeia: `lid` → `pn` (phone number)
- Exemplo: LID `234754607685703` → PN `554185134105`

**Padrao no codigo:**
- Sempre verificar se JID contem `@lid` antes de processar
- Se `@lid`: resolver via `_resolver_lid()` que consulta `whatsmeow_lid_map`
- Se `@s.whatsapp.net`: extrair numero direto
- Para ENVIAR mensagens: pode usar tanto LID quanto telefone — o meowhats resolve via `IsOnWhatsApp()`

**DB whatsmeow:**
- Host: localhost:5433
- DB: whatsmeow
- User: postgres / fralib2024
- Tabelas: `whatsmeow_lid_map` (lid→pn), `tenant_device` (tenant_id, jid)

**API meowhats (porta 3001):**
- Auth: Header `X-API-Key: 1763kovQ@`
- Enviar msg: `POST /api/sessions/{tenantId}/send` — body: `{jid, type, text}`
- Status: `GET /api/sessions/{tenantId}/status`
- Conectar: `POST /api/sessions/{tenantId}/connect`
- WebSocket: `ws://localhost:3001/ws`

**WebSocket events:**
- `message` — msg recebida (Baileys format)
- `connection.update` — status: connected, qr, disconnected, reconnecting, timeout

**Importante:**
- O LID NAO e o telefone — nao tentar buscar lead por LID direto
- Sempre resolver LID → telefone antes de buscar no banco de leads
- O campo `wpp_jid` nos leads guarda o LID pra fallback de busca
- Sessoes persistem no PostgreSQL — restart nao perde login
- Celular NAO precisa ficar ligado (multi-device protocol)
