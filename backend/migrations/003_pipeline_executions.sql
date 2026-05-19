-- pipeline_executions: histórico robusto de execuções do pipeline
-- Substitui dependência de leads.processado_em para cooldown

CREATE TABLE IF NOT EXISTS pipeline_executions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    lead_id VARCHAR(255),
    lead_nome VARCHAR(255),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    plano_no_momento VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_exec_user_finished ON pipeline_executions(user_id, finished_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_exec_status ON pipeline_executions(user_id, status);

-- Seed com histórico existente
INSERT INTO pipeline_executions (user_id, lead_id, lead_nome, started_at, finished_at, status, plano_no_momento)
SELECT l.user_id, l.id, l.nome, l.processado_em - INTERVAL '3 minutes', l.processado_em, 'completed', u.plano
FROM leads l JOIN users u ON u.id = l.user_id
WHERE l.status = 'concluido' AND l.processado_em IS NOT NULL
ON CONFLICT DO NOTHING;
