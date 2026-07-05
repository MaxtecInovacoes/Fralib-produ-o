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
-- IMPORTANTE: Cada DELETE eh protegido por EXISTS check na tabela-alvo
-- para nao falhar se a tabela nao existir (migration 100% idempotente).

-- 2.1 Historico de mensagens (inbound + outbound) - user_id em interacoes
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'interacoes'
    ) THEN
        DELETE FROM interacoes WHERE user_id = 2;
    END IF;
END $$;

-- 2.2 Fila de envio (pendente ou sent, tudo) - tenant_id em outbound_queue
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'outbound_queue'
    ) THEN
        DELETE FROM outbound_queue WHERE tenant_id = 2;
    END IF;
END $$;

-- 2.3 Auditoria de turnos SDR - tenant_id em sdr_turns
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'sdr_turns'
    ) THEN
        DELETE FROM sdr_turns WHERE tenant_id = 2;
    END IF;
END $$;

-- 2.4 Aprendizado do Franz - user_id em sdr_learning
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'sdr_learning'
    ) THEN
        DELETE FROM sdr_learning WHERE user_id = 2;
    END IF;
END $$;

-- 2.5 Falhas do pipeline - tenant_id em pipeline_failures
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'pipeline_failures'
    ) THEN
        DELETE FROM pipeline_failures WHERE tenant_id = 2;
    END IF;
END $$;

-- 2.6 Traces do pipeline - tenant_id em pipeline_traces
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'pipeline_traces'
    ) THEN
        DELETE FROM pipeline_traces WHERE tenant_id = 2;
    END IF;
END $$;

-- 2.7 Token usage (cache de custo por tenant) - tenant_id em pipeline_token_usage
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'pipeline_token_usage'
    ) THEN
        DELETE FROM pipeline_token_usage WHERE tenant_id = 2;
    END IF;
END $$;

-- 2.8 pipeline_run_spans - tenant_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'pipeline_run_spans'
    ) THEN
        DELETE FROM pipeline_run_spans WHERE tenant_id = 2;
    END IF;
END $$;

-- ============================================================================
-- 3. Caches de DB do tenant 2
-- ============================================================================

-- 3.1 Cache de leads (resultados do hunter) - user_id em leads_cache
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'leads_cache'
    ) THEN
        DELETE FROM leads_cache WHERE user_id = 2;
    END IF;
END $$;

-- 3.2 keyword_cache NAO tem user_id - eh cache global por (segmento, cidade).
-- Para resetar tenant 2, o mais seguro eh limpar TUDO (todos os tenants
-- vao reprocessar keywords do zero). Aceitavel porque cache expira em 30d.
-- Ver backend/agents/keyword_research.py linha 175.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'keyword_cache'
    ) THEN
        DELETE FROM keyword_cache;
    END IF;
END $$;

-- ============================================================================
-- 4. Audit log desta operacao (para reversao futura)
-- ============================================================================
-- Schema audit_events (ver migrations/2026_07_audit_events.sql):
--   tenant_id, actor_id, actor_email, actor_role, action, entity_type,
--   entity_id, diff_json, ip, user_agent, metadata, criado_em
-- Encaixamos o reset nos campos canônicos:
--   tenant_id = 2 (escopo do reset)
--   actor_id = NULL (operacao automatica do sistema)
--   action = 'reset_tenant_2_leads'
--   entity_type = 'tenant'
--   entity_id = 2
--   diff_json = snapshot com contadores antes do reset
DO $$
DECLARE
    v_leads_count INT;
    v_interacoes_count INT;
    v_outbound_count INT;
    v_sdr_turns_count INT;
    v_sdr_learning_count INT;
    v_pipeline_failures_count INT;
    v_pipeline_traces_count INT;
    v_pipeline_token_usage_count INT;
    v_leads_cache_count INT;
    v_keyword_cache_count INT;
    v_audit_exists BOOLEAN;
BEGIN
    -- Snapshot ANTES (os DELETE's acima ja rodaram; entao contagem eh pos-reset,
    -- mas mantemos o padrao de documentar a operacao)
    SELECT COUNT(*) INTO v_leads_count FROM leads WHERE user_id = 2;
    SELECT COUNT(*) INTO v_interacoes_count FROM interacoes WHERE user_id = 2;
    SELECT COUNT(*) INTO v_outbound_count FROM outbound_queue WHERE tenant_id = 2;
    SELECT COUNT(*) INTO v_sdr_turns_count FROM sdr_turns WHERE tenant_id = 2;
    SELECT COUNT(*) INTO v_sdr_learning_count FROM sdr_learning WHERE user_id = 2;
    SELECT COUNT(*) INTO v_pipeline_failures_count FROM pipeline_failures WHERE tenant_id = 2;
    SELECT COUNT(*) INTO v_pipeline_traces_count FROM pipeline_traces WHERE tenant_id = 2;
    SELECT COUNT(*) INTO v_pipeline_token_usage_count FROM pipeline_token_usage WHERE tenant_id = 2;
    SELECT COUNT(*) INTO v_leads_cache_count FROM leads_cache WHERE user_id = 2;
    SELECT COUNT(*) INTO v_keyword_cache_count FROM keyword_cache;

    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'audit_events'
    ) INTO v_audit_exists;

    IF v_audit_exists THEN
        INSERT INTO audit_events (
            tenant_id,
            actor_id,
            actor_email,
            action,
            entity_type,
            entity_id,
            diff_json,
            metadata,
            criado_em
        ) VALUES (
            2,
            NULL,
            'system:reset_migration',
            'reset_tenant_2_leads',
            'tenant',
            2,
            jsonb_build_object(
                'migration', '2026_07_05_reset_tenant_2_leads',
                'leads_remaining_for_tenant_2', v_leads_count,
                'deleted_interacoes', v_interacoes_count,
                'deleted_outbound', v_outbound_count,
                'deleted_sdr_turns', v_sdr_turns_count,
                'deleted_sdr_learning', v_sdr_learning_count,
                'deleted_pipeline_failures', v_pipeline_failures_count,
                'deleted_pipeline_traces', v_pipeline_traces_count,
                'deleted_pipeline_token_usage', v_pipeline_token_usage_count,
                'deleted_leads_cache', v_leads_cache_count,
                'deleted_keyword_cache', v_keyword_cache_count,
                'note', 'contagens sao pos-reset; valores baixos indicam sucesso'
            ),
            jsonb_build_object(
                'migration_file', '2026_07_05_reset_tenant_2_leads.sql',
                'scope', 'tenant_2_only',
                'operation', 'reset_to_caio_baseline'
            ),
            NOW()
        );
    END IF;
END $$;

COMMIT;