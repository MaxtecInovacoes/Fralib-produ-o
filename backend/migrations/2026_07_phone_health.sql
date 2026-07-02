-- ============================================================================
-- Migration: phone_health
-- Data: 2026-07
-- Sprint: Trilha A — observabilidade de saúde do número WhatsApp
--
-- Três tabelas:
--   1. rate_limit_counters       — substitui dict in-memory de AntiAbuseGuards
--   2. phone_health_score        — score agregado 0-100 por tenant (atualizado por cron)
--   3. phone_health_events       — log de eventos detectados (erros whatsmeow, DLQ, opt-outs)
--
-- Justificativa: o whatsmeow não entrega Quality Rating da Meta. Sem esta
-- observabilidade, a Fralib não tem como saber que um número foi restringido
-- até o `logged_out` chegar (sinal tardio, sem recurso possível).
-- ============================================================================

-- ============================================================================
-- 1. RATE LIMIT COUNTERS
--    Persiste flood_tracker / daily_count / lead_last_reply / human_pause.
--    Antes vivia em dict Python dentro do processo (perdido em restart).
-- ============================================================================

CREATE TABLE IF NOT EXISTS rate_limit_counters (
  id              BIGSERIAL PRIMARY KEY,
  user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  lead_key        VARCHAR(120) NOT NULL,                -- "{user_id}:{telefone}"
  counter_kind    VARCHAR(32)  NOT NULL,                -- 'flood' | 'daily' | 'cooldown' | 'human_pause'
  counter_value   INTEGER      NOT NULL DEFAULT 0,
  payload         JSONB        NOT NULL DEFAULT '{}'::jsonb,  -- ex.: lista timestamps p/ flood
  expires_at      TIMESTAMPTZ  NOT NULL,                -- TTL; cleanup posterior
  atualizado_em   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_rate_limit_kind
    CHECK (counter_kind IN ('flood', 'daily', 'cooldown', 'human_pause'))
);

-- 1 linha por (user, lead, kind) — UPSERT no app
CREATE UNIQUE INDEX IF NOT EXISTS idx_rate_limit_dedup
  ON rate_limit_counters(user_id, lead_key, counter_kind);

-- Cleanup de expirados (índice leve p/ cron de GC)
CREATE INDEX IF NOT EXISTS idx_rate_limit_expires
  ON rate_limit_counters(expires_at);

-- ============================================================================
-- 2. PHONE HEALTH SCORE
--    Estado atual da saúde do número WhatsApp por tenant.
--    Atualizado por /cron/compute_phone_health_score (1x/hora ou 1x/dia).
--    Lido por /api/superadmin/phone-health e /api/admin/phone-health.
-- ============================================================================

CREATE TABLE IF NOT EXISTS phone_health_score (
  user_id              INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  score                SMALLINT  NOT NULL DEFAULT 100,  -- 0-100
  status               VARCHAR(16) NOT NULL DEFAULT 'healthy',
  signals              JSONB     NOT NULL DEFAULT '{}'::jsonb,  -- detalhe do cálculo
  ultima_restricao_em  TIMESTAMPTZ,
  pause_franz_until    TIMESTAMPTZ,                       -- freio de emergência
  atualizado_em        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_phone_health_score_range
    CHECK (score BETWEEN 0 AND 100),
  CONSTRAINT chk_phone_health_status
    CHECK (status IN ('healthy', 'degraded', 'restricted', 'banned'))
);

CREATE INDEX IF NOT EXISTS idx_phone_health_status
  ON phone_health_score(status, score);

-- ============================================================================
-- 3. PHONE HEALTH EVENTS
--    Log append-only. Cada erro detectado vira 1 linha.
--    Alimentado por sender.py (handler de erros whatsmeow) + crons.
-- ============================================================================

CREATE TABLE IF NOT EXISTS phone_health_events (
  id            BIGSERIAL PRIMARY KEY,
  user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  severity      VARCHAR(16) NOT NULL,                    -- 'info' | 'warn' | 'error' | 'critical'
  event_type    VARCHAR(64) NOT NULL,                    -- 'restricted' | 'banned' | 'rate_limited' | 'dlq' | 'opt_out'
  detail        JSONB     NOT NULL DEFAULT '{}'::jsonb,  -- código de erro, mensagem, contexto
  criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_phone_event_severity
    CHECK (severity IN ('info', 'warn', 'error', 'critical'))
);

CREATE INDEX IF NOT EXISTS idx_phone_events_user_time
  ON phone_health_events(user_id, criado_em DESC);

CREATE INDEX IF NOT EXISTS idx_phone_events_severity_time
  ON phone_health_events(severity, criado_em DESC);

-- ============================================================================
-- 4. SEED INICIAL
--    Para tenants já existentes, cria phone_health_score = 100 (healthy).
--    Roda idempotente.
-- ============================================================================

INSERT INTO phone_health_score (user_id, score, status, signals)
SELECT id, 100, 'healthy', '{"seed": true, "reason": "initial migration"}'::jsonb
FROM users
ON CONFLICT (user_id) DO NOTHING;

-- ============================================================================
-- Trigger para atualizar phone_health_score.atualizado_em
-- ============================================================================

CREATE OR REPLACE FUNCTION trg_phone_health_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.atualizado_em = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_phone_health_updated ON phone_health_score;
CREATE TRIGGER trg_phone_health_updated
  BEFORE UPDATE ON phone_health_score
  FOR EACH ROW
  EXECUTE FUNCTION trg_phone_health_updated_at();