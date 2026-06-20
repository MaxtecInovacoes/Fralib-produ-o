# Fix Report: PERF_002 - Índices Críticos de Performance

## Problema
Múltiplos índices faltantes causando full table scans em queries frequentes.

## Índices Criados

### CRÍTICO: leads.criado_em
```sql
CREATE INDEX CONCURRENTLY idx_leads_user_criado_em ON leads (user_id, criado_em DESC);
CREATE INDEX CONCURRENTLY idx_leads_user_status_criado ON leads (user_id, status, criado_em);
```

### CRÍTICO: interacoes.lead_id
```sql
CREATE INDEX CONCURRENTLY idx_interacoes_lead_id ON interacoes (lead_id);
CREATE INDEX CONCURRENTLY idx_interacoes_lead_user_direcao ON interacoes (lead_id, user_id, direcao, criado_em DESC);
```

### HIGH: ciclos.user_id
```sql
CREATE INDEX CONCURRENTLY idx_ciclos_user_id ON ciclos (user_id, id DESC);
```

### HIGH: sdr_learning.user_id
```sql
CREATE INDEX CONCURRENTLY idx_sdr_learning_user_id ON sdr_learning (user_id, criado_em DESC);
```

### MEDIUM: leads.segmento, leads.cidade, interacoes.direcao
```sql
CREATE INDEX idx_leads_user_segmento ON leads (user_id, segmento);
CREATE INDEX idx_leads_user_cidade ON leads (user_id, cidade);
CREATE INDEX idx_interacoes_direcao ON interacoes (direcao, criado_em DESC);
```

## Arquivo de Migração
`alembic/versions/perf_idx_2025_01_15.py`

## Métricas Estimadas
| Query | Antes | Depois | Melhoria |
|-------|-------|--------|----------|
| ORDER BY criado_em | ~500ms | <5ms | 99% |
| JOIN interacoes | ~2000ms | <20ms | 99% |
| Query ciclos | ~100ms | <10ms | 90% |

## Status
✅ CORRIGIDO - Migração criada
