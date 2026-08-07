# FraLib — CLAUDE.md

## REGRAS ABSOLUTAS DE DEPLOY

1. NUNCA usar SCP, rsync ou editar arquivos direto na VPS
2. SEMPRE: editar local → git add → git commit → git push (deploy automatico)
3. NUNCA deployar codigo nao commitado
4. Se fez alteracao, DEVE commitar antes de encerrar sessao

## Visao Geral do Projeto

FraLib e um SaaS de geracao de landing pages via pipeline de agentes IA.
O pipeline recebe um briefing e produz HTML completo, animado e responsivo.
Modulo paralelo de SDR via WhatsApp (Franz agent loop + meowhats).

## Pipeline de Agentes (ordem de execucao)

Fonte: commit a9030deb (22 junho 2026) - pipeline funcional
Documento: docs/RESTORE_JUNHO22_REFERENCE.md

### Cadeia completa (11 fases)
```
FASE 1  HUNTER           -> Hunter captura leads
FASE 2  CURADORIA/CAIO   -> Qualifica lead (tier, score, paleta)
FASE 3  JINA             -> Pesquisa mercado Jina AI
FASE 4  INTELIGENCIA     -> Analise concorrencia
FASE 5  FOTOS            -> Download fotos
FASE 6  NICHO            -> Analise nicho
FASE 7  VARIACAO         -> Variacao estrutural
FASE 8  ARQUITETO        -> Gera DesignerPRD (secoes, paleta, animacoes)
FASE 9  BUILDER          -> HTML via OpenUI (wandb/openui, porta 7878)
FASE 10 DEPLOY           -> Site em /var/www/fralib/sites/
FASE 11 FRANZ            -> SDR outreach WhatsApp
```

### Agentes
| Fase | Agente | Funcao |
|------|--------|--------|
| 1 | Hunter | Captura leads Google Maps |
| 2 | Caio | Qualifica lead (tier, score, paleta) |
| 3 | Jina | Pesquisa mercado Jina AI |
| 4 | Inteligencia | Analise concorrencia |
| 5 | Fotos | Download fotos Unsplash/Pexels |
| 6 | Nicho | Analise nicho segmento |
| 7 | Variacao | Variacao estrutural site |
| 8 | Arquiteto Mestre | Gera DesignerPRD via LLM |
| 9 | Builder (OpenUI) | Gera HTML completo com contratos SEO/LGPD/motion |
| 10 | Deploy | Publica site |
| 11 | Franz | SDR outreach WhatsApp (FSM + Orchestrator) |

**Orquestrador:** backend/services/pipeline_executors.py (11 fases)
**Estado:** backend/services/pipeline_phases.py (FraLibState 15+ campos)
**Motor HTML:** wandb/openui (Python backend, porta 7878, LiteLLM proxy)

Nota: Theo, Designer PRD, Liam, Liz sao agentes LEGADO. Arquiteto Mestre funde Theo + Designer.


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

**/opt/fralib/openui-wandb/backend/.env:**
```
ANTHROPIC_API_KEY=dh-live-5MI2EvgUoAuoLAnP4jn0
ANTHROPIC_BASE_URL=https://deployflow.com.br/api/public/v1
OPENAI_COMPATIBLE_ENDPOINT=https://deployflow.com.br/api/public/v1
OPENAI_COMPATIBLE_API_KEY=dh-live-5MI2EvgUoAuoLAnP4jn0
PORT=7878
HOST=0.0.0.0
```

## Deploy

- Push: `git push github master` → post-receive hook na VPS
- Nao rebuildar containers sem necessidade — volumes persistem mudancas em /opt/fralib/backend/
- OpenUI: restart `fralib-openui` (systemd) apos mudancas em openui-service/
- Backend: rebuild `fralib-app` + `fralib-worker-1` apos mudancas em backend/

## Logs

- Worker unificado: `docker logs -f fralib-worker-1`
- OpenUI: `journalctl -u fralib-openui -f`
- App (API): `systemctl status fralib-api`

## Arquivos Principais

**Pipeline ativa (VPS /opt/fralib/):**
```
backend/agents/arquiteto_mestre.py      PRD designer + copywriter
backend/agents/builder/agent.py         Builder HTML (single-shot OpenUI)  ← existe na VPS
backend/agents/caio.py                   Qualificacao
backend/agents/franz.py                  Finalizador / SDR (legacy — fallback)
backend/agents/theo.py                   Estrategista
backend/agents/liz.py                    Revisora codigo
backend/agents/designer_prd.py           PRD designer (legado)
backend/agents/design_context.py         Tokens OKLch por nicho
backend/agents/animation_injector.py     Injetor animacoes
backend/agents/open_design_selector.py   Selecao design system
backend/agents/franz/
  ├── __init__.py                       Franz agent package
  ├── franz_tools.py                    Tool definitions + execute_tool() dispatcher
  └── franz_agent_loop.py               Managed agent loop (MCP-like tool calling)
backend/endpoints/pipeline_endpoints.py  Rotas pipeline
backend/endpoints/leads_endpoints.py     CRUD leads
backend/endpoints/cron_endpoints.py      Cron Franz
backend/whatsapp_listener.py             WebSocket meowhats + Franz agent loop
```

**Legado local (nao deployado, manter referencia):**
```
backend/agents/liam.py                  1373 linhas — substituido por builder/
backend/agents/_arquivo/alex.py          ARQUIVADO
backend/agents/_arquivo/liam_motion.py   ARQUIVADO
backend/agents/_arquivo/animation_injector.py  ARQUIVADO (versao antiga)
backend/agents/_arquivo/design_guidelines.py   ARQUIVADO
```

**IMPORTANTE:** `backend/agents/builder/` existe localmente e na VPS. Para editar o Builder, editar localmente e fazer git push.

## Franz Agent Loop (Phase 3.2)

Franz usa MCP-like tool calling para interagir com sistemas externos durante conversas WhatsApp.

**Arquitetura:**
```
mensagem → run_agent_loop() → Claude (tools=FRANZ_TOOLS)
                                          ├─ tool_use → execute_tool() → tool_result → Claude
                                          └─ text → retorna reply para WhatsApp
Max 10 iteracoes. Tool results capped em 4000 chars.
```

**Tools disponiveis (10):**
| Tool | Funcao |
|------|--------|
| `buscar_lead` | Dados completos do lead |
| `consultar_historico` | Todas as interacoes anteriores |
| `consultar_site` | URL do site gerado |
| `marcar_status_lead` | Atualiza status (hot_lead, negociacao, etc) |
| `registrar_interacao` | Registra interacao no banco |
| `enviar_whatsapp` | Envia mensagem WhatsApp (cautela) |
| `agendar_followup` | Agenda follow-up automatico |
| `marcar_deferido` | Marca lead para contato futuro |
| `buscar_leads_similares` | Leads do mesmo segmento |
| `verificar_status_wpp` | Verifica conexao WhatsApp |

**Wiring:** `whatsapp_listener.py` integra Franz agent loop com fallback para `agents.franz` legacy. Variavel `FRANZ_AGENT_LOOP=1` ativa/desativa.

**Commit:** b2de8eb6

## Alertas

- pipeline_endpoints.py tem 1664 linhas — quebrar em modulos
- franz.py tem 1362 linhas — proximo do limite
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
