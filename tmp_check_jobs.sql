SELECT id, tipo, status, tenant_id, 
       payload->>'_lead_id_existente' as lead_id,
       payload->>'segmento' as segmento,
       payload->>'cidade' as cidade,
       created_at, updated_at, attempts, max_attempts
FROM jobs
WHERE id >= 406490
ORDER BY id;
