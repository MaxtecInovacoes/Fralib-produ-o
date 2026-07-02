-- ============================================================================
-- Migration: lead_outcomes + sdr_kpi_aggregated
-- Data: 2026-07
-- Sprint: 1.4 — Orquestração de KPIs entre Agentes
--
-- Duas tabelas:
--   1. lead_outcomes           — INSERT por lead quando stage vira ganho/perdido
--   2. sdr_kpi_aggregated      — agregado por nicho (calculado por cron diário)
--
-- Justificativa: para o SDR Franz aprender automaticamente qual nicho
-- converte mais em qual horário / abordagem / template, precisamos persistir
-- o "resultado final" de cada lead e agregar por nicho.
-- ============================================================================

-- ============================================================================
-- 1. LEAD_OUTCOMES
--    1 linha por lead quando ele termina (ganhou ou perdeu). Inserido pelo
--    hook no SDR agent quando sdr_stage muda para 'ganho' ou 'perdido'.
-- ============================================================================

CREATE TABLE IF NOT EXISTS lead_outcomes (
  id                     BIGSERIAL PRIMARY KEY,
  lead_id                INTEGER NOT NULL,
  tenant_id              INTEGER NOT NULL,
  nicho                  VARCHAR(80),
  horario_contato        TIME,
  abordagem_usada        VARCHAR(80),
  site_template_usado    VARCHAR(80),
  kanban_stage_final     VARCHAR(40),
  dias_ate_fechamento    INTEGER,
  criado_em              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lead_outcomes_tenant_nicho
  ON lead_outcomes(tenant_id, nicho);

CREATE INDEX IF NOT EXISTS idx_lead_outcomes_criado_em
  ON lead_outcomes(criado_em DESC);

CREATE INDEX IF NOT EXISTS idx_lead_outcomes_stage
  ON lead_outcomes(kanban_stage_final);


-- ============================================================================
-- 2. SDR_KPI_AGGREGATED
--    Agregado por nicho + período (30d, 7d, all). Recalculado por
--    backend/jobs/aggregate_sdr_kpis.py diariamente.
--    metricas aceitas: 'taxa_conversao' | 'horario_melhor' | 'abordagem_melhor'
--    | 'site_template_melhor'.
-- ============================================================================

CREATE TABLE IF NOT EXISTS sdr_kpi_aggregated (
  id              BIGSERIAL PRIMARY KEY,
  nicho           VARCHAR(80) NOT NULL,
  metrica         VARCHAR(80) NOT NULL,
  valor           TEXT NOT NULL,
  periodo         VARCHAR(20),
  sample_size     INTEGER,
  atualizado_em   TIMESTAMP DEFAULT NOW()
);

-- 1 linha por (nicho, metrica, periodo) — UPSERT no app
CREATE UNIQUE INDEX IF NOT EXISTS idx_sdr_kpi_dedup
  ON sdr_kpi_aggregated(nicho, metrica, periodo);

-- Query pattern: top nichos por conversao, ultimas 30d
CREATE INDEX IF NOT EXISTS idx_sdr_kpi_nicho_periodo
  ON sdr_kpi_aggregated(nicho, periodo);
