<!--
LEGACY / HISTÓRICO — não use como fonte de verdade.
Ver docs/ONE_TRUTH_CANONICAL_STATE.md e docs/SYSTEM_OPERATIONS_MAP.md para o estado canônico atual.
-->


# FraLib — Auditoria do Sistema

Data: 2026-05-30 America/Sao_Paulo.
Branch: `codex/pipeline-stabilization`.

## Resumo Executivo

O sistema tem uma arquitetura promissora: pipeline de agentes, fila, checkpoint, Skill Renderer unico, Bryan separado e observabilidade parcial. O risco principal era operacional: producao e local tinham alteracoes manuais fora do Git, documentacao divergente e locks orfaos. Antes de benchmark real, a prioridade correta e tornar o estado reproduzivel.

## O Que Esta Certo

- Servicos essenciais existem na VPS: backend, worker, Skill Renderer via LLM, meowhats e gosom.
- Pipeline separa captura, qualificacao, inteligencia, PRD, HTML, validacao, deploy e SDR.
- Skill Renderer concentra a geracao HTML no caminho principal, reduzindo rotas concorrentes.
- Bryan e enfileirado como job separado e nao deveria bloquear deploy.
- Existe `pipeline_state`, `pipeline_queue`, checkpoints e traces.
- Refatoracao do Arquiteto Mestre em blocos reduz o monolito.

## O Que Estava Errado

- Local e VPS estavam no mesmo commit base, mas com codigo nao commitado.
- `AGENTS.md`, `CLAUDE.md` e `README.md` descreviam pipelines diferentes.
- `pipeline_state` tinha lock orfao para tenant 2.
- `keyword_research.py` lia `backend/.env` manualmente e falhava com `.env` na raiz.
- Smoke antigo do Caio estava quebrado: passava `dict` incompatível e esperava `int` onde a funcao retorna tupla.
- PRD podia sair sem `sobre`, embora o validador exigisse essa secao.
- Arquivos temporarios/ad hoc locais atrapalhavam busca e reproduzibilidade.
- Existiam muitas pastas FraLib fora de `C:\fralib` e `/root/fralib`, criando contexto falso para outras IAs.

## Sinais de Risco na VPS

- PM2 reportou muitos restarts historicos do processo `fralib`.
- Fila recente tinha erros de PRD sem secoes obrigatorias, timeout Anthropic e falha de run OD.
- Havia arquivos untracked na VPS, incluindo caches, testes e scripts soltos.
- A tabela `pipeline_queue` na VPS tem schema legado diferente do worker novo em alguns pontos.

## Correcoes Nesta Branch

- Criado CLI oficial: `python pipeline.py smoke --dry-run`.
- Adicionado reset central de locks orfaos em `backend/core/database.py`.
- Endpoint `/api/pipeline/iniciar` usa reset central antes de bloquear nova execucao.
- `keyword_research.py` agora usa `DATABASE_URL` do ambiente com `dotenv` raiz/backend.
- Caio aceita `dict` legado nos testes de smoke sem afetar fluxo normal.
- Bloco de estrutura e Arquiteto garantem `hero`, `sobre`, `servicos`, `contato`.
- Documentacao consolidada em `AGENTS.md`, `CLAUDE.md`, `README.md`.
- `.gitignore` cobre caches/logs/temporarios que nao devem virar produto.
- Documentos agora declaram `C:\fralib` e `/root/fralib` como fontes canonicas; pastas externas sao legado/backup.
- RAG/docs/frontend/backend nao expõem mais agentes antigos; o smoke bloqueia regressao.

## Multiusuario e Robustez

- Padrao correto: tudo que e dado de cliente precisa carregar `tenant_id/user_id` ate DB, jobs, assets, URL e WhatsApp.
- Ja existe escopo por tenant em muitos pontos: leads, pipeline_state, pipeline_executions, assets `/sites/{tenant_id}/{slug}` e meowhats `fralib_user_{tenant_id}`.
- Ainda falta hardening profissional: testes automatizados de isolamento entre tenants, indices compostos por `user_id`, limite global de concorrencia por worker e auditoria de SQL cru.
- Risco principal de escala: `pipeline_endpoints.py` concentra orquestracao demais; quebrar em fases reduz bug por alteracao concorrente.

## Endpoints Auditados por Mapa

- Pipeline: `/api/pipeline/*`.
- Leads/site: `/api/leads/*`, `/api/sites/*`.
- Logs/SSE: `/api/logs/*`.
- Queue/falhas: `/api/queue/*`, `/api/falhas/*`.
- Observability: `/api/observability/*`.
- WhatsApp: `/api/whatsapp/*`.
- LLM/config: `/api/llm/*`, `/api/agent-configs/*`, `/api/provider-keys/*`.
- Admin/uso: `/api/superadmin/*`, `/api/usage/*`, `/api/credits/*`.

## Proximas Medidas Profissionais

1. Rodar smoke dry-run local e na VPS apos deploy.
2. Corrigir qualquer divergencia de schema entre worker novo e `pipeline_queue` legado.
3. Criar benchmark real com uma pipeline curta e medir tempos por fase.
4. Adicionar budget de tokens por fase e alertas quando Arquiteto/OD excederem baseline.
5. Quebrar `pipeline_endpoints.py` em runner, fases, validacao e rotas.
6. Criar script versionado para limpar untracked antigo na VPS, com dry-run antes.

## Auditoria 2026-05-30 — Deploy E Direcao Visual

- Causa raiz do frontend antigo reaparecer: `scripts/post-receive` publicava em
  qualquer push recebido, mas sempre puxava `origin master`. Push em branch de
  estabilizacao podia republicar um master antigo.
- Risco adicional: o hook copiava `frontend/*.html`, incluindo artefatos soltos.
- Risco adicional: `frontend/build.py` tentava copiar direto para
  `/var/www/fralib`, criando rota de deploy fora do Git.
- Correcao: hook ignora pushes sem mudanca em `refs/heads/master`, valida
  frontend canonico e publica HTML por whitelist.
- Correcao: build apenas gera artefatos locais; smoke roda contratos
  `frontend-canonical` e `deploy-contract`.
- Removidos `frontend/landing2.html` e `frontend/landing_backup.html`.
- Design: FraLib ja tinha design systems, craft rules, GSAP/Lenis e repair do
  Liam. A lacuna foi fechada com arquétipos compactos universais injetados no
  Arquiteto, Liam e queries Unsplash.
- Arquétipos: `BOLD_IMPACT`, `TRUST_AUTHORITY`, `ZEN_WELLNESS`,
  `MODERN_TECH`, `LUXURY_EDITORIAL`.
- Auditoria VPS ficou pendente: SSH recusou autenticacao neste ambiente.
