-- Sprint 1.1 — Janela de Simulação do Franz
-- Persiste cada simulação rodada pelo admin (request + response classificada).
-- Não tem FK para leads/tenants porque simulação é offline (sem lead real).

CREATE TABLE IF NOT EXISTS sdr_simulations (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    response TEXT,
    intent VARCHAR(40),
    stage_after VARCHAR(40),
    kanban_action VARCHAR(80),
    rules_applied JSONB DEFAULT '[]'::jsonb,
    latency_ms INTEGER,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sdr_simulations_tenant_time
    ON sdr_simulations (tenant_id, criado_em DESC);