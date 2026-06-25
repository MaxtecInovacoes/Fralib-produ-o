-- JOBS por tenant
SELECT tenant_id, status, COUNT(*) AS total,
       MIN(criado_em) AS mais_antigo,
       MAX(atualizado_em) AS mais_recente
FROM jobs
WHERE tenant_id IN (2, 31)
GROUP BY tenant_id, status
ORDER BY tenant_id, status;

-- JOBS pendentes/running detalhados (tenant 2)
SELECT id, tenant_id, tipo, status, attempts, criado_em, next_retry_at, last_phase
FROM jobs
WHERE tenant_id = 2
  AND status IN ('pending', 'running', 'failed_retriable')
ORDER BY criado_em ASC;

-- JOBS pendentes/running detalhados (tenant 31)
SELECT id, tenant_id, tipo, status, attempts, criado_em, next_retry_at, last_phase
FROM jobs
WHERE tenant_id = 31
  AND status IN ('pending', 'running', 'failed_retriable')
ORDER BY criado_em ASC;

-- PIPELINE_QUEUE por user_id
SELECT user_id, status, COUNT(*) AS total
FROM pipeline_queue
WHERE user_id IN (2, 31)
GROUP BY user_id, status
ORDER BY user_id, status;

-- PIPELINE_EXECUTIONS rodando
SELECT id, user_id, lead_nome, status, started_at
FROM pipeline_executions
WHERE user_id IN (2, 31)
  AND status = 'running'
ORDER BY started_at ASC;

-- PIPELINE_EXECUTIONS últimas 24h
SELECT user_id, status, COUNT(*) AS total
FROM pipeline_executions
WHERE user_id IN (2, 31)
  AND started_at >= NOW() - INTERVAL '24 hours'
GROUP BY user_id, status
ORDER BY user_id, status;