"""tenant_api_keys table

Revision ID: tenant_api_keys_v1
Revises: provider_alerts
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'tenant_api_keys_v1'
down_revision = 'provider_alerts'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS tenant_api_keys (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            key_hash VARCHAR(64) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL DEFAULT 'Primary',
            scopes VARCHAR(500),
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            last_used_at TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_key_hash ON tenant_api_keys(key_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_user_id ON tenant_api_keys(user_id)")


def downgrade():
    op.drop_index('ix_tenant_api_keys_user_id', table_name='tenant_api_keys')
    op.drop_index('ix_tenant_api_keys_key_hash', table_name='tenant_api_keys')
    op.drop_table('tenant_api_keys')
