# PRD MVP — Estabilizacao Profissional do FraLib

Data: 2026-05-26.
Branch: `codex/pipeline-stabilization`.

## 1. Objetivo

Transformar o FraLib em um SaaS reproduzivel, multiusuario e auditavel, removendo ruido legado e impedindo que agentes, docs, backups ou caches antigos voltem a contaminar o desenvolvimento.

O MVP nao busca adicionar features comerciais novas. Ele estabiliza a base para que o produto aguente usuarios simultaneos sem misturar dados, travar pipeline, gastar tokens sem controle ou quebrar por divergencia entre local, VPS e documentacao.

## 2. Problema

O sistema tinha sinais de produto promissor, mas com risco operacional alto:

- Contexto antigo dentro do repo e fora dele induzia IAs a citar agentes e arquivos inexistentes.
- Docs descreviam pipelines diferentes.
- Pipeline concentrado demais em arquivos grandes, com pontos de lock e checkpoint sensiveis.
- Execucao multiusuario dependia de disciplina manual em queries, assets, jobs e WhatsApp.
- Smoke/preflight nao bloqueava regressao de contexto legado.
- Deploy e producao tinham historico de alteracoes fora do Git.

## 3. Principios

- Fonte da verdade unica: local `C:\fralib`, VPS `/root/fralib`, Git como origem operacional.
- Todo dado de cliente deve carregar `tenant_id` ou `user_id`.
- Pipeline real so roda depois de smoke dry-run passar.
- Nada de deploy manual por SCP/rsync.
- Legado nao documentado e nao importado deve ser removido ou isolado.
- Cada correcao critica precisa de teste, smoke ou criterio de aceite verificavel.

## 4. Escopo do MVP

### Dentro do MVP

- Consolidar documentacao canonica: `AGENTS.md`, `CLAUDE.md`, `README.md`, `docs/SYSTEM_AUDIT.md`.
- Remover referencias publicas a agentes legados e caminhos fantasmas.
- Criar contrato automatizado no smoke para bloquear retorno de nomes/caminhos antigos.
- Garantir que locks e checkpoints sejam escopados por tenant.
- Padronizar nomes reais do pipeline: Hunter, Caio, Jina, Agente de Nicho, Agente de Variacao, Arquiteto Mestre, Skill Renderer, Quality Gate, Deploy, Bryan.
- Auditar endpoints e jobs mais sensiveis para `tenant_id/user_id`.
- Validar imports, regras do Caio, contrato minimo do PRD, portas e DB.
- Documentar plano de hardening multiusuario e observabilidade.

### Fora do MVP

- Reescrever todo o `pipeline_endpoints.py`.
- Implementar RLS PostgreSQL completo.
- Trocar PM2 por Kubernetes/Docker.
- Criar novo design do produto.
- Rodar benchmark pago com LLM em massa.

## 5. Jornada Operacional Alvo

1. Desenvolvedor abre `C:\fralib`.
2. Le `AGENTS.md` e identifica o pipeline real.
3. Executa `python pipeline.py smoke --dry-run`.
4. Se o smoke falhar por contexto legado, remove o ruido antes de rodar pipeline real.
5. Commit e push sao a unica rota de deploy.
6. Na VPS, `/root/fralib` recebe o Git e reinicia servicos via hook.
7. Operador roda o smoke na VPS antes de teste real.

## 6. Requisitos Funcionais

### RF1 — Contrato de Contexto

O smoke deve falhar se encontrar nomes/caminhos legados em docs, backend ou frontend.

Aceite:
- `python pipeline.py smoke --dry-run` mostra `context-contract` como `PASS`.
- Busca por agentes legados nao retorna ocorrencias no escopo canonico.

### RF2 — Smoke Oficial

O smoke deve validar sem chamar LLM, Hunter real, deploy ou WhatsApp:

- env minima
- imports criticos
- DB e locks
- regras do Caio
- secoes obrigatorias do PRD
- contexto canonico
- portas locais

Aceite:
- Local pode falhar apenas se servicos locais estiverem desligados.
- Na VPS, todos os passos precisam passar antes de pipeline real.

### RF3 — Multiusuario Seguro por Padrao

Toda operacao de lead, pipeline, asset, job e WhatsApp deve ser escopada por tenant.

Aceite:
- Queries de leitura/escrita em endpoints criticos usam `user_id` ou `tenant_id`.
- Sites gerados usam `/sites/{tenant_id}/{slug}`.
- Bryan usa sessao `fralib_user_{tenant_id}`.
- Checkpoints usam `pipeline_id` com prefixo de usuario.

### RF4 — Pipeline Canonico

Docs, RAG, frontend admin e logs devem usar apenas os nomes reais.

Aceite:
- `AGENTS.md`, `CLAUDE.md`, `README.md` contam a mesma historia.
- RAG usa `agente_nicho`, `builder_renderer` e demais agentes ainda ativos.
- Painel admin nao mostra sandbox legado como fluxo ativo.

### RF5 — Deploy Reproduzivel

O estado de producao deve ser derivavel do Git.

