# FraLib — Índice de Entrada

> **Fonte única de verdade**: [`AGENTS.md`](AGENTS.md).
> Toda a arquitetura, pipeline, contratos, atalhos, caches, testes e plano de ação estão lá.
> Se `CLAUDE.md` e `AGENTS.md` divergirem, **`AGENTS.md` vence**.
>
> **Pipeline atual**: Vite/React como engine padrão (Sprint 12.9+).
> OpenUI virou apenas fallback. 26 segmentos cobertos. Briefing real
> injetado no caroço. Post-process contra tela-preta.
> Em produção, publicação fora de `vite_react` falha fechado com
> `FRALIB_STRICT_CANONICAL_PUBLISH=1` ou `FRALIB_ENV=prod`.

## TL;DR
- **Pipeline canônica: 11 fases** (Hunter → Caio → Jina → Nicho → Variação → Arquiteto → **Vite/React** → QA → Deploy → Franz).
- **Gerador de site: Vite/React** (`backend/services/vite_react_renderer.py`) — engine PADRÃO desde Sprint 12.9.
- **Política LLM do Vite**: `FRALIB_VITE_LLM_POLICY=copy_only` por padrão. O LLM retorna JSON de conteúdo; o TSX é gerado pelo Studio/FraLib.
- **Fallback**: OpenUI (`backend/services/openui_renderer.py`) — só roda se Vite/React falhar.
- **26 segmentos** cobertos no studio fallback (barbearia, academia, restaurante, clinica, etc).
- **7 contratos canônicos** injetados no caroço: SEO, Design, Motion, A11y, Factual, LGPD, Deploy.
- **Briefing real** do lead: nome, segmento, cidade, telefone, fotos, SEO, services, horários.
- **Cross-contamination guard**: barbearia NUNCA menciona musculacao, academia NUNCA menciona corte.
- **Tracing** (Sprint 5) e **Sub-agentes por estética** (Sprint 6) continuam ativos.
- **Deploy**: `git push origin master` → `scripts/post-receive` → publish.
- **Diagnóstico**: `python pipeline.py smoke --dry-run`.
- **Regressão**: 12+ suites anti-regressão (v1.0 → v1.14).
- **Sprints concluídos (SDK)**: 13/13 sinais ativos — Sprints 0-9, 11, 12.

## Regra de ouro
A pipeline canônica é o **ÚNICO** caminho para gerar sites.
Mudou a pipeline, código, config ou docs? Atualizar **`AGENTS.md` primeiro** e propagar.

## Mapa de docs (verdade única)

| Doc | Função |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Fonte canônica — arquitetura, pipeline, sprints 0-12, ROI |
| `AGENTS.md` seção 22 | Sprint 11-12: Migração Vite/React, 26 segmentos, caroço rico |
| `AGENTS.md` seção 21 | Sprints 5-9 SDK: tracing, sub-agentes, RAG, auto-melhoria |
| `AGENTS.md` seção 7 | Os 46 patches canônicos (OpenUI path) |
| [`docs/ONE_TRUTH_CANONICAL_STATE.md`](docs/ONE_TRUTH_CANONICAL_STATE.md) | Estado canônico de filas, locks, billing |
| [`docs/SYSTEM_OPERATIONS_MAP.md`](docs/SYSTEM_OPERATIONS_MAP.md) | Mapa de runtime, request→site flow |
| [`docs/ONBOARDING_FOR_AI_AGENTS.md`](docs/ONBOARDING_FOR_AI_AGENTS.md) | Onboarding de novos agentes IA |
| [`docs/ROLLOUT_SPRINT_5.md`](docs/ROLLOUT_SPRINT_5.md) | Tracing dos 4 agentes |
| [`docs/ROLLOUT_SPRINT_6.md`](docs/ROLLOUT_SPRINT_6.md) | Sub-agentes por estética |
| [`docs/VITE_REACT_DEPLOY.md`](docs/VITE_REACT_DEPLOY.md) | Como Vite/React virou engine padrão e policy copy-only |

