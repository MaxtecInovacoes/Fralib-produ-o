"""legal acceptance and Mercado Pago payment audit

Revision ID: legal_payment_hardening
Revises: tenant_api_keys_v1
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa  # noqa: F401


revision = "legal_payment_hardening"
down_revision = "tenant_api_keys_v1"
branch_labels = None
depends_on = None


def upgrade():
    for statement in (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_version VARCHAR(80)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS privacy_accepted_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS privacy_version VARCHAR(80)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS legal_acceptance_ip VARCHAR(120)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS payment_provider VARCHAR(40)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS mercadopago_payer_id VARCHAR(120)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS mercadopago_subscription_id VARCHAR(120)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS mercadopago_last_payment_id VARCHAR(120)",
    ):
        op.execute(statement)
    op.execute("""
        CREATE TABLE IF NOT EXISTS mercadopago_events (
            event_id VARCHAR(180) PRIMARY KEY,
            tipo VARCHAR(120),
            user_id INTEGER,
            payment_id VARCHAR(120),
            processado BOOLEAN DEFAULT FALSE,
            erro TEXT,
            raw_payload TEXT,
            criado_em TIMESTAMP DEFAULT NOW(),
            processado_em TIMESTAMP
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mercadopago_events_payment
        ON mercadopago_events (payment_id, criado_em DESC)
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_mercadopago_events_payment")
    op.execute("DROP TABLE IF EXISTS mercadopago_events")
    for column_name in (
        "mercadopago_last_payment_id",
        "mercadopago_subscription_id",
        "mercadopago_payer_id",
        "payment_provider",
        "legal_acceptance_ip",
        "privacy_version",
        "privacy_accepted_at",
        "terms_version",
        "terms_accepted_at",
    ):
        op.execute(f"ALTER TABLE users DROP COLUMN IF EXISTS {column_name}")