Aceite:
- Hook usa `/root/fralib`.
- Nenhum arquivo temporario/cache vira fonte de produto.
- `.gitignore` cobre logs, caches, checkpoints, backups e stubs soltos.

## 7. Requisitos Nao Funcionais

- Confiabilidade: falhas transientes devem ter retry controlado; falhas permanentes nao devem entrar em loop.
- Concorrencia: um pipeline por tenant, varios tenants em paralelo via fila/worker.
- Observabilidade: cada run deve ter trace, ledger e status consultavel.
- Seguranca: endpoints de cliente nunca podem acessar dado de outro tenant.
- Custo: chamadas LLM devem usar modelo por complexidade e cache quando possivel.
- Manutenibilidade: arquivos monoliticos devem ser quebrados por fases apos o MVP.

## 8. Backlog Prioritario

### P0 — Bloqueadores

- [x] Criar docs canonicos e remover divergencia de pipeline.
- [x] Remover nomes legados do contexto ativo.
- [x] Criar smoke oficial `python pipeline.py smoke --dry-run`.
- [x] Adicionar contrato de contexto ao smoke.
- [x] Remover backups locais que contaminavam busca.
- [ ] Rodar smoke completo na VPS.
- [N/A] Corrigir divergencia de schema real da `pipeline_queue`, se aparecer no smoke VPS.  *(Nao aplicavel — `pipeline_queue` e legado; ver `docs/ONE_TRUTH_CANONICAL_STATE.md`.)*

### P1 — Multiusuario e Robustez

- [ ] Criar teste de isolamento cross-tenant para leads, pipeline_state, sites e jobs.
- [x] Mapear queries SQL cruas e adicionar guardrail estatico (`scripts/tenant_scope_audit.py`) para bloquear SQL em `leads` sem `user_id/tenant_id`.
- [ ] Adicionar indices compostos: `(user_id, status)`, `(tenant_id, status)`, `(user_id, criado_em)`.
- [ ] Garantir que arquivos de site, assets, checkpoints e logs publicos nunca usem slug global.
- [ ] Definir limite de concorrencia global por worker e limite por tenant.
- [ ] Tornar idempotency_key obrigatoria para jobs de pipeline.

### P2 — Observabilidade e Operacao

- [ ] Criar endpoint/admin view de smoke e health por servico.
- [ ] Registrar p50/p95 por fase: Hunter, Caio, Jina, Arquiteto, Skill Renderer, Quality Gate, Deploy, Bryan.
- [ ] Alertar quando run exceder baseline de tokens, tempo ou retries.
- [ ] Criar script versionado de limpeza VPS com `--dry-run`.
- [ ] Documentar rollback operacional do hook de deploy.

### P3 — Arquitetura

- [ ] Quebrar `pipeline_endpoints.py` em `routes`, `runner`, `phases`, `state`, `deploy`.
- [ ] Quebrar `leads_endpoints.py` por dominio: CRUD, site editor, SDR, analytics.
- [ ] Criar camada repository/service para SQL critico.
- [ ] Avaliar RLS PostgreSQL depois dos testes de isolamento.
- [ ] Criar benchmark real curto com custo controlado.

## 9. Plano de Execucao

### Sprint 1 — Estado Reproduzivel

- Finalizar commit da estabilizacao.
- Rodar smoke local e documentar falhas esperadas por servicos desligados.
- Push da branch.
- Rodar smoke na VPS.
- Corrigir falhas de schema/porta/lock encontradas na VPS.

### Sprint 2 — Multiusuario

- Escrever testes cross-tenant.
- Corrigir endpoints/queries sem filtro de tenant.
- Adicionar indices.
- Validar pipeline simultaneo com dois tenants usando jobs controlados.

### Sprint 3 — Operacao

- Dashboard de health/smoke.
- Metricas p95 por fase.
- Alertas de custo/latencia.
- Script versionado de limpeza VPS.

### Sprint 4 — Refatoracao Estrutural

- Extrair fases do pipeline para modulos.
- Reduzir superficie de bug em `pipeline_endpoints.py`.
- Criar contrato de fase com inputs/outputs tipados.

## 10. Criterios de Aceite do MVP

- `python pipeline.py smoke --dry-run` passa na VPS.
- Nenhuma busca no escopo canonico retorna agentes/caminhos legados.
- Dois tenants conseguem ter pipelines/jobs sem compartilhar lead, checkpoint, site, asset ou sessao WhatsApp.
- Deploy acontece somente por Git.
- Admin e docs exibem apenas o pipeline atual.
- Falhas geram mensagem amigavel para usuario e detalhe tecnico para suporte.

## 11. Riscos

- Schema legado na VPS pode divergir do codigo novo.
- Refatorar o monolito inteiro antes de estabilizar pode aumentar o risco.
- Sem testes cross-tenant, regressao multiusuario pode voltar silenciosamente.
- LLM/Skill Renderer podem gerar custo/latencia altos se nao houver budget por fase.

## 12. Decisao de MVP

O MVP termina quando o FraLib tiver smoke confiavel, contexto limpo, deploy reproduzivel e isolamento multiusuario validado. Depois disso, novas features comerciais ficam mais seguras de implementar.
