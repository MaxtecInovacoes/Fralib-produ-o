# FraLib — Índice de Entrada

> **Fonte única de verdade**: [`AGENTS.md`](AGENTS.md).
> Toda a arquitetura, pipeline, contratos, atalhos, caches, testes e plano de ação estão lá.
> Se `CLAUDE.md` e `AGENTS.md` divergirem, **`AGENTS.md` vence**.

## TL;DR
- **Pipeline canônica: 11 fases** (Hunter → Caio → Jina → Nicho → Variação → Arquiteto → **OpenUI** → QA → Deploy → Franz).
- **Gerador de site: OpenUI** (`backend/services/openui_renderer.py`) — é o ÚNICO gerador. Não use Vite/React ou outros.
- **Sub-agentes por estética (Sprint 6)**: 6 templates Awwwards (BOLD/EDITORIAL/MINIMAL/KINETIC/SCROLL/IMMERSIVE_3D) + router opt-in via `FRALIB_USE_SUB_AGENTS=1`.
- **Tracing dos 4 agentes (Sprint 5)**: opt-in via `FRALIB_TRACING=1`. 4 endpoints SuperAdmin JSON.
- **Runtime: PM2** (processo `fralib` na porta 8000) — `whatsmeow` externo na 3001.
- **Deploy**: `git push origin master` → `scripts/post-receive` → publish.
- **Diagnóstico**: `python pipeline.py smoke --dry-run`.
- **Regressão**: 130/130 testes verdes (12 suites: v1.0/v1.1/v1.2/v1.3/v1.4/v1.5/v1.6/v1.8/v1.9/v1.10/v1.11/v1.12).
- **Sprints concluídos (SDK)**: 13/13 sinais ativos — Sprint 0+1+2+3A+3B+3C+5+6+7+8+9.

## Regra de ouro
A pipeline canônica é o **ÚNICO** caminho para gerar sites.
Mudou a pipeline, código, config ou docs? Atualizar **`AGENTS.md` primeiro** e propagar.

## Mapa de docs (verdade única)

| Doc | Função |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Fonte canônica — arquitetura, pipeline, sprints 0-9, ROI |
| [`docs/ONE_TRUTH_CANONICAL_STATE.md`](docs/ONE_TRUTH_CANONICAL_STATE.md) | Estado canônico de filas, locks, billing |
| [`docs/SYSTEM_OPERATIONS_MAP.md`](docs/SYSTEM_OPERATIONS_MAP.md) | Mapa de runtime, request→site flow |
| [`docs/ONBOARDING_FOR_AI_AGENTS.md`](docs/ONBOARDING_FOR_AI_AGENTS.md) | Onboarding de novos agentes IA |
| [`docs/ROLLOUT_SPRINT_5.md`](docs/ROLLOUT_SPRINT_5.md) | Tracing dos 4 agentes |
| [`docs/ROLLOUT_SPRINT_6.md`](docs/ROLLOUT_SPRINT_6.md) | Sub-agentes por estética |
| [`docs/ROADMAP_SPRINTS_5_6_7_8_9.md`](docs/ROADMAP_SPRINTS_5_6_7_8_9.md) | Roadmap unificado dos 5 sprints SDK |

## Como ativar features novas (VPS)

```bash
# Sprint 5 — Tracing
sed -i "s/FRALIB_TRACING: '0'/FRALIB_TRACING: '1'/" ecosystem.config.js && pm2 restart fralib

# Sprint 6 — Sub-agentes por estética
sed -i "s/FRALIB_USE_SUB_AGENTS: '0'/FRALIB_USE_SUB_AGENTS: '1'/" ecosystem.config.js && pm2 restart fralib

# Sprint 7 — RAG Templates
sed -i "s/FRALIB_USE_TEMPLATE_RAG: '0'/FRALIB_USE_TEMPLATE_RAG: '1'/" ecosystem.config.js && pm2 restart fralib

# Sprint 8 — Auto-melhoria
sed -i "s/FRALIB_AUTO_IMPROVE: '0'/FRALIB_AUTO_IMPROVE: '1'/" ecosystem.config.js && pm2 restart fralib
```

## O que ganhamos (Sprints 5-9)

| Métrica | Antes | Depois |
|---|---|---|
| Latência média render | 10-30s (LLM) | **5ms** (template) |
| Custo por site | $0.003 | **$0** |
| Debug time | 30min | **2min** |
| Variedade visual | 1 genérico | **6 Awwwards** |
| Sinais SDK | 4/13 | **13/13** |
| Cobertura testes | 76 | **130** |

## Status atual

- ✅ **130/130 testes verdes** (12 suites anti-regressão)
- ✅ **21 checks** no pre-commit hook (proteção de decisões críticas)
- ✅ **5 docs novos** de rollout/roadmap
- ✅ **VPS rodando** com `FRALIB_TRACING=1` ativo
- ⏳ Sub-agentes, RAG, auto-melhoria: implementados, aguardando ativação por tenant