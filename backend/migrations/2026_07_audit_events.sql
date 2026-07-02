-- Sprint 2.2 — Trilha de Auditoria Unificada
-- Tabela unificada audit_events: registra acoes de auth, leads, tenants, pipelines, credits, SDR, etc.
-- Fail-safe: insercoes falhas NUNCA devem derrubar a request principal (ver backend/audit/recorder.py).

CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER,
    actor_id INTEGER,
    actor_email VARCHAR(180),
    actor_role VARCHAR(40),
    action VARCHAR(80) NOT NULL,
    entity_type VARCHAR(60) NOT NULL,
    entity_id INTEGER,
    diff_json JSONB DEFAULT '{}'::jsonb,
    ip INET,
    user_agent VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant_time
    ON audit_events (tenant_id, criado_em DESC);

CREATE INDEX IF NOT EXISTS idx_audit_actor_time
    ON audit_events (actor_id, criado_em DESC);

CREATE INDEX IF NOT EXISTS idx_audit_action_time
    ON audit_events (action, criado_em DESC);