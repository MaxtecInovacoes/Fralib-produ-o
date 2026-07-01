-- ============================================================
-- MIGRACAO: subscription_flow_v1
-- Novos campos: users.access, users.trial_*, users.current_plan_id
-- Novas tabelas: plans, orders, subscriptions, webhook_events
-- ============================================================

-- ============================================================
-- 1. NOVOS CAMPOS NA TABELA USERS
-- ============================================================

-- Access control: 'released' | 'blocked'
ALTER TABLE users ADD COLUMN IF NOT EXISTS access VARCHAR(20) DEFAULT 'released';

-- Trial tracking
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_started_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMP;

-- Plano atual (references plans.id)
ALTER TABLE users ADD COLUMN IF NOT EXISTS current_plan_id VARCHAR(50) DEFAULT 'trial';
ALTER TABLE users ADD COLUMN IF NOT EXISTS converted_at TIMESTAMP;

-- Contato
ALTER TABLE users ADD COLUMN IF NOT EXISTS whatsapp VARCHAR(50);

-- Atualizar usuarios existentes: marcar trial valido
UPDATE users
SET
    access = COALESCE(access, 'released'),
    current_plan_id = COALESCE(current_plan_id, plano, 'trial'),
    trial_started_at = COALESCE(trial_started_at, criado_em::timestamp, NOW()),
    trial_ends_at = COALESCE(trial_ends_at, trial_expires_at::timestamp, NOW() + INTERVAL '7 days')
WHERE trial_ends_at IS NULL;

-- ============================================================
-- 2. TABELA PLANS
-- ============================================================

CREATE TABLE IF NOT EXISTS plans (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    monthly_price_cents INTEGER NOT NULL DEFAULT 0,
    monthly_credits INTEGER NOT NULL DEFAULT 1,
    cooldown_seconds INTEGER DEFAULT 0,
    has_sdr BOOLEAN DEFAULT FALSE,
    is_paid BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    trial_days INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Plans default (R$97 Starter, R$197 Pro, R$497 Agency)
INSERT INTO plans (id, name, description, monthly_price_cents, monthly_credits, cooldown_seconds, has_sdr, is_paid, trial_days, sort_order)
VALUES
    ('trial',   'Trial',   '1 site para testar o sistema', 0,     1,     0,    FALSE, FALSE, 7,  0),
    ('starter', 'Starter', '180 creditos/mes com cooldown 60min', 9700,  180, 3600, FALSE, TRUE, 0,   1),
    ('pro',     'Pro',     '360 creditos/mes com cooldown 30min e SDR automatico', 19700, 360, 1800, TRUE,  TRUE, 0,  2),
    ('agency',  'Agency',  'Sites ilimitados sem cooldown, painel master', 49700, 99999, 0,  TRUE,  TRUE, 0,  3)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    monthly_price_cents = EXCLUDED.monthly_price_cents,
    monthly_credits = EXCLUDED.monthly_credits,
    cooldown_seconds = EXCLUDED.cooldown_seconds,
    has_sdr = EXCLUDED.has_sdr,
    is_paid = EXCLUDED.is_paid,
    trial_days = EXCLUDED.trial_days,
    updated_at = NOW();

-- ============================================================
-- 3. TABELA ORDERS (Pedidos/Payments)
-- ============================================================

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    plan_id VARCHAR(50) NOT NULL,
    amount_cents INTEGER NOT NULL DEFAULT 0,
    amount_paid_cents INTEGER DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'BRL',
    payment_type VARCHAR(30) DEFAULT 'mercadopago',
    mercadopago_preference_id VARCHAR(120),
    mercadopago_payment_id VARCHAR(120),
    mercadopago_status VARCHAR(30),
    status VARCHAR(30) DEFAULT 'pending',  -- pending | approved | canceled | refunded | expired | failed
    flow VARCHAR(30) NOT NULL,             -- trial_signup | direct_signup | trial_upgrade | abandoned_recovery | recurring
    created_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    canceled_at TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_mp_payment_id ON orders(mercadopago_payment_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_plan_id ON orders(plan_id);

-- ============================================================
-- 4. TABELA SUBSCRIPTIONS (Assinaturas Recorrentes)
-- ============================================================

CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    plan_id VARCHAR(50) NOT NULL,
    mercadopago_preapproval_id VARCHAR(120),
    mercadopago_payer_id VARCHAR(120),
    billing_cycle INTEGER DEFAULT 1,
    amount_cents INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(30) DEFAULT 'pending',  -- active | canceled | paused | pending | expired
    started_at TIMESTAMP,
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    canceled_at TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_mp_preapproval ON subscriptions(mercadopago_preapproval_id);

-- ============================================================
-- 5. TABELA WEBHOOK_EVENTS (Auditoria de Webhooks)
-- ============================================================

CREATE TABLE IF NOT EXISTS webhook_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(180) UNIQUE NOT NULL,
    source VARCHAR(50) DEFAULT 'mercadopago',
    event_type VARCHAR(120),
    action VARCHAR(120),
    payment_id VARCHAR(120),
    preapproval_id VARCHAR(120),
    preference_id VARCHAR(120),
    user_id INTEGER,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    error TEXT,
    raw_payload TEXT,
    raw_headers JSONB,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhook_events_user_id ON webhook_events(user_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_processed ON webhook_events(processed);
CREATE INDEX IF NOT EXISTS idx_webhook_events_payment_id ON webhook_events(payment_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_created_at ON webhook_events(created_at DESC);
