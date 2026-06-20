# PRD MVP — Pipeline Multiusuario, Fila Justa e Controle de Custo

## Contexto

O FraLib hoje usa uma fila `jobs` compartilhada entre tenants. Isso funciona em baixo volume, mas gerou ruido operacional: jobs antigos de usuarios diferentes ficam na mesma fila, um pipeline longo pode segurar todos, retries antigos confundem status, e uma unica API key compartilhada impede paralelizar sem controle de custo/rate limit.

O objetivo do MVP e deixar a pipeline profissional para multiusuarios, sem perder progresso e sem estourar limite da API.

## Objetivos

- Cada usuario deve enxergar e controlar apenas seus jobs, leads, falhas e status.
- A fila deve ser justa por tenant: nenhum usuario deve bloquear todos os outros.
- A pipeline de um mesmo tenant deve rodar sequencialmente por padrao para evitar duplicidade, disputa de cooldown e overwrite de site.
- A chave de API compartilhada deve ter limite global de concorrencia, tokens/minuto e custo/dia.
- O sistema deve saber responder: quantas pipelines simultaneas podemos rodar hoje?
- Erro em uma fase deve permitir retomar do ultimo checkpoint valido.
- HTML completo do Skill Renderer deve ser preservado como HTML final, sem wrapper/footer legado.

## Nao Objetivos Do MVP

- Nao criar infra pesada como Celery/Redis agora, salvo se Postgres nao sustentar.
- Nao prometer paralelismo ilimitado enquanto houver uma unica API key compartilhada.
- Nao misturar Bryan/WhatsApp com capacidade de geracao de site no mesmo limite critico.

## Decisao Recomendada

Manter uma fila Postgres unica, mas com scheduler profissional:

- `tenant_id` obrigatorio em jobs de pipeline.
- Claim justo por tenant com `SKIP LOCKED`.
- No maximo 1 pipeline rodando por tenant.
- 2 a 3 workers de pipeline no total, limitados por um semaforo global de LLM.
- Bryan em fila/worker separado ou prioridade menor que pipeline.
- Rate limiter global por provider/modelo antes de cada chamada LLM.

Isso evita criar uma fila fisica por usuario, mas entrega isolamento operacional.

## Capacidade E Custo

Formula inicial:

- `pipeline_cost = soma(tokens_in * preco_in + tokens_out * preco_out por modelo)`
- `pipeline_time = soma(p95_fase)`
- `max_parallel_by_rate = floor(tokens_por_minuto_disponiveis / tokens_por_minuto_por_pipeline)`
- `max_parallel_by_budget = floor(orçamento_por_hora / custo_p95_pipeline)`
- `max_parallel_final = min(max_parallel_by_rate, max_parallel_by_budget, workers_pipeline, limite_builder_renderer)`

Sem medicao real de tokens por agente, usar modo conservador:

- 1 pipeline simultanea enquanto a API key for unica e sem BYOK.
- Liberar 2 pipelines somente quando ledger mostrar p95 e custo reais por 20 execucoes.
- Liberar 3+ apenas com pool de chaves/BYOK ou rate limit contratado maior.

## MVP Tasks

### Fase 1 — Reset E Higiene

> **LEGADO:** `pipeline_queue` e legado; `jobs` e a fila canonica.
> Referencias a `pipeline_queue` abaixo refletem o estado do documento em 2026-06
> e nao o estado canonico atual. Ver `docs/ONE_TRUTH_CANONICAL_STATE.md`.

- Zerar dados runtime/teste: `jobs`, `pipeline_queue`, `pipeline_state`, `pipeline_executions`, `pipeline_failures`, `leads`, `interacoes`, `site_visitas`, checkpoints e sites gerados.
- Manter usuarios, planos, auth, provider keys e configuracoes.
- Adicionar comando oficial `python pipeline.py reset-runtime --confirm` para nunca mais fazer limpeza manual por SQL solto.
- ~~Ao concluir retry com sucesso, limpar `pipeline_queue.erro`.~~ *(LEGADO: `pipeline_queue` nao e mais a fonte ativa.)*

