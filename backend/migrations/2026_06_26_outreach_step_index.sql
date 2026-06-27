-- ============================================================================
-- Migration: indice GIN em outreach_attempts.metadata->>'step'
-- Data: 2026-06-26
-- Sprint: 14.4 — Drip campaign
--
-- Query do cron drip-diario faz: WHERE metadata->>'step'='N'
-- Sem indice, faz seq scan na tabela. Indice GIN parcial resolve.
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_outreach_meta_step
  ON outreach_attempts ((metadata->>'step'))
  WHERE metadata->>'step' IS NOT NULL;