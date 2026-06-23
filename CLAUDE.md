# FraLib — Índice de Entrada

> **Fonte única de verdade**: [`AGENTS.md`](AGENTS.md).
> Toda a arquitetura, pipeline, contratos, atalhos, caches, testes e plano de ação estão lá.
> Se `CLAUDE.md` e `AGENTS.md` divergirem, **`AGENTS.md` vence**.

## TL;DR
- **Pipeline canônica: 11 fases** (Hunter → Caio → Jina → Nicho → Variação → Arquiteto → **OpenUI** → QA → Deploy → Franz).
- **Gerador de site: OpenUI** (`backend/services/openui_renderer.py`) — é o ÚNICO gerador. Não use Vite/React ou outros.
- **Runtime: systemd** (5 serviços) com ServiceManager; PM2 é legado.
- **Deploy**: `git push origin master` → `scripts/post-receive` → publish.
- **Diagnóstico**: `python pipeline.py smoke --dry-run`.
- **Regressão**: `pytest tests/test_regression_patches.py` (27 testes, 46/46 patches).

## Regra de ouro
A pipeline canônica é o **ÚNICO** caminho para gerar sites.
Mudou a pipeline, código, config ou docs? Atualizar **`AGENTS.md` primeiro** e propagar.
