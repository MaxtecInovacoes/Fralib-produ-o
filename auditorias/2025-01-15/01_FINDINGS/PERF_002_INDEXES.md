# PERF_002 - Database Index Audit Report

**Data**: 2025-01-15
**Auditor**: Performance Engineer (Claude)
**Status**: PROBLEMAS ENCONTRADOS
**Severidade Geral**: MEDIA-ALTA

---

## Resumo Executivo

| Categoria | Encontrados |
|---|---|
| Indices faltantes CRITICOS | 4 |
| Indices faltantes HIGH | 6 |
| Indices faltantes MEDIUM | 8 |
| Padrao N+1 / JOIN textual | 1 |
| **Total de recomendacoes** | **19** |

---

## Questoes Criticas de Indice

### FINDING_001 - `leads.criado_em` SEM INDICE

**Tabela**: `leads`
**Coluna**: `criado_em`
**Arquivo**: `backend/endpoints/leads_queries.py:249, 261, 275, 299`, `backend/endpoints/leads_crud.py:69`
**Query Impacto**:
```sql
-- get_leads_incompletos (leads_queries.py:249)
SELECT ... FROM leads WHERE user_id = :uid AND (...) ORDER BY criado_em DESC LIMIT 200

-- get_fila_qualificados (leads_queries.py:275)
SELECT ... FROM leads WHERE user_id = :uid AND status = 'concluido' ORDER BY criado_em ASC LIMIT 100

-- get_descartados (leads_queries.py:299)
SELECT ... FROM leads WHERE user_id = :uid AND status = 'descartado' ORDER BY atualizado_em DESC LIMIT 100

-- fila_sql (leads_queries.py:27)
SELECT ... FROM leads WHERE user_id = :uid AND status = :st ORDER BY criado_em ASC LIMIT 1

-- desq_sql (leads_queries.py:37)
SELECT ... FROM leads WHERE user_id = :uid AND (status = 'desqualificado' OR ...) ORDER BY criado_em DESC LIMIT 200

-- get_sites (leads_crud.py:69)
SELECT ... FROM leads WHERE (site_url IS NOT NULL ...) AND user_id = :uid ORDER BY criado_em DESC
```

**Impacto**: Full table scan em `leads` a cada requisicao. Tabela pode ter milhoes de linhas. Todas as queries com ORDER BY `criado_em` ou `atualizado_em` fazem sort em memoria.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_leads_user_criado_em
ON leads (user_id, criado_em DESC);

CREATE INDEX idx_leads_user_status_criado_em
ON leads (user_id, status, criado_em ASC)
WHERE status IN ('capturado', 'pendente', 'concluido');

CREATE INDEX idx_leads_user_status_criado_em_desc
ON leads (user_id, status, criado_em DESC)
WHERE status IN ('descartado', 'rejeitado', 'desqualificado');
```

**Prioridade**: CRITICA
**Impacto Estimado**: Reduz de ~500ms para <5ms em tabelas com mais de 10.000 leads.

---

### FINDING_002 - `interacoes.lead_id` SEM INDICE

**Tabela**: `interacoes`
**Coluna**: `lead_id`
**Arquivos**:
- `backend/endpoints/leads_queries.py:57` (JOIN)
- `backend/endpoints/leads_queries.py:114` (WHERE lead_id)
- `backend/whatsapp_listener.py:415-418` (JOIN)
- `backend/whatsapp_listener.py:503` (WHERE lead_id)
- `backend/whatsapp_listener.py:539` (UPDATE)
- `backend/whatsapp_listener.py:615-617` (WHERE lead_id)
- `backend/endpoints/leads_crud.py:507` (DELETE subselect)
- `backend/services/sdr_gateway.py:187-189` (WHERE lead_id + user_id + direcao)

**Query Impacto**:
```sql
-- get_conversa (leads_queries.py:57)
SELECT i.id, i.mensagem, i.direcao, i.criado_em
FROM interacoes i
JOIN leads l ON l.id = i.lead_id
WHERE i.lead_id = :lead_id AND l.user_id = :uid
ORDER BY i.id ASC

-- get_lead_chat (leads_queries.py:114)
SELECT mensagem, direcao, criado_em FROM interacoes
WHERE lead_id = :lid ORDER BY id ASC LIMIT 100

