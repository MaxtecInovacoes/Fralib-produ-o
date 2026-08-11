"""Schema initialization — extracted from core/database.py for reuse."""
from sqlalchemy import text


# Tables created by inicializar_database().
# Keep this list in sync with core/database.py if schema changes.
_CREATE_TABLES_SQL = """

-- Multi-tenancy
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nome VARCHAR(255),
    tenant_id INTEGER DEFAULT 1,
    role VARCHAR(50) DEFAULT 'user',
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    chave VARCHAR(255) NOT NULL,
    valor TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, chave)
);

CREATE TABLE IF NOT EXISTS licencas (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    plano VARCHAR(50) DEFAULT 'basico',
    pipelines_contratadas INTEGER DEFAULT 10,
    pipelines_usadas INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS config_pipeline (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    chave VARCHAR(255) NOT NULL,
    valor TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, chave)
);

-- Pipeline state
CREATE TABLE IF NOT EXISTS pipeline_state (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    lead_id VARCHAR(255) NOT NULL,
    current_state VARCHAR(100) DEFAULT 'init',
    estado_manual VARCHAR(50),
    rodando BOOLEAN DEFAULT FALSE,
    pausado BOOLEAN DEFAULT FALSE,
    caio_output JSONB,
    design_output JSONB,
    build_output JSONB,
    deploy_url VARCHAR(500),
    deploy_path VARCHAR(500),
    run_id VARCHAR(255),
    error TEXT,
    history JSONB DEFAULT '[]'::jsonb,
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_queue (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    lead_id VARCHAR(255) NOT NULL,
    prioridade INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ciclos (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    nome VARCHAR(255),
    ativo BOOLEAN DEFAULT TRUE,
    config JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Leads
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    user_id INTEGER REFERENCES users(id),
    nome VARCHAR(255),
    segmento VARCHAR(100),
    cidade VARCHAR(100),
    status VARCHAR(50) DEFAULT 'novo',
    url_site VARCHAR(500),
    site_url VARCHAR(500),
    email VARCHAR(255),
    telefone VARCHAR(50),
    endereco TEXT,
    jina_research JSONB,
    caio_output JSONB,
    score INTEGER DEFAULT 0,
    tier VARCHAR(50),
    dark_mode BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Jobs
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    run_id VARCHAR(255),
    tipo VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    payload JSONB,
    result JSONB,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error TEXT,
    locked_by VARCHAR(255),
    locked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_failures (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255),
    step VARCHAR(100),
    error TEXT,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_traces (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255) NOT NULL,
    tenant_id INTEGER NOT NULL,
    agent_name VARCHAR(100),
    model VARCHAR(100),
    total_chamadas_llm INTEGER DEFAULT 0,
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    total_cache_read INTEGER DEFAULT 0,
    total_cache_creation INTEGER DEFAULT 0,
    custo_total_usd NUMERIC(10,6) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_token_usage (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(100),
    step VARCHAR(100),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read INTEGER DEFAULT 0,
    cache_creation INTEGER DEFAULT 0,
    model VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS llm_budget_ledger (
    id SERIAL PRIMARY KEY,
    model_id VARCHAR(100) NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read INTEGER DEFAULT 0,
    cache_creation INTEGER DEFAULT 0,
    cost_usd NUMERIC(10,6) DEFAULT 0,
    agente VARCHAR(100),
    provider VARCHAR(50),
    tenant_id INTEGER,
    run_id VARCHAR(255),
    latency_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_run_spans (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255) NOT NULL,
    tenant_id INTEGER NOT NULL,
    span_id VARCHAR(255) NOT NULL,
    parent_span_id VARCHAR(255),
    agent_name VARCHAR(100),
    operation VARCHAR(100),
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    duration_ms INTEGER,
    status VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS provider_rate_limits (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    remaining INTEGER,
    reset_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_model_configs (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100) UNIQUE NOT NULL,
    model VARCHAR(100),
    tier VARCHAR(50),
    temperature NUMERIC(3,2),
    max_tokens INTEGER,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sdr_learning (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    lead_id VARCHAR(255),
    interaction_type VARCHAR(50),
    content TEXT,
    sentiment VARCHAR(50),
    effectiveness_score NUMERIC(3,2),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mercadopago_events (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100),
    payload JSONB,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hermes_incidents (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER,
    severity VARCHAR(50),
    description TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lead_supply_config (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    segmento VARCHAR(100),
    cidade VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE,
    config JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lead_inventory (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    segmento VARCHAR(100),
    cidade VARCHAR(100),
    quantidade_disponivel INTEGER DEFAULT 0,
    quantidade_entregue INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lead_supply_events (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    event_type VARCHAR(100),
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lead_requests (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    segmento VARCHAR(100),
    cidade VARCHAR(100),
    quantidade_solicitada INTEGER DEFAULT 1,
    quantidade_entregue INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    lead_ids JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS franz_conversations (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    lead_id VARCHAR(255),
    phone_number VARCHAR(50),
    messages JSONB DEFAULT '[]'::jsonb,
    sentiment VARCHAR(50),
    intent VARCHAR(100),
    needs_human_followup BOOLEAN DEFAULT FALSE,
    followup_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS franz_memory_episodic (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    lead_id VARCHAR(255),
    phone_number VARCHAR(50),
    interaction_summary TEXT,
    key_facts JSONB,
    next_best_action VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS franz_sales_rules (
    id SERIAL PRIMARY KEY,
    axis_code VARCHAR(10) UNIQUE NOT NULL,
    axis_name VARCHAR(255) NOT NULL,
    trigger_keywords TEXT[],
    system_prompt_fragment TEXT,
    active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS franz_learning_events (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    conversation_id INTEGER REFERENCES franz_conversations(id),
    event_type VARCHAR(100),
    agent_reflection TEXT,
    user_feedback VARCHAR(50),
    applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cakto_events (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100),
    payload JSONB,
    processed BOOLEAN DEFAULT FALSE,
    tenant_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS observability_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(15,6),
    labels JSONB,
    recorded_at TIMESTAMP DEFAULT NOW()
);
"""

