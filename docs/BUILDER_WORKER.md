# Builder Worker

## Objetivo

Rota canonica para transformar o prompt final do Agente de Prompt em um site
publicavel. O motor ativo gera um projeto Vite + React + TypeScript +
Tailwind/motion componentizado e publica somente a pasta `dist`.

## Arquitetura Atual

```text
Hunter -> Caio -> Jina -> Agente de Prompt
-> backend/services/builder_worker.py
-> backend/services/vite_react_renderer.py
-> Claude Sonnet
-> fallback Claude Opus somente se Sonnet falhar validacao/build
-> .tmp/builder-workspaces/tenant-{tenant}/job-{job}/src
-> npm install --ignore-scripts
-> tsc --noEmit
-> vite build
-> .tmp/builder-workspaces/tenant-{tenant}/job-{job}/dist
-> Deploy FraLib
```

O nome logico da fase continua `builder_renderer` para manter fila, planos,
observabilidade, dashboards e mensagens de erro compativeis.

## Contrato

Cada job gera um manifest em `logs/builder_manifests` com:

- `tenant_id` e `job_id` isolados;
- `engine=vite_react`;
- prompt completo do Agente de Prompt;
- `idempotency_key`;
- `workspace`, `source_dir` e `output_dir` exclusivos por tenant/job.

O Builder deve entregar uma arvore Studio, semelhante a um projeto AI Studio:

- `package.json`, `index.html`, `vite.config.ts`, `tsconfig.json`;
- `src/main.tsx`, `src/App.tsx`, `src/index.css`, `src/types.ts`;
- `src/pages/Index.tsx`;
- componentes em `src/components/*.tsx`.

O renderer normaliza dependencias para uma lista fixa, valida caminhos, bloqueia
codigo ativo perigoso (`fetch`, env runtime, cookies/storage, `eval`,
`dangerouslySetInnerHTML`) e exige:

- Tailwind v4 via `@tailwindcss/vite` e `@import "tailwindcss"`;
- `motion/react`, `useState`, `useEffect` e interacoes locais;
- navbar, galeria, lifestyle/editorial, servicos/planos e modal/lightbox;
- imagens reais/editoriais com `images.unsplash.com` ou midia do briefing;
- densidade minima de fonte e componentes para evitar site magro.

Depois roda:

```bash
npm install --ignore-scripts --no-audit --no-fund
node node_modules/typescript/bin/tsc --noEmit
node node_modules/vite/bin/vite.js build
```

O deploy copia somente `dist`. Fonte React fica como evidencia/auditoria no
workspace isolado.

## OpenUI Legado

`FRALIB_BUILDER_ENGINE=openui` ainda executa o renderer HTML puro para debug ou
rollback controlado. Ele nao e a rota padrao.

## Custos

O Builder usa `agents.llm_direct.call_claude`, portanto custo e tokens entram em:

- `llm_usage`;
- `llm_budget_ledger`;
- `llm_budget_ledger` (fonte canonica de custo/tokens via TokenTracker/log_tracking).

Modelos padrao:

- `FRALIB_OPENUI_PRIMARY_MODEL=sonnet`;
- `FRALIB_OPENUI_FALLBACK_MODEL=opus`;
- `FRALIB_VITE_REACT_MAX_TOKENS=36000`;
- `FRALIB_OPENUI_TEMPERATURE=0.55`.

Para `builder_renderer`, o DB pode ajustar provider/model/temperatura, mas nao
reduz `max_tokens` abaixo do teto solicitado pelo Vite Studio.

Quando houver `key_invalid` ou cooldown global por API, corrija por comando
versionado, nunca por SQL solto:

```bash
set FRALIB_PROVIDER_API_KEY=...
python pipeline.py repair-provider-key --provider anthropic --label aibee-main
python pipeline.py repair-provider-key --provider anthropic --label aibee-main --apply --mark-alerts-read
```

O primeiro comando so valida. O segundo grava em `provider_keys`, limpa
`global_cooldown_until` e marca alertas antigos como lidos.

## Deploy

O hook publica `master`, preserva `.env`, valida frontend canonico e reinicia
PM2. Sites gerados pelo Builder ja chegam compilados em `dist` antes da copia
para o diretorio publico.
