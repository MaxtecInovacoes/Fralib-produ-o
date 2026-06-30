-- ============================================================
-- VERIFICAR FILA DE WHATSAPP
-- Execute no pgAdmin para ver leads pendentes
-- ============================================================

-- 1. Total de leads pendentes WhatsApp
SELECT COUNT(*) as total_pendentes_wpp
FROM leads
WHERE sdr_stage = 'pendente_wpp'
  AND status = 'concluido'
  AND site_url IS NOT NULL;

-- 2. Detalhado por tenant
SELECT
    u.email as tenant_email,
    u.plano,
    COUNT(*) as total_leads,
    COUNT(*) FILTER (WHERE l.whatsapp IS NOT NULL AND l.whatsapp != '') as com_whatsapp,
    COUNT(*) FILTER (WHERE l.whatsapp IS NULL OR l.whatsapp = '') as sem_whatsapp
FROM leads l
JOIN users u ON u.id = l.user_id
WHERE l.sdr_stage = 'pendente_wpp'
  AND l.status = 'concluido'
  AND l.site_url IS NOT NULL
GROUP BY u.email, u.plano
ORDER BY total_leads DESC;

-- 3. Leads com bug pending_sdr_send (precisam de correção)
SELECT COUNT(*) as pending_sdr_send_count
FROM leads
WHERE sdr_stage = 'pending_sdr_send'
  AND status = 'concluido';

-- 4. Todos os leads por stage
SELECT
    sdr_stage,
    status,
    COUNT(*) as total
FROM leads
WHERE status = 'concluido'
GROUP BY sdr_stage, status
ORDER BY sdr_stage;