## Como ativar features novas (VPS)

```bash
# Sprint 12.9 - Vite/React (default desde 2026-06-25)
echo "FRALIB_BUILDER_ENGINE=vite_react" >> ecosystem.config.js && pm2 restart fralib

# Sprint 14 - reduzir custo/token do Vite
# default: copy_only (LLM JSON curto + TSX determinístico)
# alternativas: none (zero LLM) ou full_code (legado, LLM gera TSX completo)
echo "FRALIB_VITE_LLM_POLICY=copy_only" >> ecosystem.config.js && pm2 restart fralib

# Sprint 5 — Tracing
sed -i "s/FRALIB_TRACING: '0'/FRALIB_TRACING: '1'/" ecosystem.config.js && pm2 restart fralib

# Sprint 6 — Sub-agentes por estética
sed -i "s/FRALIB_USE_SUB_AGENTS: '0'/FRALIB_USE_SUB_AGENTS: '1'/" ecosystem.config.js && pm2 restart fralib

# Sprint 7 — RAG Templates
sed -i "s/FRALIB_USE_TEMPLATE_RAG: '0'/FRALIB_USE_TEMPLATE_RAG: '1'/" ecosystem.config.js && pm2 restart fralib

# Sprint 8 — Auto-melhoria
sed -i "s/FRALIB_AUTO_IMPROVE: '0'/FRALIB_AUTO_IMPROVE: '1'/" ecosystem.config.js && pm2 restart fralib
```

## O que ganhamos (Sprints 5-12)

| Métrica | Antes (Sprint 4) | Depois (Sprint 12.19) |
|---|---|---|
| Engine padrão | OpenUI HTML estático | **Vite/React** (componentes) |
| Latência média render | 10-30s (LLM) | **5-30s** (LLM cascata) ou **5ms** (studio fallback) |
| Custo por site | $0.003 | **$0** (`none`) ou JSON curto (`copy_only`) |
| Debug time | 30min | **2min** |
| Variedade visual | 1 genérico | **26 segmentos + 6 Awwwards** |
| Sinais SDK | 4/13 | **13/13** |
| Cobertura testes | 76 | **130+** (12+ suites) |
| Tela preta no site | comum (sem React) | **impossível** (post-process {var}) |
| Lead name injetado | ❌ | ✅ via `_business_context` |

## Status atual

- ✅ **Site v15h deployado e FUNCIONANDO** (`seunegociofralib.site/sites/2/barbearia-fio-nobre-v15h/`)
- ✅ **130+ testes verdes** (12+ suites anti-regressão)
- ✅ **21+ checks** no pre-commit hook
- ✅ **VPS rodando** com `FRALIB_BUILDER_ENGINE=vite_react`
- ✅ **Sprint 12.19** commita post-process que elimina tela-preta
- ✅ **Sprint 12.20** remove contaminação `matricula/treino` do BookingModal em nutricionista
- ✅ **Sprint 12.20** garante Hero/Galeria com fotos reais quando o LLM entrega Vite sem imagens
- ✅ **Sprint 12.20** ajusta guard: `musculação` é permitido em nutrição esportiva, `matrícula` continua bloqueado
- ✅ **Sprint 14** ativa `copy_only`: LLM deixa de gerar TSX por padrão e só preenche JSON de slots
- ⏳ Sub-agentes, RAG, auto-melhoria: implementados, aguardando ativação por tenant

## Tags v1.14.x (Sprint 12.19)

| Tag | Descrição |
|---|---|
| `v1.14.0-baseline` | Migração Vite/React engine padrão |
| `v1.14.1-baseline` | Wire caroço rico no LLM dispatcher |
| `v1.14.2-baseline` | 26 segmentos + clean bundle + deploy |
| `v1.14.3-baseline` | Lead name injection (Fio Nobre) |
| `v1.14.4-baseline` | Post-process {var} placeholders |

Todas em `2026-06-25`. Pronto para roll-forward.
