<!--
LEGACY / HISTÓRICO — não use como fonte de verdade.
Ver docs/ONE_TRUTH_CANONICAL_STATE.md e docs/SYSTEM_OPERATIONS_MAP.md para o estado canônico atual.
-->


# FraLib Builder Pipeline

## Arvore Real

```text
Lead Supply
  Hunter -> lead_inventory
  Caio -> fila de producao

Pipeline de Producao
  Jina / inteligencia de mercado
  backend/agents/site_prompt_agent.py
    -> contrato-prompt final + visual_direction
  backend/services/builder_worker.py
    -> manifest tenant/job
  backend/services/vite_react_renderer.py
    -> Vite/React/Tailwind/motion/Sonnet
    -> Opus se Sonnet falhar validacao/build
    -> src/pages/Index.tsx
    -> src/components/*.tsx
    -> navbar/galeria/lifestyle/modal/imagens reais
    -> npm install --ignore-scripts
    -> tsc --noEmit
    -> vite build
  .tmp/builder-workspaces/tenant-{tenant}/job-{job}/dist/index.html
  Deploy
  Bryan/SDR conforme plano
```

## O Que Saiu da Rota Padrao

- OpenUI HTML puro como motor principal;
- Sandbox Agent/Bolt;
- PM2 `fralib-sandbox-agent`;
- `FRALIB_SANDBOX_AGENT_URL`.

OpenUI continua disponivel com `FRALIB_BUILDER_ENGINE=openui` para rollback
controlado.

## Contrato Visual Studio

O Vite renderer nao aceita mais entrega React magra. O projeto precisa ter
Tailwind v4, `motion/react`, estado/efeitos, navbar, galeria premium, lifestyle
editorial, modal/lightbox, imagens reais/editoriais e densidade minima de fonte.
Se esses sinais estiverem ausentes, Sonnet falha a validacao e Opus recebe o
brief de reparo completo.

## Multi-tenant

O isolamento acontece por:

- `tenant_id`;
- `job_id`;
- manifest scoped;
- output em `.tmp/builder-workspaces/tenant-{tenant}/job-{job}`;
- ledger com `tenant_id`;
- fila de producao reservando 1 lead aprovado por vez.

Nenhum job compartilha fonte ou `dist` com outro tenant. O deploy copia apenas o
`dist` compilado.

## Auditoria de Peso

O sistema vai acumular:

- fontes React em `.tmp/builder-workspaces`;
- `dist` compilado;
- manifests em `logs/builder_manifests`;
- `builder-render.json` e `vite-render.json`;
- caches de npm/node_modules por job;
- screenshots e traces de testes;
- fotos/midias baixadas.

Plano recomendado de limpeza diaria:

1. Manter outputs publicados e manifests recentes.
2. Apagar workspaces `.tmp/builder-workspaces` com mais de 7 dias quando o site
   ja estiver publicado.
3. Apagar caches `pytest-cache-files-*`, `__pycache__`, `htmlcov` e coverage
   fora de runs de QA.
4. Compactar ou expirar leads rejeitados/duplicados por tenant.
5. Manter logs de custo e falha por pelo menos 30 dias para auditoria.

## Criterio Para Rodar Pipeline

Antes de producao em massa:

- `python pipeline.py smoke --dry-run`;
- `python pipeline.py pre-release-gate`;
- teste real de 1 lead com `FRALIB_PROMPT_AGENT_FLOW=1`;
- confirmar `llm_budget_ledger` com linha `builder_renderer`;
- confirmar site publicado com bundle `assets/*.js` e metadata `vite-render.json`.
