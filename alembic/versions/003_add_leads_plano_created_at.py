"""Migration: Add plano and created_at columns to leads

Revision ID: 003_add_leads_plano_created_at
Revises: 002_add_retargeting_tracking
Create Date: 2026-06-27 19:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_leads_plano_created_at'
down_revision = '002_add_retargeting_tracking'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar colunas que faltavam na tabela leads para automação
    op.add_column('leads', sa.Column('plano', sa.String(50), nullable=True, server_default='trial'))
    op.add_column('leads', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))

    # Atualizar leads existentes que tem criado_em mas não created_at
    op.execute("UPDATE leads SET created_at = criado_em::timestamp WHERE created_at IS NULL AND criado_em IS NOT NULL")


def downgrade():
    op.drop_column('leads', 'created_at')
    op.drop_column('leads', 'plano')
