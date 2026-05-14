"""provider_alerts — alertas de problemas com keys de IA (rate-limit, all-failed, key-invalid)

Revision ID: provider_alerts
Revises: provider_keys
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa  # noqa: F401


revision = 'provider_alerts'
down_revision = 'provider_keys'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS provider_alerts (
            id              BIGSERIAL PRIMARY KEY,
            tipo            VARCHAR(32) NOT NULL,
            key_id          INTEGER REFERENCES provider_keys(id) ON DELETE SET NULL,
            mensagem        TEXT NOT NULL,
            lead_id         BIGINT REFERENCES leads(id) ON DELETE SET NULL,
            user_id_afetado BIGINT REFERENCES users(id) ON DELETE SET NULL,
            lido            BOOLEAN NOT NULL DEFAULT FALSE,
            criado_em       TIMESTAMP NOT NULL DEFAULT NOW(),
            lido_em         TIMESTAMP,
            CONSTRAINT provider_alerts_tipo_chk
                CHECK (tipo IN ('rate_limit','all_keys_failed','key_invalid','test_failed'))
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_provider_alerts_unread
        ON provider_alerts(lido, criado_em DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_provider_alerts_lead
        ON provider_alerts(lead_id) WHERE lead_id IS NOT NULL
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_provider_alerts_lead")
    op.execute("DROP INDEX IF EXISTS idx_provider_alerts_unread")
    op.execute("DROP TABLE IF EXISTS provider_alerts")
