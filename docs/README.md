# FraLib Docs — Índice

Fonte de verdade operacional: `../README.md` e `../AGENTS.md`.

Esta pasta contém histórico, specs, consultas SQL e documentos auxiliares. Muitos arquivos foram escritos antes da consolidação da pipeline visual em 2026-08-13 e podem citar caminhos legados.

## Como Usar Esta Pasta

- Use `../README.md` para entender produção, pipeline e deploy.
- Use `../AGENTS.md` para regras obrigatórias de alteração por IA.
- Use arquivos desta pasta apenas como contexto histórico ou referência específica.
- Se houver conflito entre um arquivo em `docs/` e `../README.md`, siga `../README.md`.

## Status dos Documentos Antigos

Documentos antigos sobre:

- Liam;
- `pipeline_executors.py`;
- `openui_renderer.py`;
- OpenUI Node/porta `3333`;
- VPS antiga `100.124.56.36` ou `104.243.41.166` sem domínio `app`;
- fluxo sem `niche_brief`, `creative_direction` e `variation_blueprint`;

devem ser considerados desatualizados até revisão explícita.

## Produção Atual

Resumo:

```text
Admin/API → jobs → worker.py → manager FSM → OpenUI :7878 → Gates → Deploy
```

Consulte `../README.md` para detalhes completos.
