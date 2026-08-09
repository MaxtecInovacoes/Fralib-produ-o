"""provider_keys — CRUD de API keys de provedores de IA com round-robin e failover

Revision ID: provider_keys
Revises: fase4_multitenant_hardening
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa  # noqa: F401


revision = 'provider_keys'
down_revision = 'fase4_multitenant_hardening'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS provider_keys (
            id              SERIAL PRIMARY KEY,
            provider        VARCHAR(32) NOT NULL,
            label           VARCHAR(100) NOT NULL,
            encrypted_key   TEXT NOT NULL,
            base_url        VARCHAR(255),
            enabled         BOOLEAN NOT NULL DEFAULT TRUE,
            cooldown_until  TIMESTAMP,
            last_error      TEXT,
            last_used_at    TIMESTAMP,
            success_count   BIGINT NOT NULL DEFAULT 0,
            failure_count   BIGINT NOT NULL DEFAULT 0,
            criado_em       TIMESTAMP NOT NULL DEFAULT NOW(),
            atualizado_em   TIMESTAMP NOT NULL DEFAULT NOW(),
            criado_por      BIGINT REFERENCES users(id) ON DELETE SET NULL,
            CONSTRAINT provider_keys_provider_chk
                CHECK (provider IN ('anthropic','openai','groq','custom'))
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_provider_keys_provider_enabled
        ON provider_keys(provider, enabled)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_provider_keys_health
        ON provider_keys(provider, enabled, cooldown_until)
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_provider_keys_health")
    op.execute("DROP INDEX IF EXISTS idx_provider_keys_provider_enabled")
    op.execute("DROP TABLE IF EXISTS provider_keys")
