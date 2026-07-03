-- Migration: Tabelas para Sistema de Auto-Post Multi-Tenant
-- Executar: psql -U fralib_user -d fralib_db -f migration_social_projects.sql

BEGIN;

-- Tabela principal de projetos sociais
CREATE TABLE IF NOT EXISTS social_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_slug VARCHAR(100) NOT NULL,
    project_name VARCHAR(255) NOT NULL,

    -- Credenciais (criptografadas com FERNET_KEY)
    facebook_page_token_encrypted TEXT,
    facebook_page_id_encrypted TEXT,
    instagram_business_id_encrypted TEXT,
    linkedin_access_token_encrypted TEXT,
    twitter_bearer_token_encrypted TEXT,
    twitter_api_key_encrypted TEXT,
    twitter_api_secret_encrypted TEXT,
    twitter_access_token_encrypted TEXT,
    twitter_access_secret_encrypted TEXT,

    -- Configurações
    is_active BOOLEAN DEFAULT true,
    post_frequency_per_day INTEGER DEFAULT 1,
    preferred_post_time TIME DEFAULT '10:00:00',
    timezone VARCHAR(50) DEFAULT 'America/Sao_Paulo',

    -- Estratégia de conteúdo
    content_niche VARCHAR(100),
    content_tone VARCHAR(50),
    content_formats TEXT[],
    content_hooks TEXT[],
    content_ctas TEXT[],

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_post_at TIMESTAMP,

    UNIQUE(tenant_id, project_slug)
);

-- Log de postagens por projeto
CREATE TABLE IF NOT EXISTS social_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES social_projects(id) ON DELETE CASCADE,

    platform VARCHAR(20) NOT NULL,
    post_type VARCHAR(20) NOT NULL,
    content_text TEXT,
    media_urls TEXT[],
    media_local_paths TEXT[],

    status VARCHAR(20) DEFAULT 'pending',
    external_post_id VARCHAR(255),
    published_at TIMESTAMP,
    error_message TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Calendário editorial por projeto
CREATE TABLE IF NOT EXISTS content_calendar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES social_projects(id) ON DELETE CASCADE,

    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL,
    platform VARCHAR(20) NOT NULL,
    content_type VARCHAR(20) NOT NULL,
    topic VARCHAR(255),
    hook VARCHAR(500),
    caption_template TEXT,
    media_brief TEXT,
    status VARCHAR(20) DEFAULT 'draft',
    post_id UUID REFERENCES social_posts(id),

    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, scheduled_date, platform)
);

-- Análise de viralização por nicho
CREATE TABLE IF NOT EXISTS niche_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES social_projects(id) ON DELETE CASCADE,

    competitor_username VARCHAR(255),
    platform VARCHAR(20),
    total_followers INTEGER,
    avg_engagement_rate NUMERIC(5,2),
    top_posts JSONB,
    top_hooks JSONB,
    content_patterns JSONB,
    analyzed_at TIMESTAMP DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_social_projects_tenant ON social_projects(tenant_id);
CREATE INDEX IF NOT EXISTS idx_social_projects_slug ON social_projects(project_slug);
CREATE INDEX IF NOT EXISTS idx_social_posts_project ON social_posts(project_id);
CREATE INDEX IF NOT EXISTS idx_social_posts_status ON social_posts(status);
CREATE INDEX IF NOT EXISTS idx_content_calendar_project ON content_calendar(project_id);
CREATE INDEX IF NOT EXISTS idx_content_calendar_date ON content_calendar(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_niche_analysis_project ON niche_analysis(project_id);

-- Comentários
COMMENT ON TABLE social_projects IS 'Projetos multi-tenant de auto-post em redes sociais';
COMMENT ON TABLE social_posts IS 'Log de postagens realizadas';
COMMENT ON TABLE content_calendar IS 'Calendário editorial por projeto';
COMMENT ON TABLE niche_analysis IS 'Análise de viralização por nicho';

COMMIT;