_INIT_AGENT_MODELS_SQL = """
INSERT INTO agent_model_configs (agent_name, model, tier, temperature, max_tokens, active)
VALUES
    ('caio', 'claude-sonnet-4-6', 'STANDARD', 0.3, 4096, TRUE),
    ('arquiteto', 'claude-sonnet-4-6', 'PREMIUM', 0.5, 8192, TRUE),
    ('builder', 'claude-sonnet-4-6', 'STANDARD', 0.4, 4096, TRUE),
    ('validador', 'claude-sonnet-4-6', 'LIGHT', 0.2, 2048, TRUE),
    ('franz', 'claude-sonnet-4-6', 'STANDARD', 0.6, 4096, TRUE),
    ('deploy', 'claude-sonnet-4-6', 'LIGHT', 0.2, 2048, TRUE),
    ('hunter', 'claude-sonnet-4-6', 'LIGHT', 0.3, 2048, TRUE),
    ('jina', 'claude-sonnet-4-6', 'LIGHT', 0.1, 1024, TRUE)
ON CONFLICT (agent_name) DO NOTHING;
"""

_INIT_SALES_RULES_SQL = """
INSERT INTO franz_sales_rules (axis_code, axis_name, trigger_keywords, system_prompt_fragment, priority)
VALUES
    ('A', 'Urgency Scarcity', ARRAY['urgente','urgent','rápido','rapido','hoje','agora','prazo','deadline'], '', 10),
    ('B', 'Social Proof', ARRAY['clientes','cliente','cases','case','depoimento','referencia','portfolio'], '', 9),
    ('C', 'Authority Expertise', ARRAY['especialista','expert','anos','experiencia','certificado','premio'], '', 8),
    ('D', 'Pain Agitation', ARRAY['problema','dor','dificuldade','perdendo','perdido','ruim','ruins','falta'], '', 7),
    ('E', 'ROI Value', ARRAY['investimento','retorno','roi','lucro','receita','faturamento','custo','economia'], '', 6),
    ('F', 'Risk Reversal', ARRAY['garantia','risco','satisfacao','devolucao','teste','testar','experimentar'], '', 5),
    ('G', 'CTA Direct', ARRAY['comecar','iniciar','contratar','assinar','contrato','proposta','orcamento','proximo'], '', 4),
    ('H', 'Objection Handler', ARRAY['caro','preco','preços','dinheiro','verba','orcamento','agora nao','depois'], '', 3),
    ('I', 'Empathy Connection', ARRAY['entendo','compreendo','imagino','deve ser','sua situacao','seu momento'], '', 2),
    ('J', 'Curiosity Gap', ARRAY['como','quais','quanto','descobrir','saber mais','explicar','detalhes'], '', 1),
    ('K', 'Closing Assumptive', ARRAY['quando','qual data','qual dia','posso enviar','vou enviar','entao combinado'], '', 0)
ON CONFLICT (axis_code) DO NOTHING;
"""

_SCHEMA_INIT_LOCK_KEY = "fralib_schema_init"


def inicializar_database(engine) -> None:
    """Create all tables and seed data if they do not exist.

    Idempotent — safe to run multiple times.
    Uses advisory lock to prevent race conditions during concurrent startup.
    """
    with engine.connect() as conn:
        conn.execute(text("SET lock_timeout TO '3s'"))
        conn.execute(text("SET statement_timeout TO '60s'"))
        lock_acquired = conn.execute(
            text("SELECT pg_try_advisory_lock(hashtext(:lock_key))"),
            {"lock_key": _SCHEMA_INIT_LOCK_KEY},
        ).scalar()

        if not lock_acquired:
            print("[schema_init] Another worker is initializing schema, skipping.")
            return

        try:
            print("[schema_init] Creating tables...")
            conn.execute(text(_CREATE_TABLES_SQL))
            print("[schema_init] Tables created.")

            print("[schema_init] Seeding agent_model_configs...")
            conn.execute(text(_INIT_AGENT_MODELS_SQL))

            print("[schema_init] Seeding franz_sales_rules...")
            conn.execute(text(_INIT_SALES_RULES_SQL))

            conn.commit()
            print("[schema_init] Schema initialization complete.")
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(hashtext(:lock_key))", {"lock_key": _SCHEMA_INIT_LOCK_KEY}))