-- whatsapp_listener.py:503
SELECT mensagem FROM interacoes
WHERE lead_id=:lead_id AND user_id=:user_id AND direcao='saida'
ORDER BY criado_em DESC LIMIT 1
```

**Impacto**: JOIN entre `interacoes` e `leads` sem indice em `interacoes.lead_id`. Para cada mensagem trocada (pode ser milhoes de linhas), o banco faz full scan em `interacoes`.

**Sugestao de Indice**:
```sql
-- Indice simples para lookups por lead
CREATE INDEX idx_interacoes_lead_id
ON interacoes (lead_id);

-- Indice composto para a query mais comum do whatsapp_listener
CREATE INDEX idx_interacoes_lead_user_direcao
ON interacoes (lead_id, user_id, direcao, criado_em DESC);
```

**Prioridade**: CRITICA
**Impacto Estimado**: JOIN de interacoes sem indice em leads com milhoes de linhas. Reduz de segundos para milissegundos.

---

### FINDING_003 - `ciclos.user_id` SEM INDICE

**Tabela**: `ciclos`
**Coluna**: `user_id`
**Arquivo**: `backend/endpoints/pipeline_endpoints.py:24`
**Query Impacto**:
```sql
-- get_ciclos (pipeline_endpoints.py:24)
SELECT id, numero, cidade, segmento, leads_buscados, sites_gerados, ...
FROM ciclos
WHERE user_id = :uid
ORDER BY id DESC
LIMIT 100
```

**Impacto**: Full table scan em `ciclos`. Tambem referenced em `backend/endpoints/pipeline_status_endpoints.py` para agregado de metricas.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_ciclos_user_id
ON ciclos (user_id, id DESC);
```

**Prioridade**: HIGH
**Impacto Estimado**: ~50-200ms em tabelas com >1.000 ciclos.

---

### FINDING_004 - JOIN textual `interacoes.lead_nome = leads.nome` (N+1 e full scan)

**Tabelas**: `interacoes` + `leads`
**Colunas**: `lead_nome` (TEXT), `nome` (VARCHAR 255)
**Arquivos**:
- `backend/endpoints/pipeline_status_endpoints.py:246`
- `backend/endpoints/pipeline_status_endpoints.py:251`

**Query Impacto**:
```sql
-- /pipeline/stats - COUNT DISTINCT (MAIS CARO)
SELECT COUNT(DISTINCT i.lead_nome)
FROM interacoes i
JOIN leads l ON l.nome = i.lead_nome   -- TEXT JOIN = SEM INDICE
WHERE l.user_id = :uid AND i.direcao = 'entrada'

-- /pipeline/stats - COUNT mensagens saida
SELECT COUNT(*)
FROM interacoes i
JOIN leads l ON l.nome = i.lead_nome   -- TEXT JOIN = SEM INDICE
WHERE l.user_id = :uid AND i.direcao = 'saida'
```

**Impacto**: Este e o problema mais grave. JOIN entre duas colunas textuais sem nenhum indice. Cada linha de `interacoes` faz lookup em `leads.nome` sem indice. Para tabelas com milhoes de interacoes, esta query e incomparavel.

 Alem disso, ha um problema de integridade: `lead_nome` e texto livre que pode duplicar/inconsistir. O correto e usar `lead_id` como chave de juncao.

**Sugestao de Indice** (Workaround imediato):
```sql
-- Se os dados de lead_nome precisam ser mantidos (legacy):
CREATE INDEX idx_leads_nome_lower
ON leads (lower(nome));

CREATE INDEX idx_interacoes_lead_nome
ON interacoes (lower(lead_nome));
```

**Correcao Arquitetural** (RECOMENDADO):
```sql
-- Mudar JOIN para usar lead_id ao inves de nome textual
-- A query canonica deveria ser:
SELECT COUNT(DISTINCT i.lead_id)
FROM interacoes i
WHERE i.user_id = :uid AND i.direcao = 'entrada';
```

**Prioridade**: CRITICA (arquitetural)
**Impacto Estimado**: Query pode levar minutos em tabelas grandes. Reduz para <100ms com a correcao.

---

## Questoes HIGH

### FINDING_005 - `sdr_learning.user_id` SEM INDICE

**Tabela**: `sdr_learning`
**Colunas**: `user_id`
**Arquivo**: `backend/core/database.py:302` (schema definition)

