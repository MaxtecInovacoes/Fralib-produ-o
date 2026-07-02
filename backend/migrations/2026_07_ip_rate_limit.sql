-- ============================================================================
-- Migration: ip_rate_limit
-- Data: 2026-07-02
-- Sprint: 3.1 — Rate Limit por IP (HTTP)
--
-- Tabela ip_rate_limit: fallback Postgres quando Redis estiver offline.
-- O caminho primário é Redis (sliding window via INCR + EXPIRE). Esta tabela
-- é o degradar gracioso: se Redis cair, o middleware continua protegendo
-- endpoints públicos contra brute-force / flood usando UPSERT por janela.
--
-- Justificativa: a Sprint 2.0 entregou rate limit por lead_key (WhatsApp),
-- mas audit confirmou que /api/auth/login, /api/cron/*, /api/public/* e
-- /api/admin/health NÃO tinham rate limit por IP em HTTP. Esta migration
-- destrava a Sprint 3.1.
-- ============================================================================

CREATE TABLE IF NOT EXISTS ip_rate_limit (
  id              BIGSERIAL PRIMARY KEY,
  ip              INET NOT NULL,
  endpoint_bucket VARCHAR(60) NOT NULL,                 -- 'auth.login', 'cron.refresh-provider-health', 'public.*', 'default'
  window_start    TIMESTAMP NOT NULL,                    -- início da janela (segundos-truncados)
  count           INTEGER   NOT NULL DEFAULT 1,
  criado_em       TIMESTAMP NOT NULL DEFAULT NOW(),

  -- 1 linha por (ip, bucket, janela). Permite UPSERT atômico (ON CONFLICT ... DO UPDATE).
  CONSTRAINT uq_ip_rate_limit_window
    UNIQUE (ip, endpoint_bucket, window_start)
);

-- Índice composto para consulta de janela: "quantos hits esse IP teve neste bucket
-- nos últimos N segundos?". Otimiza a query de fallback do IPRateLimiter.
CREATE INDEX IF NOT EXISTS idx_ip_rate_limit_lookup
  ON ip_rate_limit (ip, endpoint_bucket, criado_em DESC);

-- Índice secundário para GC futuro: limpar janelas com mais de X horas.
CREATE INDEX IF NOT EXISTS idx_ip_rate_limit_window_start
  ON ip_rate_limit (window_start);

COMMENT ON TABLE ip_rate_limit IS
  'Fallback Postgres para rate limit HTTP por IP (Sprint 3.1). Caminho primário é Redis.';
COMMENT ON COLUMN ip_rate_limit.endpoint_bucket IS
  'Bucket do endpoint — auth.login | cron.* | public.* | default. Whitelist não chega nesta tabela.';
