-- Migration: Create CRM integration tables
-- Purpose: Store CRM configs and sync history per tenant

DO $$
BEGIN
    -- Tabela de configuração CRM
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'crm_configs') THEN

        CREATE TABLE crm_configs (
            tenant_id INT PRIMARY KEY,
            crm_type VARCHAR(50) DEFAULT 'salesforce',
            api_key_encrypted TEXT,
            access_token_encrypted TEXT,
            refresh_token_encrypted TEXT,
            instance_url VARCHAR(500),
            webhook_url VARCHAR(500),
            last_sync_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        COMMENT ON TABLE crm_configs IS 'Armazena configuração de CRM por tenant';
        COMMENT ON COLUMN crm_configs.api_key_encrypted IS 'API Key criptografada';
        COMMENT ON COLUMN crm_configs.access_token_encrypted IS 'Access token criptografado';

        RAISE NOTICE 'Tabela crm_configs criada';
    ELSE
        RAISE NOTICE 'Tabela crm_configs já existe';
    END IF;

    -- Tabela de histórico de sincronização
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'crm_sync_history') THEN

        CREATE TABLE crm_sync_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id INT NOT NULL,
            lead_id UUID NOT NULL,
            crm_type VARCHAR(50) NOT NULL,
            crm_lead_id VARCHAR(100),
            status VARCHAR(50) DEFAULT 'success',
            error_message TEXT,
            synced_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX idx_crm_sync_tenant ON crm_sync_history(tenant_id);
        CREATE INDEX idx_crm_sync_lead ON crm_sync_history(tenant_id, lead_id);
        CREATE INDEX idx_crm_sync_date ON crm_sync_history(tenant_id, synced_at);

        COMMENT ON TABLE crm_sync_history IS 'Histórico de sincronizações com CRM';

        RAISE NOTICE 'Tabela crm_sync_history criada';
    ELSE
        RAISE NOTICE 'Tabela crm_sync_history já existe';
    END IF;

END $$;
