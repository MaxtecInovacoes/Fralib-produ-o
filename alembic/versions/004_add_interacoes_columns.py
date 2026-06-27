"""Migration: Add created_at and tipo columns to interacoes

Revision ID: 004_add_interacoes_columns
Revises: 003_add_leads_plano_created_at
Create Date: 2026-06-27 20:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_interacoes_columns'
down_revision = '003_add_leads_plano_created_at'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar colunas que faltavam na tabela interacoes
    op.add_column('interacoes', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('interacoes', sa.Column('tipo', sa.String(50), nullable=True))

    # Backfill: created_at = criado_em::timestamp
    op.execute("UPDATE interacoes SET created_at = criado_em::timestamp WHERE created_at IS NULL AND criado_em IS NOT NULL")

    # Indice para queries de automacao (ultimas interacoes por lead)
    op.create_index('idx_interacoes_lead_created', 'interacoes', ['lead_id', 'created_at'])


def downgrade():
    op.drop_index('idx_interacoes_lead_created')
    op.drop_column('interacoes', 'tipo')
    op.drop_column('interacoes', 'created_at')
