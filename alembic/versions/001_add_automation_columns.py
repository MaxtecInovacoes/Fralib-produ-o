"""Migration: Add automation columns to leads table

Revision ID: 001_add_automation_columns
Revises: 001_initial_schema
Create Date: 2025-01-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_automation_columns'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar colunas de automação à tabela leads
    op.add_column('leads', sa.Column('proximo_sequencia_dia', sa.Integer, nullable=False, server_default='1'))
    op.add_column('leads', sa.Column('sdr_stage', sa.String(50), nullable=False, server_default='pendente_wpp'))
    op.add_column('leads', sa.Column('engajamento_score', sa.Integer, nullable=False, server_default='0'))
    op.add_column('leads', sa.Column('last_automation_sent', sa.DateTime(timezone=True), nullable=True))

    # Criar índice para performance
    op.create_index('idx_leads_sdr_stage', 'leads', ['user_id', 'sdr_stage'])
    op.create_index('idx_leads_sequence_day', 'leads', ['user_id', 'proximo_sequencia_dia'])


def downgrade():
    # Remover índices
    op.drop_index('idx_leads_sequence_day')
    op.drop_index('idx_leads_sdr_stage')

    # Remover colunas
    op.drop_column('leads', 'last_automation_sent')
    op.drop_column('leads', 'engajamento_score')
    op.drop_column('leads', 'sdr_stage')
    op.drop_column('leads', 'proximo_sequencia_dia')