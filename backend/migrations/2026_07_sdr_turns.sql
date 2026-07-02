-- Sprint 1.5: Transparencia pro Lead + auditoria de turnos do Franz.
--
-- Tabela sdr_turns registra cada turno processado pelo SDR:
-- stage_before / stage_after = transicao no FSM
-- intent = classificacao do orchestrator (regex/LLM)
-- confidence = score do intent classifier (0.00-1.00)
-- latency_ms = quanto o turno levou end-to-end
-- llm_cost_usd = quanto custou o LLM naquele turno
--
-- Indice composto (lead_id, criado_em DESC) suporta queries de auditoria
-- do tipo "mostre os ultimos 50 turnos deste lead" sem sort em memoria.

CREATE TABLE IF NOT EXISTS sdr_turns (
    id BIGSERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL,
    tenant_id INTEGER NOT NULL,
    stage_before VARCHAR(40),
    stage_after VARCHAR(40),
    intent VARCHAR(40),
    confidence NUMERIC(3,2),
    latency_ms INTEGER,
    llm_cost_usd NUMERIC(12,6),
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sdr_turns_lead ON sdr_turns (lead_id, criado_em DESC);
