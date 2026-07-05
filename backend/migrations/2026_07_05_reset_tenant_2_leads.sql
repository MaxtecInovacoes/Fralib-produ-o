-- ============================================================================
-- Migration: 2026_07_05_reset_tenant_2_leads
--
-- OBJETIVO: Resetar leads do tenant 2 para estado "como se nunca tivessem
-- passado pelo pipeline", mantendo apenas os dados que vieram do Caio
-- (qualificacao inicial): nome, telefone, whatsapp, segmento, cidade,
-- rating, score, tier, dados_completos (JSONB do Caio), user_id, criado_em.
--
-- DELETA: tudo que veio DEPOIS do Caio:
--   - site_url / url_site (URL do site gerado)
--   - html_gerado (HTML cacheado)
--   - dados_completos: esvaziar (manter {} mas sem payload do pipeline)
--   - sdr_stage (volta para pendente_wpp pra cron pegar)
--   - status='pendente', processado=FALSE, tentativas=0, ciclo=0
--   - observacoes (era anotacao de etapas anteriores)
--   - valor_venda (era venda concluida)
--   - atualizado_em (volta pra NOW() - representa reset)
--
-- IDEMPOTENTE: pode rodar varias vezes sem efeito colateral.
-- ESCOPO: APENAS tenant 2 (user_id=2). Outros tenants NAO sao afetados.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. TABELA leads: resetar campos do pipeline, manter dados do Caio
-- ============================================================================
UPDATE leads
SET
    -- LIMPAR tudo do pipeline/site/SDR
    site_url = NULL,
    url_site = NULL,
    html_gerado = NULL,
    sdr_stage = 'pendente_wpp',
    status = 'pendente',
    processado = FALSE,
    tentativas = 0,
    ciclo = 0,
    observacoes = NULL,
    valor_venda = 0,
    -- dados_completos: preservar chaves que vieram do Caio, remover o resto
    dados_completos = COALESCE(
        dados_completos,
        '{}'::jsonb
    ) - 'site_gerado' - 'pipeline_logs' - 'sdr_historico' - 'ultima_abordagem',
    -- timestamp de reset
    atualizado_em = NOW()
WHERE user_id = 2;

-- ============================================================================
-- 2. DELETAR tabelas relacionadas ao pipeline/SDR para o tenant 2
-- ============================================================================

-- 2.1 Historico de mensagens (inbound + outbound)
DELETE FROM interacoes WHERE user_id = 2;

-- 2.2 Fila de envio (pendente ou sent, tudo)
DELETE FROM outbound_queue WHERE tenant_id = 2;

-- 2.3 Auditoria de turnos SDR
DELETE FROM sdr_turns WHERE tenant_id = 2;

-- 2.4 Aprendizado do Franz
DELETE FROM sdr_learning WHERE user_id = 2;

-- 2.5 Falhas do pipeline
DELETE FROM pipeline_failures WHERE tenant_id = 2;

-- 2.6 Traces do pipeline
DELETE FROM pipeline_traces WHERE tenant_id = 2;

-- 2.7 Token usage (cache de custo por tenant)
DELETE FROM pipeline_token_usage WHERE tenant_id = 2;

-- ============================================================================
-- 3. Caches de DB do tenant 2
-- ============================================================================

-- 3.1 Cache de leads (resultados do hunter)
DELETE FROM leads_cache WHERE user_id = 2;

-- 3.2 Cache de keywords (pesquisa, tabela global - limpa tudo do tenant 2
-- via join, ou tudo se nao houver user_id)
-- Se keyword_cache tem user_id:
DELETE FROM keyword_cache WHERE user_id = 2;
-- Fallback: se nao tem user_id, o script wrapper fara cleanup manual

-- ============================================================================
-- 4. Audit log desta operacao (para reversao futura)
-- ============================================================================
INSERT INTO audit_events (
    event_type,
    actor,
    payload,
    criado_em
) VALUES (
    'reset_tenant_2_leads',
    'system:cleanup_migration',
    jsonb_build_object(
        'migration', '2026_07_05_reset_tenant_2_leads',
        'reset_leads_count', (SELECT COUNT(*) FROM leads WHERE user_id = 2),
        'deleted_interacoes', (SELECT COUNT(*) FROM interacoes WHERE user_id = 2),
        'deleted_outbound', (SELECT COUNT(*) FROM outbound_queue WHERE tenant_id = 2),
        'deleted_sdr_turns', (SELECT COUNT(*) FROM sdr_turns WHERE tenant_id = 2),
        'deleted_sdr_learning', (SELECT COUNT(*) FROM sdr_learning WHERE user_id = 2),
        'deleted_pipeline_failures', (SELECT COUNT(*) FROM pipeline_failures WHERE tenant_id = 2),
        'deleted_pipeline_traces', (SELECT COUNT(*) FROM pipeline_traces WHERE tenant_id = 2),
        'deleted_pipeline_token_usage', (SELECT COUNT(*) FROM pipeline_token_usage WHERE tenant_id = 2),
        'deleted_leads_cache', (SELECT COUNT(*) FROM leads_cache WHERE user_id = 2),
        'deleted_keyword_cache', (SELECT COUNT(*) FROM keyword_cache WHERE user_id = 2)
    ),
    NOW()
);

COMMIT;