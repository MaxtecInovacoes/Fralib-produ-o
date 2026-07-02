-- ============================================================================
-- Migration: tenant_alerts (Sprint 3.3 — Alerta de Tenant Silencioso)
-- Data: 2026-07
--
-- Tabela para alertas de saúde/uso por tenant.
-- Critérios atuais:
--   1. admin_inactive_7d       — admin sem login > 7 dias
--   2. no_new_leads_15d        — sem leads novos > 15d
--   3. no_cost_events_3d       — tenant ativo sem evento de custo > 3d
--   4. subscription_expiring_7d — plano vence em <= 7d
--   5. trial_active_no_use_14d — trial > 14d sem login
--
-- Severities: info | warning | critical
-- Status: open | acknowledged | resolved
--
-- Partial unique: impede múltiplas linhas abertas para o mesmo (tenant_id, alert_type)
-- Uma vez acknowledged/resolved, é permitido criar nova ocorrência.
-- ============================================================================

CREATE TABLE IF NOT EXISTS tenant_alerts (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL,
    alert_type      VARCHAR(40) NOT NULL,
    severity        VARCHAR(20) NOT NULL,
    detail          JSONB DEFAULT '{}'::jsonb,
    status          VARCHAR(20) DEFAULT 'open',
    acknowledged_by INTEGER,
    acknowledged_at TIMESTAMP,
    resolved_at     TIMESTAMP,
    criado_em       TIMESTAMP DEFAULT NOW(),
    atualizado_em   TIMESTAMP DEFAULT NOW()
);

-- Partial unique: impede múltiplas linhas OPEN para o mesmo (tenant_id, alert_type).
CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_alerts_open
    ON tenant_alerts (tenant_id, alert_type)
    WHERE status = 'open';

-- Index operacional: listagem filtrada por status+severity ordem cronológica.
CREATE INDEX IF NOT EXISTS idx_tenant_alerts_status_severity_time
    ON tenant_alerts (status, severity, criado_em DESC);

-- Lookup rápido por tenant.
CREATE INDEX IF NOT EXISTS idx_tenant_alerts_tenant
    ON tenant_alerts (tenant_id, criado_em DESC);