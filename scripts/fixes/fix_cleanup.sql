-- 1) Limpar jobs failed_permanent repetidos do mesmo lead (sao lixo do loop)
DELETE FROM jobs 
WHERE tipo = 'pipeline_lead' 
  AND status = 'failed_permanent'
  AND payload::jsonb->>'_lead_id_existente' = '6ee318c7-bdf9-454a-b206-b90a90e45ec0';

-- 2) Liberar leads reservados travados (locked_until expirado)
UPDATE lead_inventory 
SET status = 'raw', locked_by = NULL, locked_until = NULL, atualizado_em = NOW()
WHERE status = 'reserved' 
  AND locked_until < NOW() - INTERVAL '2 hours';

-- 3) Aumentar max_attempts dos pending de 3 para 5
UPDATE jobs 
SET max_attempts = 5, attempts = LEAST(attempts, 4)
WHERE tipo = 'pipeline_lead' AND status = 'pending' AND max_attempts <= 3;

-- 4) Liberar error_retry travados (bloquear novo retry para nao loop)
UPDATE lead_inventory 
SET status = 'discarded', atualizado_em = NOW(), erro = 'Bloqueado para revisao manual - erro repetido'
WHERE status = 'error_retry' AND attempts >= 3;

-- 5) Verificar resultado
SELECT 'jobs_apos_limpeza' as item, COUNT(*)::text as total FROM jobs
UNION ALL SELECT 'pending', COUNT(*)::text FROM jobs WHERE status='pending'
UNION ALL SELECT 'running', COUNT(*)::text FROM jobs WHERE status='running'
UNION ALL SELECT 'inventory_status', COUNT(*)::text FROM lead_inventory GROUP BY status ORDER BY status;
