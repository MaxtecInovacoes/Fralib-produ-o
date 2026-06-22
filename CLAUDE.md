# FraLib — Índice de Entrada

> **Fonte única de verdade**: [`AGENTS.md`](AGENTS.md). Toda a arquitetura, pipeline,
> contratos, atalhos, caches, testes e plano de ação estão lá. Se este `CLAUDE.md`
> e `AGENTS.md` divergirem, **`AGENTS.md` vence**.

## TL;DR
- Pipeline: 11 fases canônicas (Hunter → Caio → Jina → Nicho → Variação → Arquiteto → **OpenUI** → QA → Deploy → Franz).
- Gerador de site: **OpenUI** (`backend/services/openui_renderer.py`) — Vite/React é opt-in Studio Premium.
- Runtime: **systemd** (5 serviços) com ServiceManager; PM2 é legado.
- Deploy: `git push origin master` → `scripts/post-receive` → publish.
- Diagnóstico: `python pipeline.py smoke --dry-run`.

## Diagnóstico rápido
```bash
python pipeline.py smoke --dry-run
python pipeline.py pre-release-gate
```

## Leia primeiro
1. [`AGENTS.md`](AGENTS.md) — fonte única de verdade
2. [`docs/DOCS_INDEX.md`](docs/DOCS_INDEX.md) — índice de docs operacionais
3. [`docs/ONE_TRUTH_CANONICAL_STATE.md`](docs/ONE_TRUTH_CANONICAL_STATE.md) — estado canônico de fila/leads/planos
4. [`docs/SYSTEM_OPERATIONS_MAP.md`](docs/SYSTEM_OPERATIONS_MAP.md) — mapa do sistema em execução

## Regra de ouro
Mudou a pipeline, código, config ou docs? Atualizar **`AGENTS.md` primeiro** e propagar.
