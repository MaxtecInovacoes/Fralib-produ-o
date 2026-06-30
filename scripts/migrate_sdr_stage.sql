-- ============================================================
-- MIGRATION: Fix SDR Stage Bug
-- pending_sdr_send -> pendente_wpp
-- ============================================================
-- Execute this in pgAdmin or psql
-- ============================================================

-- 1. VER ANTES
-- Contagem de leads por estágio antes da migração
SELECT
    sdr_stage,
    COUNT(*) as total
FROM leads
WHERE status = 'concluido'
GROUP BY sdr_stage
ORDER BY sdr_stage;

-- 2. VER TOTAL PARA MIGRAR
SELECT COUNT(*) as pending_sdr_send_count
FROM leads
WHERE status = 'concluido'
  AND sdr_stage = 'pending_sdr_send';

-- 3. EXECUTAR MIGRAÇÃO (descomente para executar)
-- UPDATE leads
-- SET sdr_stage = 'pendente_wpp',
--     atualizado_em = NOW()::text
-- WHERE status = 'concluido'
--   AND sdr_stage = 'pending_sdr_send';

-- 4. VER DEPOIS
-- Contagem após migração
SELECT
    sdr_stage,
    COUNT(*) as total
FROM leads
WHERE status = 'concluido'
GROUP BY sdr_stage
ORDER BY sdr_stage;

-- ============================================================
-- VERIFICAR POR TENANT (opcional)
-- ============================================================
SELECT
    user_id as tenant_id,
    COUNT(*) FILTER (WHERE sdr_stage = 'pending_sdr_send') as pending_sdr_send,
    COUNT(*) FILTER (WHERE sdr_stage = 'pendente_wpp') as pendente_wpp,
    COUNT(*) FILTER (WHERE sdr_stage = 'hook') as hook,
    COUNT(*) FILTER (WHERE sdr_stage = 'intro') as intro,
    COUNT(*) FILTER (WHERE sdr_stage = 'followup1') as followup1,
    COUNT(*) FILTER (WHERE sdr_stage = 'followup2') as followup2,
    COUNT(*) FILTER (WHERE sdr_stage = 'sdr_enqueue_failed') as sdr_enqueue_failed
FROM leads
WHERE status = 'concluido'
GROUP BY user_id
ORDER BY user_id;
