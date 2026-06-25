"""Add dedup_key column to interacoes table for idempotency

Revision ID: interacoes_idempotency_v1
Revises: tenant_api_keys_v1
Create Date: 2025-01-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'interacoes_idempotency_v1'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar coluna dedup_key (nullable para compatibilidade)
    op.add_column('interacoes', sa.Column('dedup_key', sa.String(255), nullable=True))

    # Criar índice para melhorar performance de lookup
    op.create_index('ix_interacoes_dedup_key', 'interacoes', ['dedup_key'])

    # Criar constraint UNIQUE na combinação (lead_id, user_id, dedup_key)
    # Isso impede inserções duplicadas baseadas na chave de deduplicação
    op.create_index(
        'ix_interacoes_unique_dedup',
        'interacoes',
        ['lead_id', 'user_id', 'dedup_key'],
        unique=True,
        postgresql_where=sa.text('dedup_key IS NOT NULL')
    )


def downgrade():
    # Remover constraint e índice
    op.drop_index('ix_interacoes_unique_dedup', table_name='interacoes')
    op.drop_index('ix_interacoes_dedup_key', table_name='interacoes')

    # Remover coluna
    op.drop_column('interacoes', 'dedup_key')