**Context**: Tabela criada em `inicializar_database()`. Nao ha indice em `user_id`. Qualquer query por tenant fara full scan.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_sdr_learning_user_id
ON sdr_learning (user_id, criado_em DESC);
```

**Prioridade**: HIGH

---

### FINDING_006 - `hermes_incidents.actor_id` SEM INDICE

**Tabela**: `hermes_incidents`
**Coluna**: `actor_id`
**Arquivo**: `backend/core/database.py:579-604`

**Context**: Tabela criada com indice em `created_at` e `(status, severity, created_at)`, mas `actor_id` nao tem indice.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_hermes_incidents_actor
ON hermes_incidents (actor_id, created_at DESC);
```

**Prioridade**: HIGH

---

### FINDING_007 - `llm_budget_ledger.job_id` SEM INDICE

**Tabela**: `llm_budget_ledger`
**Coluna**: `job_id`
**Arquivo**: `backend/core/database.py:679-725`

**Query Impacto**: Usado em `alembic/versions/72bd68b42efe_sync_one_truth_mirrors.py:42` para fazer GROUP BY em `job_id`. tambem referenced em queries de custo por job.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_llm_budget_job
ON llm_budget_ledger (job_id);
```

**Prioridade**: HIGH

---

### FINDING_008 - `provider_alerts.user_id_afetado` SEM INDICE

**Tabela**: `provider_alerts`
**Coluna**: `user_id_afetado`
**Arquivo**: `alembic/versions/provider_alerts.py:25`

**Context**: Tabela tem indice em `(lido, criado_em)` e em `(lead_id)` WHERE lead_id IS NOT NULL, mas `user_id_afetado` nao tem indice.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_provider_alerts_user
ON provider_alerts (user_id_afetado, criado_em DESC);
```

**Prioridade**: HIGH

---

### FINDING_009 - `pipeline_failures.created_at` SEM INDICE ISOLADO

**Tabela**: `pipeline_failures`
**Coluna**: `created_at`
**Arquivo**: `backend/core/database.py:386-411`

**Query Impacto**: Queries em `queue_endpoints.py:83` fazem `WHERE created_at > NOW() - make_interval(days => :dias)`.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_failures_created_at
ON pipeline_failures (criado_em DESC);
```

**Nota**: Ja existe `idx_failures_tenant` em `(tenant_id, resolvido, criado_em DESC)`, mas para queries globais sem tenant filter (admin/superadmin), um indice em `created_at` sozinho ajudaria.

**Prioridade**: HIGH

---

### FINDING_010 - `pipeline_run_spans.fase_nome` SEM INDICE PARA AGREGACAO

**Tabela**: `pipeline_run_spans`
**Coluna**: `fase_nome`
**Arquivos**: `backend/endpoints/obs_endpoints.py:86` (GROUP BY fase_nome), `backend/endpoints/obs_endpoints.py:343`

**Query Impacto**:
```sql
SELECT fase_nome, COUNT(*), ROUND(AVG(duracao_ms)), ...
FROM pipeline_run_spans
WHERE tenant_id = :tenant_id AND started_at > ...
GROUP BY fase_nome
ORDER BY custo_total DESC
```

**Sugestao de Indice**:
```sql
-- Para agregacoes por fase dentro de um tenant
CREATE INDEX idx_spans_tenant_fase
ON pipeline_run_spans (tenant_id, started_at, fase_nome)
WHERE started_at > NOW() - INTERVAL '90 days';
```

**Nota**: Os indices existentes `idx_spans_tenant` e `idx_spans_status` cobrem filtragem por tenant/data, mas GROUP BY em `fase_nome` pode se beneficiar de um indice composto.

**Prioridade**: HIGH

---

## Questoes MEDIUM

### FINDING_011 - `interacoes.direcao` SEM INDICE

**Tabela**: `interacoes`
**Coluna**: `direcao`
**Query Impacto**: Filtro constante em `direcao = 'entrada'` e `direcao = 'saida'` nas queries de whatsapp_listener e leads_queries.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_interacoes_direcao
ON interacoes (direcao, criado_em DESC)
WHERE direcao IS NOT NULL;
```

**Prioridade**: MEDIUM

---

### FINDING_012 - `leads.segmento` SEM INDICE

