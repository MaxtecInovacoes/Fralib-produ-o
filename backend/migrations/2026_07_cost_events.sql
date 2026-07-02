-- ============================================================================
-- Migration: cost_events
-- Data: 2026-07
-- Sprint: 0.3 — Dashboard de Custos (Fase 0)
--
-- Tabela única `cost_events` para custo unificado multi-provider:
--   - 1 linha por chamada/evento de custo (LLM, FB Ads, Jina, Hunter, Maps, etc.)
--   - instrumentada via `record_cost_event(...)` em backend/agents/cost_tracker.py
--   - failed-friendly: cron diário agrega spend Facebook Ads via API
--
-- Resolve: bug #9 (llm_router sem tracking) + bug #10 (Jina sem custo).
-- ============================================================================

CREATE TABLE IF NOT EXISTS cost_events (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           INTEGER,
    user_id             INTEGER,
    job_id              INTEGER,
    provider            VARCHAR(50)  NOT NULL,
    model               VARCHAR(100),
    service             VARCHAR(80),
    input_tokens        INTEGER      DEFAULT 0,
    output_tokens       INTEGER      DEFAULT 0,
    cache_read_tokens   INTEGER      DEFAULT 0,
    units               INTEGER      DEFAULT 1,
    latency_ms          INTEGER,
    custo_usd           NUMERIC(12,6) DEFAULT 0,
    custo_brl           NUMERIC(14,4),
    cotacao_usd_brl     NUMERIC(8,4)  DEFAULT 5.65,
    status              VARCHAR(30)   DEFAULT 'success',
    error_message       TEXT,
    metadata            JSONB         DEFAULT '{}'::jsonb,
    criado_em           TIMESTAMP     DEFAULT NOW()
);

-- Lookup rápido por tenant + janela de tempo
CREATE INDEX IF NOT EXISTS idx_cost_events_tenant_time
    ON cost_events (tenant_id, criado_em DESC);

-- Lookup rápido por provider + janela de tempo
CREATE INDEX IF NOT EXISTS idx_cost_events_provider_time
    ON cost_events (provider, criado_em DESC);

-- GIN index no metadata JSONB (auditoria estruturada)
CREATE INDEX IF NOT EXISTS idx_cost_events_metadata_gin
    ON cost_events USING GIN (metadata);

-- ============================================================================
-- VIEW: v_cost_events_by_provider
-- Agrega custo diário por provider (últimos 30 dias).
-- ============================================================================

CREATE OR REPLACE VIEW v_cost_events_by_provider AS
SELECT
    provider,
    DATE(criado_em) AS dia,
    COUNT(*)        AS total_eventos,
    COALESCE(SUM(custo_usd), 0)   AS total_usd,
    COALESCE(SUM(custo_brl), 0)   AS total_brl,
    COALESCE(SUM(input_tokens), 0)  AS total_input_tokens,
    COALESCE(SUM(output_tokens), 0) AS total_output_tokens
FROM cost_events
WHERE criado_em >= NOW() - INTERVAL '30 days'
GROUP BY provider, DATE(criado_em);

-- ============================================================================
-- VIEW: v_cost_events_by_tenant
-- Custo diário por tenant (últimos 30 dias).
-- ============================================================================

CREATE OR REPLACE VIEW v_cost_events_by_tenant AS
SELECT
    COALESCE(tenant_id, 0) AS tenant_id,
    DATE(criado_em)        AS dia,
    COUNT(*)               AS total_eventos,
    COALESCE(SUM(custo_usd), 0) AS total_usd,
    COALESCE(SUM(custo_brl), 0) AS total_brl
FROM cost_events
WHERE criado_em >= NOW() - INTERVAL '30 days'
GROUP BY tenant_id, DATE(criado_em);
