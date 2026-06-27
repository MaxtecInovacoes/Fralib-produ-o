"""Adicionar campo whatsapp_pendente na tabela leads

Revision ID: add_whatsapp_pendente_to_leads
Revises: add_wpp_lock_to_leads
Create Date: 2026-06-27 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_whatsapp_pendente_to_leads'
down_revision = 'add_wpp_lock_to_leads'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar coluna whatsapp_pendente como nullable
    op.add_column('leads', sa.Column('whatsapp_pendente', sa.Boolean(), nullable=True, server_default='false'))

    # Criar índice para melhor performance
    op.create_index('idx_leads_whatsapp_pendente', 'leads', ['whatsapp_pendente'])

    # Atualizar registros existentes: se não tiver telefone_whatsapp, marca como pendente
    op.execute("""
        UPDATE leads
        SET whatsapp_pendente = true
        WHERE telefone_whatsapp IS NULL OR telefone_whatsapp = ''
    """)


def downgrade():
    # Remover índice
    op.drop_index('idx_leads_whatsapp_pendente')

    # Remover coluna
    op.drop_column('leads', 'whatsapp_pendente')