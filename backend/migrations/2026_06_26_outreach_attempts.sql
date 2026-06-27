-- ============================================================================
-- Migration: outreach_attempts
-- Data: 2026-06-26
-- Sprint: 14.3 — Campanha de reativação de clientes inativos
--
-- Tabela para tracking de campanhas de outreach (email + whatsapp).
-- UNIQUE INDEX (user_id, campaign, channel) garante idempotência:
-- o mesmo user nunca recebe a mesma campanha duas vezes no mesmo canal.
-- ============================================================================

CREATE TABLE IF NOT EXISTS outreach_attempts (
  id              SERIAL PRIMARY KEY,
  user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  campaign        VARCHAR(64) NOT NULL,
  channel         VARCHAR(16) NOT NULL,
  status          VARCHAR(20) NOT NULL DEFAULT 'pending',
  provider_msg_id TEXT,
  sent_at         TIMESTAMPTZ,
  delivered_at    TIMESTAMPTZ,
  opened_at       TIMESTAMPTZ,
  clicked_at      TIMESTAMPTZ,
  replied_at      TIMESTAMPTZ,
  bounce_reason   TEXT,
  error_message   TEXT,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_outreach_channel
    CHECK (channel IN ('email', 'whatsapp', 'sms')),
  CONSTRAINT chk_outreach_status
    CHECK (status IN ('pending', 'sent', 'delivered', 'opened', 'clicked', 'replied', 'bounced', 'failed', 'unsubscribed'))
);

CREATE INDEX IF NOT EXISTS idx_outreach_user_id ON outreach_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_outreach_campaign ON outreach_attempts(campaign);
CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach_attempts(status);
CREATE INDEX IF NOT EXISTS idx_outreach_criado ON outreach_attempts(criado_em DESC);

-- Idempotência: 1 user só recebe 1 vez por campanha+canal
CREATE UNIQUE INDEX IF NOT EXISTS idx_outreach_dedup
  ON outreach_attempts(user_id, campaign, channel);

-- Trigger para atualizar atualizado_em
CREATE OR REPLACE FUNCTION trg_outreach_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.atualizado_em = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_outreach_updated ON outreach_attempts;
CREATE TRIGGER trg_outreach_updated
  BEFORE UPDATE ON outreach_attempts
  FOR EACH ROW
  EXECUTE FUNCTION trg_outreach_updated_at();