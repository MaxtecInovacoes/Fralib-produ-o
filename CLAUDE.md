# FraLib — CLAUDE.md

## REGRAS ABSOLUTAS DE DEPLOY

1. NUNCA usar SCP, rsync ou editar arquivos direto na VPS
2. SEMPRE: editar local → git add → git commit → git push (deploy automatico)
3. NUNCA deployar codigo nao commitado
4. Se fez alteracao, DEVE commitar antes de encerrar sessao

## Visao Geral do Projeto

FraLib e um SaaS de geracao de landing pages via pipeline de agentes IA.
O pipeline recebe um briefing e produz HTML completo, animado e responsivo.
Modulo paralelo de SDR via WhatsApp (Bryan + meowhats).

## Pipeline de Agentes (ordem de execucao)

1. Theo — Estrategista / PRD
   max_tokens: 6000 (PRD), 4000 (briefing)

2. Designer PRD — Arquiteto visual
   max_tokens: 8000

3. Liam — Gerador de HTML
   max_tokens: 8000 por bloco

4. Liz — Revisora de codigo
   max_tokens: 4000 / 8000

5. Caio — Otimizador
   max_tokens: 2000

6. Bryan — Finalizador / SDR
   max_tokens: 4000

Nota: Alex (Integrador) foi arquivado em backend/agents/_arquivo/.
Permanece referenciado em CLAUDE.md historico mas nao esta no fluxo ativo.

## Arquivos Principais (linhas em 2026-05-13)

backend/agents/liam.py            1373  Gerador HTML principal
backend/agents/theo.py             814  Estrategista / PRD
backend/agents/liz.py              564  Revisora de codigo
backend/agents/caio.py             275  Otimizador
backend/agents/bryan.py           1362  Finalizador / SDR
backend/agents/designer_prd.py     566  Arquiteto visual
backend/endpoints/pipeline_endpoints.py  1664  Rotas do pipeline
backend/endpoints/leads_endpoints.py      809  CRUD de leads
backend/endpoints/cron_endpoints.py       353  Cron de envio Bryan
backend/whatsapp_listener.py              481  WebSocket meowhats + gate de envio
backend/agents/_arquivo/alex.py    157  ARQUIVADO

## Infraestrutura

VPS: 187.77.37.72 (root)
Processos PM2:
  0  fralib            (backend FastAPI)
  1  claude-mem
  2  meowhats          (servico Go, /opt/whatsmeow_, porta 3001)
  4  fralib-worker
  5  fralib-suporte
Runtime backend: Python 3.13 + FastAPI
Banco: PostgreSQL (porta 5433)
  - fralib_db: dados da aplicacao
  - whatsmeow: sessoes do meowhats + tabela tenant_device

Repos GitHub:
  - meowhats: https://github.com/higorklein47-hub/whatsmeow_

## Estado do Sistema (ultima atualizacao: 2026-05-13)

Correcoes recentes:
- meowhats multi-tenant CORRIGIDO: tabela tenant_device(tenant_id, jid)
  isola devices por tenant; antes todos compartilhavam GetAllDevices()[0]
  (vazamento entre contas). Migration aplicada e session.go reescrito.
  Commit local na VPS: 39777dd .
- whatsapp_listener: cache _TENANT_STATUS por connection.update; helper
  publico is_tenant_connected(tenant_id) usado em cron/leads/pipeline antes
  de cada POST /send para evitar envios em sessao quebrada.
- Status que o meowhats emite: connected, pairing, rejected, logged_out,
  disconnected, reconnecting, qr, timeout. Apenas "connected" libera envio.

## Alertas

- pipeline_endpoints.py tem 1664 linhas — quebrar em modulos (rotas vs
  pipeline_runner vs validacao). Acima do limite 800.
- bryan.py tem 1362 linhas e liam.py 1373 — proximos do limite, considerar
  extracao de skills/prompts para arquivos separados.
- websocket.go:166 (meowhats): filtro tenantId no WS vem da query string
  sem autorizacao. Aceitavel hoje porque API key e backend-only, mas
  registrar como divida.

## WhatsApp LID Protocol (whatsmeow)

O WhatsApp Web/whatsmeow usa o protocolo **LID** (Linked ID) internamente para multi-device. Mensagens chegam com JIDs no formato `234754607685703@lid` ao invés do antigo `telefone@s.whatsapp.net`.

**Como funciona:**
- Cada número tem um LID único atribuído pelo WhatsApp (multi-device)
- A tabela `whatsmeow_lid_map` (DB whatsmeow, porta 5433) mapeia: `lid` → `pn` (phone number)
- Exemplo: LID `234754607685703` → PN `554185134105`

**Padrão no código:**
- Sempre verificar se JID contém `@lid` antes de processar
- Se `@lid`: resolver via `_resolver_lid()` que consulta `whatsmeow_lid_map`
- Se `@s.whatsapp.net`: extrair número direto (formato antigo, ainda funciona pra envio)
- Para ENVIAR mensagens: pode usar tanto o LID (`234754607685703@lid`) quanto o telefone (`5541985134105@s.whatsapp.net`) — o meowhats resolve via `IsOnWhatsApp()`

**DB whatsmeow:**
- Host: localhost:5433
- DB: whatsmeow
- User: postgres / fralib2024
- Tabela `whatsmeow_lid_map`: lid (PK) | pn (unique)
- Tabela `tenant_device`: tenant_id | jid

**API meowhats (porta 3001):**
- Auth: Header `X-API-Key: 1763kovQ@`
- Enviar msg: `POST /api/sessions/{tenantId}/send` — body: `{jid, type, text}`
- Typing: `POST /api/sessions/{tenantId}/presence` — body: `{jid, type: "composing"}`
- Status: `GET /api/sessions/{tenantId}/status`
- Conectar: `POST /api/sessions/{tenantId}/connect`
- Desconectar: `POST /api/sessions/{tenantId}/disconnect`
- Logout (apaga creds): `POST /api/sessions/{tenantId}/logout`
- WebSocket: `ws://localhost:3001/ws` (header X-API-Key, query ?tenantId= opcional)

**WebSocket events:**
- `message` — msg recebida (Baileys format): data.message.key.remoteJid, data.message.message.conversation
- `connection.update` — status: connected, qr, disconnected, reconnecting, timeout
- Server pinga a cada 30s, ReadDeadline 90s — client DEVE responder pong ou enviar frames

**Importante:**
- O LID NÃO é o telefone — não tentar buscar lead por LID direto
- Sempre resolver LID → telefone antes de buscar no banco de leads
- O campo `wpp_jid` nos leads guarda o LID pra fallback de busca
- JID formato: `{DDI}{DDD}{numero}@s.whatsapp.net` (sem +, sem espaços)
- Sessões persistem no PostgreSQL — restart não perde login
- Celular NÃO precisa ficar ligado (multi-device protocol)