**Tabela**: `leads`
**Coluna**: `segmento`
**Query Impacto**: `backend/endpoints/pipeline_status_endpoints.py:248` faz GROUP BY segmento.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_leads_user_segmento
ON leads (user_id, segmento)
WHERE segmento IS NOT NULL AND segmento != '';
```

**Prioridade**: MEDIUM

---

### FINDING_013 - `leads.cidade` SEM INDICE PARA GROUP BY

**Tabela**: `leads`
**Coluna**: `cidade`
**Query Impacto**: `backend/endpoints/pipeline_status_endpoints.py:249` faz GROUP BY cidade.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_leads_user_cidade
ON leads (user_id, cidade)
WHERE cidade IS NOT NULL AND cidade != '';
```

**Prioridade**: MEDIUM

---

### FINDING_014 - `leads.atualizado_em` SEM INDICE

**Tabela**: `leads`
**Coluna**: `atualizado_em`
**Query Impacto**: `get_descartados` (leads_queries.py:299) faz `ORDER BY atualizado_em DESC`. tambem usado em UPDATEs.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_leads_user_status_atualizado
ON leads (user_id, status, atualizado_em DESC)
WHERE status = 'descartado';
```

**Nota**: Ja há indice em `criado_em` (FINDING_001) que deve resolver a maioria dos casos.

**Prioridade**: MEDIUM

---

### FINDING_015 - `users.tenant_id` SEM INDICE

**Tabela**: `users`
**Coluna**: `tenant_id`
**Query Impacto**: Filtros por tenant em tabelas que referenciam users via tenant_id.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_users_tenant_id
ON users (tenant_id)
WHERE tenant_id IS NOT NULL;
```

**Prioridade**: MEDIUM

---

### FINDING_016 - `mercadopago_events.user_id` SEM INDICE

**Tabela**: `mercadopago_events`
**Coluna**: `user_id`
**Arquivo**: `backend/core/database.py:553-572`, `alembic/versions/legal_payment_hardening.py:34`

**Query Impacto**: Webhooks e queries por user_id. Tabela tem PK em `event_id` e indice em `(payment_id, criado_em)`, mas `user_id` nao tem indice.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_mercadopago_events_user
ON mercadopago_events (user_id, criado_em DESC);
```

**Prioridade**: MEDIUM

---

### FINDING_017 - `pipeline_run_spans.agente` SEM INDICE

**Tabela**: `pipeline_run_spans`
**Coluna**: `agente`
**Query Impacto**: Agregacoes por agente em `backend/endpoints/obs_endpoints.py:86`.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_spans_agente
ON pipeline_run_spans (agente, tenant_id, started_at DESC);
```

**Prioridade**: MEDIUM

---

### FINDING_018 - `pipeline_token_usage.run_id` SEM INDICE DEDICADO

**Tabela**: `pipeline_token_usage`
**Coluna**: `run_id`
**Arquivo**: `backend/core/database.py:649-675`

**Context**: `run_id` tem indice UNIQUE (ja que a coluna e UNIQUE), mas nao ha indice para queries que buscam por tenant+run_id.

**Sugestao de Indice**:
```sql
CREATE INDEX idx_token_usage_tenant_run
ON pipeline_token_usage (tenant_id, run_id);
```

**Prioridade**: MEDIUM

---

## Consolidacao de Scripts de Migracao

### Script 1/2 - Indices Criticos e HIGH

```sql
-- FINDING_001: leads.criado_em
CREATE INDEX idx_leads_user_criado_em
ON leads (user_id, criado_em DESC);

CREATE INDEX idx_leads_user_status_criado
ON leads (user_id, status, criado_em);

-- FINDING_002: interacoes.lead_id
CREATE INDEX idx_interacoes_lead_id
ON interacoes (lead_id);

CREATE INDEX idx_interacoes_lead_user_direcao
ON interacoes (lead_id, user_id, direcao, criado_em DESC);

-- FINDING_003: ciclos.user_id
CREATE INDEX idx_ciclos_user_id
ON ciclos (user_id, id DESC);

-- FINDING_005: sdr_learning.user_id
CREATE INDEX idx_sdr_learning_user_id
ON sdr_learning (user_id, criado_em DESC);

-- FINDING_006: hermes_incidents.actor_id
CREATE INDEX idx_hermes_incidents_actor
ON hermes_incidents (actor_id, created_at DESC);

-- FINDING_007: llm_budget_ledger.job_id
CREATE INDEX idx_llm_budget_job
ON llm_budget_ledger (job_id);

-- FINDING_008: provider_alerts.user_id_afetado
CREATE INDEX idx_provider_alerts_user
ON provider_alerts (user_id_afetado, criado_em DESC);

-- FINDING_009: pipeline_failures.created_at
CREATE INDEX idx_failures_created
ON pipeline_failures (criado_em DESC);

-- FINDING_010: pipeline_run_spans.fase_nome
CREATE INDEX idx_spans_tenant_fase
ON pipeline_run_spans (tenant_id, started_at, fase_nome);
```

