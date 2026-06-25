-- ============================================================================
-- Migration: Lead Funnel ponta-a-ponta com UTM tracking
-- Data: 2026-06-25
-- Objetivo: Saber DE ONDE veio cada visitante/cadastro E quanto converteu
-- ============================================================================

CREATE TABLE IF NOT EXISTS lead_funnel (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(64) NOT NULL,
  user_id INTEGER NULL,                    -- FK para users.id quando virar conta
  whatsapp VARCHAR(32) NULL,               -- preenchido quando vira lead
  email VARCHAR(255) NULL,
  nome VARCHAR(255) NULL,

  -- UTM / origem
  utm_source VARCHAR(64) NULL,             -- facebook, instagram, google, direto, whatsapp
  utm_medium VARCHAR(64) NULL,             -- cpc, story, post, email, organic
  utm_campaign VARCHAR(128) NULL,          -- nome da campanha
  utm_content VARCHAR(128) NULL,
  referer TEXT NULL,
  landing_path VARCHAR(255) NULL,          -- /landing.html, /landing2.html, /admin, etc

  -- Funil: cada etapa registra timestamp + bool
  etapa_atual VARCHAR(32) NOT NULL,        -- visit | cta_clicked | login_start | signup_done | whatsapp_joined | first_action
  entrou_landing TIMESTAMP NULL,
  clicou_cta TIMESTAMP NULL,
  iniciou_login TIMESTAMP NULL,
  criou_conta TIMESTAMP NULL,
  entrou_grupo_whatsapp TIMESTAMP NULL,
  primeira_acao_app TIMESTAMP NULL,

  -- Metadata
  ip_hash VARCHAR(32) NULL,
  ua_hash VARCHAR(32) NULL,
  user_agent TEXT NULL,
  criado_em TIMESTAMP DEFAULT NOW(),
  atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lead_funnel_session ON lead_funnel(session_id);
CREATE INDEX IF NOT EXISTS idx_lead_funnel_user ON lead_funnel(user_id);
CREATE INDEX IF NOT EXISTS idx_lead_funnel_whatsapp ON lead_funnel(whatsapp);
CREATE INDEX IF NOT EXISTS idx_lead_funnel_utm_source ON lead_funnel(utm_source);
CREATE INDEX IF NOT EXISTS idx_lead_funnel_etapa ON lead_funnel(etapa_atual);
CREATE INDEX IF NOT EXISTS idx_lead_funnel_criado ON lead_funnel(criado_em);


-- ============================================================================
-- View: Funil agregado por utm_source (para dashboard)
-- ============================================================================
CREATE OR REPLACE VIEW vw_funnel_por_origem AS
SELECT
  COALESCE(utm_source, 'direto') AS origem,
  COUNT(*) FILTER (WHERE entrou_landing IS NOT NULL) AS visits,
  COUNT(*) FILTER (WHERE clicou_cta IS NOT NULL) AS cta_clicks,
  COUNT(*) FILTER (WHERE iniciou_login IS NOT NULL) AS login_starts,
  COUNT(*) FILTER (WHERE criou_conta IS NOT NULL) AS signups,
  COUNT(*) FILTER (WHERE entrou_grupo_whatsapp IS NOT NULL) AS whatsapp_joined,
  COUNT(*) FILTER (WHERE primeira_acao_app IS NOT NULL) AS activated,
  -- taxas
  ROUND(100.0 * COUNT(*) FILTER (WHERE clicou_cta IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE entrou_landing IS NOT NULL), 0), 1) AS cta_rate_pct,
  ROUND(100.0 * COUNT(*) FILTER (WHERE criou_conta IS NOT NULL) /
        NULLIF(COUNT(*) FILTER (WHERE entrou_landing IS NOT NULL), 0), 2) AS signup_rate_pct
FROM lead_funnel
WHERE entrou_landing > NOW() - INTERVAL '90 days'
GROUP BY COALESCE(utm_source, 'direto')
ORDER BY visits DESC;


-- ============================================================================
-- View: Funil diário (total)
-- ============================================================================
CREATE OR REPLACE VIEW vw_funnel_diario AS
SELECT
  DATE(entrou_landing) AS dia,
  COUNT(*) AS visits,
  COUNT(*) FILTER (WHERE criou_conta IS NOT NULL) AS signups,
  COUNT(*) FILTER (WHERE entrou_grupo_whatsapp IS NOT NULL) AS whatsapp_joined,
  ROUND(AVG(EXTRACT(EPOCH FROM (criou_conta - entrou_landing)) / 60)
        FILTER (WHERE criou_conta IS NOT NULL), 1) AS avg_min_to_signup
FROM lead_funnel
WHERE entrou_landing > NOW() - INTERVAL '90 days'
GROUP BY DATE(entrou_landing)
ORDER BY dia DESC;