-- ============================================================================
-- Migration: provider_health
-- Data: 2026-07
-- Sprint: 0.1 — Painel de Provedores Externos (Fase 0)
--
-- Tabela única `provider_health` + view `v_provider_health_now`:
--   - 1 linha por provider (UPSERT por chave única)
--   - status agregado: healthy | degraded | down | unknown
--   - latência p95 + taxa de sucesso + custo diário em BRL
--   - atualizada por cron refresh-provider-health (5min) e via record_health()
--   - view ordena por severidade (down > degraded > healthy > unknown)
--
-- Resolve: bug #6 (Facebook Ads sem health check) + item 7 do plano
-- original (saúde do meowhats central).
-- ============================================================================

CREATE TABLE IF NOT EXISTS provider_health (
    id              BIGSERIAL PRIMARY KEY,
    provider        VARCHAR(40)  NOT NULL,
    endpoint        VARCHAR(120),
    status          VARCHAR(20)  NOT NULL DEFAULT 'unknown',
    latency_p95_ms  INTEGER,
    success_rate_24h NUMERIC(5,2) DEFAULT 100.00,
    calls_24h       INTEGER      DEFAULT 0,
    errors_24h      INTEGER      DEFAULT 0,
    custo_dia_brl   NUMERIC(14,4) DEFAULT 0,
    last_error      TEXT,
    last_checked_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    metadata_json   JSONB        DEFAULT '{}'::jsonb,
    criado_em       TIMESTAMP    NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMP    NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_provider_health_status
        CHECK (status IN ('healthy', 'degraded', 'down', 'unknown')),
    CONSTRAINT chk_provider_health_provider
        CHECK (provider IN (
            'anthropic','openai','google','groq','facebook_ads',
            'hunter','meowhats','gosom','jina','whatsapp_waba'
        ))
);

-- 1 linha por provider — UPSERT idempotente
CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_health_provider
    ON provider_health (provider);

-- lookup rápido por status (cron alerta amarelo >15min)
CREATE INDEX IF NOT EXISTS idx_provider_health_status
    ON provider_health (status, last_checked_at DESC);

-- ============================================================================
-- VIEW: v_provider_health_now
-- Lista atual ordenada por severidade (down primeiro), com flag
-- "stale" se last_checked_at > 15min atrás (alerta amarelo).
-- ============================================================================

CREATE OR REPLACE VIEW v_provider_health_now AS
SELECT
    ph.id,
    ph.provider,
    ph.endpoint,
    ph.status,
    ph.latency_p95_ms,
    ph.success_rate_24h,
    ph.calls_24h,
    ph.errors_24h,
    ph.custo_dia_brl,
    ph.last_error,
    ph.last_checked_at,
    (ph.last_checked_at < NOW() - INTERVAL '15 minutes') AS is_stale,
    ph.metadata_json,
    ph.atualizado_em,
    CASE ph.status
        WHEN 'down'      THEN 4
        WHEN 'degraded'  THEN 3
        WHEN 'unknown'   THEN 2
        WHEN 'healthy'   THEN 1
        ELSE 0
    END AS severity_rank
FROM provider_health ph
ORDER BY severity_rank DESC, ph.last_checked_at DESC;