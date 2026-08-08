# FraLib — Sistema de Geração de Sites

Plataforma SaaS multi-tenant para mineração de leads locais, geração de sites únicos via agentes LLM e outreach via WhatsApp.

## Arquitetura

```
backend/agents/          ← Agentes canônicos (cada um em sua pasta)
  hunter/                Fase 1: mineração de leads (PlacesAPI + Playwright)
  caio/                  Fase 2: qualificação determinística (score/tier)
  jina/                  Fase 3: pesquisa de mercado Jina AI
  unsplash/              Fase 4: download de fotos do nicho
  arquiteto/             Fase 5: DesignerPRD (estrutura, cores, seções)
  builder/               Fase 6: geração HTML + Quality Gate (OpenUI service :7878)
  franz/                 Fase 11: SDR FSM via WhatsApp
  manager/               Orquestrador FSM: Hunter → Caio → Jina → Unsplash → Arquiteto → Builder → Deploy → Franz

backend/services/        ← Infra runtime (lead_supply_engine, credits_manager, ia_manager)
backend/core/            ← Core infra (auth, database, job_queue, rate_limiter)
backend/endpoints/       ← Routers HTTP FastAPI (pipeline, crm, auth, etc)

frontend/                ← Dashboard, admin, landing, visual site editor
server.js                ← Node.js Express server (porta 3000 — preview & static routing)
server.py                ← Entry point FastAPI (porta 8000/8001 na VPS)
worker.py                ← Daemon que consome fila Postgres (skip locked)
```

## Execução da Pipeline (VPS vs Local)

- **Servidor VPS (Produção)**: Executa a pipeline completa de ponta a ponta com Playwright para scraping do Google Maps, serviço OpenUI em container Docker (:7878), banco de dados PostgreSQL e envio via WhatsApp bot (Franz).
- **Ambiente Local / Preview**: Serve a interface do Dashboard e Admin, permitindo testes de rotas, edição de site, simuladores e diagnósticos.
- **Diagnóstico com IA / Claude**: Em caso de falha em qualquer etapa da pipeline no Dashboard, um modal de diagnóstico é exibido com a causa raiz, ação recomendada e botão de 1 clique **"📋 Copiar Diagnóstico para o Claude"**, que gera um relatório formatado pronto para colagem no AI Studio / Claude.

## Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Pydantic
- **Servidor Web Preview**: Node.js, Express (Porta 3000)
- **Banco**: PostgreSQL (com filas via `SELECT FOR UPDATE SKIP LOCKED`)
- **LLM**: Claude (Sonnet primário, Opus em cascata), LiteLLM proxy
- **Frontend**: HTML5, JS Vanilla, CSS Tokens, Chart.js
- **Runtime VPS**: Docker Compose (worker, Postgres, Redis) + systemd (fralib-api porta 8001, OpenUI porta 7878) + PM2
- **Deploy**: `git push origin master` → hook `/root/repos/fralib.git/hooks/post-receive` → rsync → Docker restart + PM2 reload
- **Bind mount**: `/opt/fralib/` (host) → `/app/` (container worker)
- **Observabilidade**: Observability Traces / Spans + Pipeline Error Log

## Setup local

```bash
cp .env.example .env

# Iniciar servidor frontend / mock
npm install
npm run dev
```

## Padrões do projeto

- Cada agente em sua pasta com `agent.py`
- Sem renderer alternativo: Builder OpenUI nativo é o único caminho
- Sem LangGraph: orquestrador usa FSM pura em Python (`backend/agents/manager/agent.py`)

