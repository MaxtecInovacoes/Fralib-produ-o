-- Migration: Create linkedin_prospects and linkedin_templates tables
-- Purpose: Store LinkedIn prospects and templates per tenant

DO $$
BEGIN
    -- Tabela de Prospects
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'linkedin_prospects') THEN

        CREATE TABLE linkedin_prospects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id INT NOT NULL,
            nome VARCHAR(255) NOT NULL,
            empresa VARCHAR(255) NOT NULL,
            cargo VARCHAR(100) DEFAULT '',
            linkedin_url VARCHAR(500) DEFAULT '',
            segmento VARCHAR(100) DEFAULT '',
            cidade VARCHAR(100) DEFAULT '',
            email VARCHAR(255) DEFAULT '',
            telefone VARCHAR(50) DEFAULT '',
            status VARCHAR(50) DEFAULT 'new',
            last_contacted_at TIMESTAMP,
            response TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX idx_linkedin_prospects_tenant ON linkedin_prospects(tenant_id);
        CREATE INDEX idx_linkedin_prospects_status ON linkedin_prospects(tenant_id, status);
        CREATE INDEX idx_linkedin_prospects_segmento ON linkedin_prospects(tenant_id, segmento);

        COMMENT ON TABLE linkedin_prospects IS 'Armazena prospects do LinkedIn por tenant';

        RAISE NOTICE 'Tabela linkedin_prospects criada';
    ELSE
        RAISE NOTICE 'Tabela linkedin_prospects já existe';
    END IF;

    -- Tabela de Templates
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'linkedin_templates') THEN

        CREATE TABLE linkedin_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id INT NOT NULL,
            nome VARCHAR(255) NOT NULL,
            assunto VARCHAR(500) DEFAULT '',
            corpo TEXT NOT NULL,
            segmento VARCHAR(100) DEFAULT 'geral',
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX idx_linkedin_templates_tenant ON linkedin_templates(tenant_id);

        COMMENT ON TABLE linkedin_templates IS 'Armazena templates de InMail por tenant';

        RAISE NOTICE 'Tabela linkedin_templates criada';
    ELSE
        RAISE NOTICE 'Tabela linkedin_templates já existe';
    END IF;

END $$;
