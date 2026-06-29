-- Migration: Create competitor_intel table
-- Purpose: Store competitor intelligence per tenant

-- Verifica se a tabela já existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'competitor_intel') THEN

        CREATE TABLE competitor_intel (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id INT NOT NULL,
            segmento VARCHAR(100) NOT NULL DEFAULT '',
            nome VARCHAR(255) NOT NULL,
            site_url VARCHAR(500) DEFAULT '',
            pricing VARCHAR(100) DEFAULT '',
            strengths TEXT DEFAULT '',
            weaknesses TEXT DEFAULT '',
            battle_card TEXT DEFAULT '',
            source VARCHAR(50) DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        -- Index para consultas por tenant + segmento
        CREATE INDEX idx_competitor_intel_tenant_segmento ON competitor_intel(tenant_id, segmento);

        -- Index para busca por nome
        CREATE INDEX idx_competitor_intel_nome ON competitor_intel(tenant_id, nome);

        -- Comentários
        COMMENT ON TABLE competitor_intel IS 'Armazena inteligência competitiva por tenant';
        COMMENT ON COLUMN competitor_intel.tenant_id IS 'ID do tenant (mesmo de users.id)';
        COMMENT ON COLUMN competitor_intel.segmento IS 'Segmento/nicho do concorrente';
        COMMENT ON COLUMN competitor_intel.source IS 'Origem: manual, auto_research, import';

        RAISE NOTICE 'Tabela competitor_intel criada com sucesso';
    ELSE
        RAISE NOTICE 'Tabela competitor_intel já existe';
    END IF;
END $$;
