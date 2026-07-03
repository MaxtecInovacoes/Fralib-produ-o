# FraLib

FraLib é um SaaS que captura negócios locais, gera landing pages estáticas com IA
e aciona um SDR via WhatsApp.

> **Toda a arquitetura, pipeline, contratos, atalhos, caches e plano de ação estão em
> [`AGENTS.md`](AGENTS.md). Este README é apenas um índice de onboarding. Se este
> arquivo e `AGENTS.md` divergirem, `AGENTS.md` vence.**

## Onboarding em 5 passos

1. Ler [`AGENTS.md`](AGENTS.md) inteiro (fonte única de verdade).
2. Ler [`docs/DOCS_INDEX.md`](docs/DOCS_INDEX.md) para o índice de docs operacionais.
3. Rodar `python pipeline.py smoke --dry-run` (diagnóstico sem LLM, deploy ou WhatsApp).
4. Inspecionar [`docs/ONE_TRUTH_CANONICAL_STATE.md`](docs/ONE_TRUTH_CANONICAL_STATE.md) para estado canônico de fila/leads/planos.
5. Inspecionar [`docs/SYSTEM_OPERATIONS_MAP.md`](docs/SYSTEM_OPERATIONS_MAP.md) para o sistema em execução.

## Diagnóstico rápido

```bash
python pipeline.py smoke --dry-run                  # pré-flight (sem LLM/deploy/WhatsApp)
python pipeline.py smoke --dry-run --fix-locks      # idem + reset de locks órfãos
python pipeline.py pre-release-gate                 # gate completo (smoke + secrets + audit + testes)
```

## TL;DR da Pipeline (versão canônica de `AGENTS.md`)

1. Hunter + Keyword Research: captura leads e contexto transacional.
2. Caio: qualifica leads com regras determinísticas.
3. Jina + inteligência de mercado: pesquisa nicho, concorrência e PAA.
4. Inteligência: assets consolidados (concorrência + reviews + SEO).
5. Unsplash + Pexels: seleciona fotos e vídeos.
6. Agente de Nicho: cria `NichoBriefing`.
7. Agente de Variação: define estrutura visual.
8. Arquiteto Mestre: gera `DesignerPRD` via blocos de estrutura e copy.
9. **Builder Renderer (OpenUI — canônico)**: transforma PRD factual + arquétipo visual em HTML final. Vite/React é opt-in Studio Premium via `FRALIB_BUILDER_ENGINE=vite_react`.
10. Quality gate (loop ≤ 3 retries) + Deploy.
11. Franz: SDR WhatsApp em job separado.

## Stack

- Backend: Python, FastAPI, Uvicorn (`server.py`, porta 8000).
- Fonte canônica local: `C:\fralib`; fonte canônica VPS: `/root/fralib`.
- Banco: PostgreSQL `localhost:5433/fralib_db`.
- LLM: Anthropic direto via `backend/agents/llm_direct.py`.
- Gerador de site: **OpenUI** (`backend/services/openui_renderer.py`) por padrão.
- WhatsApp: whatsmeow em `:3001` (externo, fora do ServiceManager).
- Processos: **systemd** (5 serviços: api/worker/franz/wpp-listener/hermes) + ServiceManager.

## Arquivos Chave

- `server.py` — app FastAPI e routers.
- `backend/endpoints/pipeline_orchestrator_service.py` — orquestrador (fonte real da ordem de execução).
- `backend/services/pipeline_phases.py` — enum canônico de 11 fases.
- `backend/services/openui_renderer.py` — gerador canônico de sites (OpenUI).
- `backend/services/openui_contracts.py` — 7 contratos injetados no system prompt do OpenUI.
- `backend/agents/caio.py` — qualificação determinística.
- `backend/agents/agente_nicho.py` — Nicho (LLM Sonnet).
- `backend/agents/agente_variacao.py` — Variação (LLM Haiku).
- `backend/agents/arquiteto_mestre.py` — DesignerPRD (LLM Sonnet).
- `backend/agents/html_quality_gate.py` — quality gate determinístico.
- `backend/core/job_queue.py` — fila Postgres.
- `backend/services/builder_worker.py` — orquestra OpenUI vs Vite/React.
- `scripts/pipeline_smoke.py` — smoke oficial.
- `scripts/verify_frontend_canonical.py` — bloqueia HTML divergente.
- `scripts/check_deploy_contract.py` — bloqueia republicação de frontend antigo.
- `scripts/post-receive` — hook canônico de deploy.

## Operação

Deploy oficial:

```bash
git add .
git commit -m "mensagem"
git push origin master
```

Somente push em `master` dispara publicação. Pushes em branches de trabalho não
republicam a landing.

Regras:

- Nunca editar arquivos direto na VPS.
- Nunca usar SCP/rsync para deploy.
- Nunca rodar pipeline real antes do smoke dry-run passar.
- Não commitar caches, logs, arquivos temporários ou testes ad hoc.
- Ignore pastas antigas fora de `C:\fralib` e `/root/fralib`.
- Multiusuário exige `tenant_id/user_id` em toda query, job, asset e sessão WhatsApp.
- **Mudou algo? Atualizar `AGENTS.md` primeiro.**

## Estado de Estabilização

Esta branch resolve divergência entre local/VPS/docs e prepara o sistema para
auditoria mensurável. Os achados estão em `docs/SYSTEM_AUDIT.md`.
O plano MVP/tasks para resolver os pontos restantes está em `docs/PRD_MVP_ESTABILIZACAO_FRALIB.md`.

## Onde olhar primeiro

Dúvida sobre a pipeline? Abrir [`AGENTS.md`](AGENTS.md) e usar Ctrl+F.
# teste deploy fix 1783090683