### Script 2/2 - Indices MEDIUM

```sql
-- FINDING_011: interacoes.direcao
CREATE INDEX idx_interacoes_direcao
ON interacoes (direcao, criado_em DESC)
WHERE direcao IS NOT NULL;

-- FINDING_012: leads.segmento
CREATE INDEX idx_leads_user_segmento
ON leads (user_id, segmento)
WHERE segmento IS NOT NULL AND segmento != '';

-- FINDING_013: leads.cidade
CREATE INDEX idx_leads_user_cidade
ON leads (user_id, cidade)
WHERE cidade IS NOT NULL AND cidade != '';

-- FINDING_015: users.tenant_id
CREATE INDEX idx_users_tenant_id
ON users (tenant_id)
WHERE tenant_id IS NOT NULL;

-- FINDING_016: mercadopago_events.user_id
CREATE INDEX idx_mercadopago_events_user
ON mercadopago_events (user_id, criado_em DESC);

-- FINDING_017: pipeline_run_spans.agente
CREATE INDEX idx_spans_agente
ON pipeline_run_spans (agente, tenant_id, started_at DESC);

-- FINDING_018: pipeline_token_usage
CREATE INDEX idx_token_usage_tenant_run
ON pipeline_token_usage (tenant_id, run_id);
```

---

## Impacto Estimado

| Finding | Prioridade | Reducao Aproximada |
|---|---|---|
| FINDING_001 leads.criado_em | CRITICA | 90-95% tempo de query |
| FINDING_002 interacoes.lead_id | CRITICA | 85-98% tempo de JOIN |
| FINDING_003 ciclos.user_id | HIGH | 70-85% tempo de query |
| FINDING_004 JOIN textual lead_nome | CRITICA | 99% tempo de query (minutos -> ms) |
| FINDING_005-010 | HIGH | 60-80% tempo de query |
| FINDING_011-018 | MEDIUM | 40-70% tempo de query |

---

## Acoes Recomendadas (Ordem de Prioridade)

1. **IMEDIATO (1 dia)**: Criar indices do Script 1/2 (Criticos + HIGH)
2. **URGENTE (3 dias)**: Corrigir JOIN textual `interacoes.lead_nome = leads.nome` — migrar para `lead_id`
3. **PROXIMOS 7 DIAS**: Criar indices do Script 2/2 (MEDIUM)
4. **MONITORAMENTO**: Apos aplicar indices, rodar `EXPLAIN ANALYZE` nas queries afetadas para validar melhoria

---

## Metodo de Auditoria

- Leitura de todos os arquivos de migracao (`alembic/versions/*.py`)
- Leitura completa de `backend/core/database.py`
- Leitura de todas as queries SQL em `backend/endpoints/*.py`
- Leitura de `backend/services/*.py`
- Leitura de `backend/whatsapp_listener.py`
- Cross-reference entre colunas em WHERE/JOIN/ORDER BY/GROUP BY e indices existentes nas migrations

## Arquivos Analisados

```
backend/core/database.py              (tabelas, indices, schema)
backend/endpoints/leads_queries.py   (7 queries analisadas)
backend/endpoints/leads_crud.py      (10+ queries analisadas)
backend/endpoints/pipeline_endpoints.py (ciclos)
backend/endpoints/pipeline_status_endpoints.py (stats aggregation)
backend/endpoints/queue_endpoints.py (jobs e failures)
backend/endpoints/obs_endpoints.py   (pipeline_run_spans aggregation)
backend/endpoints/users_endpoints.py  (interacoes user_id)
backend/services/sdr_gateway.py      (interacoes queries)
backend/whatsapp_listener.py         (interacoes queries)
alembic/versions/*.py                (8 arquivos de migracao)
```
