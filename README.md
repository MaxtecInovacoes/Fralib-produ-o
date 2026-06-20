# FraLib

FraLib e um SaaS que captura negocios locais, gera landing pages estaticas com IA e aciona um SDR via WhatsApp.

## Como Rodar Diagnostico

```bash
python pipeline.py smoke --dry-run
```

O smoke dry-run mede preflight, imports, banco, locks, regras do Caio, contrato minimo do PRD e portas locais. Ele nao chama LLM, nao raspa Google Maps, nao faz deploy e nao envia WhatsApp.
Ele tambem valida contexto legado, frontend canonico e contrato do hook de deploy.

Para resetar locks orfaos durante o smoke:

```bash
python pipeline.py smoke --dry-run --fix-locks
```

Gate unico pre-release (falha se qualquer etapa falhar):

```bash
python pipeline.py pre-release-gate
```

## Ambiente Isolado com Docker

O Docker e um trilho paralelo para dev/staging e diagnostico; a VPS continua
publicando pelo fluxo oficial Git -> `master` -> PM2 ate a migracao ser
aprovada.

```bash
docker compose up --build postgres redis app
docker compose run --rm app python pipeline.py smoke --dry-run
docker compose up --build worker bryan-worker
```

O container da aplicacao inclui Python + Node 22 para o Builder Vite/React.
PostgreSQL e Redis rodam em servicos isolados. O Meowhats fica externo por
padrao em `MEOWHATS_URL=http://host.docker.internal:3001`, preservando QR e
sessoes existentes.
Para evitar colisao com PM2/Postgres da VPS, as portas publicadas sao
`127.0.0.1:18000` para app, `15433` para Postgres e `16379` para Redis.
O app do container roda como usuario `fralib`, possui healthcheck em
`/api/version` e usa Redis para rate limit distribuido quando `REDIS_URL` ou
`FRALIB_RATE_LIMIT_STORAGE_URI` estiver configurado.

## Pipeline Atual

1. Hunter + Keyword Research: captura leads e contexto transacional.
2. Caio: qualifica leads com regras deterministicas.
3. Jina + inteligencia de mercado: pesquisa nicho, concorrencia e PAA.
4. Unsplash + Pexels: seleciona fotos e videos.
5. Agente de Nicho: cria `NichoBriefing`.
6. Agente de Variacao: define estrutura visual.
7. Arquiteto Mestre: gera `DesignerPRD` via blocos de estrutura e copy.
8. Skill Renderer: transforma PRD factual + arquétipo visual em HTML final.
9. Quality gate: revisa HTML e solicita repair exato quando necessario.
10. Deploy + health check.
11. Bryan: SDR WhatsApp em job separado.

## Stack

- Backend: Python, FastAPI, Uvicorn.
- Fonte canonica local: `C:\fralib`; fonte canonica VPS: `/root/fralib`.
- Banco: PostgreSQL `localhost:5433/fralib_db`.
- LLM: Claude via `backend/agents/llm_direct.py`.
- HTML: `skill_renderer` por padrao, sem rota fallback de renderer.
- WhatsApp: meowhats em `:3001`.
- Processos: PM2 (`fralib`, `fralib-worker`, `meowhats`, `gosom-scraper`).

## Arquivos Chave

- `server.py`: app FastAPI e routers.
- `backend/endpoints/pipeline_endpoints.py`: orquestrador.
- `backend/agents/caio.py`: qualificacao.
- `backend/agents/keyword_research.py`: keywords + cache PostgreSQL.
- `backend/agents/arquiteto_mestre.py`: PRD final.
- `backend/agents/bloco_estrutura.py`: estrutura/layout.
- `backend/agents/bloco_copy.py`: copy por secao.
- `backend/agents/prompts_arquiteto.py`: prompts/helpers.
- `backend/agents/skill_based_renderer.py`: renderer HTML principal.
- `backend/agents/liam_renderer.py`: wrapper do renderer principal.
- `backend/core/database.py`: DB e locks.
- `scripts/pipeline_smoke.py`: smoke oficial.
- `scripts/verify_frontend_canonical.py`: bloqueia HTML gerado divergente dos partials.
- `scripts/check_deploy_contract.py`: bloqueia republicacao de frontend antigo.

## Operacao

Deploy oficial:

```bash
git add .
git commit -m "mensagem"
git push origin <branch>
```

Somente push em `master` dispara publicacao. Pushes em branches de trabalho nao
podem republicar a landing.

Regras:

- Nunca editar arquivos direto na VPS.
- Nunca usar SCP/rsync para deploy.
- Nunca rodar pipeline real antes do smoke dry-run passar.
- Nao commitar caches, logs, arquivos temporarios ou testes ad hoc.
- Ignore pastas antigas fora de `C:\fralib` e `/root/fralib`.
- Multiusuario exige `tenant_id/user_id` em toda query, job, asset e sessao WhatsApp.

## Estado de Estabilizacao

Esta branch resolve divergencia entre local/VPS/docs e prepara o sistema para auditoria mensuravel. Os achados estao em `docs/SYSTEM_AUDIT.md`.
O plano MVP/tasks para resolver os pontos restantes esta em `docs/PRD_MVP_ESTABILIZACAO_FRALIB.md`.