### Fase 2 — Isolamento De Fila

- Corrigir `queue_endpoints.py` para usar `criado_em` e filtrar por `tenant_id` para usuario comum.
- `claim_next()` deve priorizar pipeline sobre Bryan.
- `claim_next()` nao deve pegar segunda pipeline do mesmo tenant se ja existir pipeline `running`.
- Adicionar fairness por tenant para alternar tenants elegiveis.
- Adicionar testes de concorrencia: dois workers nao duplicam job, tenants diferentes podem rodar, mesmo tenant nao roda duas pipelines.

### Fase 3 — Controle Global De API

- Criar tabela `llm_budget_ledger` com `tenant_id`, `job_id`, `agent`, `model`, `tokens_in`, `tokens_out`, `cache_read`, `cost_usd`, `started_at`, `finished_at`.
- Criar `provider_rate_limits` com limites por provider/modelo: RPM, TPM, max_concurrency, daily_budget.
- Antes de chamada LLM, reservar capacidade em token bucket global.
- Se sem capacidade: job volta para `pending` com `next_retry_at`, sem consumir tentativa.
- Dashboard admin: custo por pipeline, por agente, por tenant e por dia.

### Fase 4 — Workers Profissionais

- Rodar pelo menos 2 workers de pipeline, mas com limite global de LLM.
- Separar worker Bryan ou limitar Bryan a rodar quando nao houver pipeline pendente.
- Heartbeat durante chamadas longas de LLM/Skill Renderer.
- Timeout por fase, nao apenas timeout global.
- Dead-letter com motivo amigavel e tecnico.

### Fase 5 — Pipeline Retomavel

- Checkpoint por `tenant_id + lead_id + job_id`, nao por segmento/cidade.
- Retomar fase cara somente se checkpoint pertence ao mesmo lead/tenant.
- Se Skill Renderer ja gerou `index.html` completo, reaproveitar.
- Se deploy falhar, nao regerar PRD/HTML; retomar em deploy.

### Fase 6 — Skill Renderer Como Fonte Visual

- Preservar `<!doctype html>` completo vindo do Skill Renderer.
- Nao embrulhar HTML completo em `montar_template_python`.
- Deixar SEO/schema/tracking como passes pequenos e nao destrutivos.
- Verificar visual com screenshot antes de marcar sucesso.

## Critérios De Aceite

- Usuario 2 nao ve jobs/leads/falhas de usuario 31 no dashboard comum.
- Dois usuarios diferentes podem ter jobs pendentes sem bloquear um ao outro por ruido antigo.
- Mesmo usuario nao roda duas pipelines de site ao mesmo tempo.
- Com API key unica, o sistema nunca ultrapassa limite configurado de concorrencia/tokens.
- Um erro em Skill Renderer/quality gate/deploy permite retry do ponto correto.
- Site novo gerado pelo Skill Renderer nao contem `fralib-content` nem `fralib-footer-token-lock`.
- `python pipeline.py pre-release-gate` passa antes de deploy.

## Sequencia Recomendada

1. Fechar Fase 1 e Fase 2 antes de novo teste real.
2. Rodar 1 pipeline real para usuario 2, academia em Campina Grande do Sul.
3. Medir custo/tempo por fase.
4. Definir `max_parallel_final`.
5. So entao testar usuario 31 em paralelo controlado.

## Mudancas Imediatas Aprovadas

Antes do proximo teste real, aplicar:

- Subir guardrails de fila ja preparados: pipeline antes de Bryan, filtro por
  `tenant_id` nos endpoints de fila e bloqueio de duas pipelines simultaneas
  para o mesmo tenant.
- Manter concorrencia global conservadora enquanto a API key for compartilhada:
  `MAX_PIPELINES_GLOBAL=1`.
- Separar Bryan da geracao de sites na prioridade operacional; Bryan nao deve
  impedir pipeline de site.
- Criar comando oficial `python pipeline.py reset-runtime --confirm RESET` para reset
  operacional controlado.
- Registrar custo/tempo por fase antes de liberar paralelismo maior que 1.
