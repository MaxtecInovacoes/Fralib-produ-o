# FraLib — CLAUDE.md

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
