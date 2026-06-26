"""Add opt_out_pending and opt_out_pending_at columns to leads table.

Bug fix 2026-06-26: Franz marcava opt_out prematuramente sem 2-step
de confirmacao porque o codigo Python LeadMemory esperava colunas
opt_out_pending / opt_out_pending_at que nunca foram criadas no banco.

Erro: column "opt_out_pending" does not exist.

Revision ID: leads_optout_pending_v1
Revises: interacoes_idempotency_v1
Create Date: 2026-06-26 20:45:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'leads_optout_pending_v1'
down_revision = 'add_wpp_lock_to_leads'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar colunas opt_out_pending (boolean) e opt_out_pending_at (timestamp)
    op.add_column('leads', sa.Column('opt_out_pending', sa.Boolean, nullable=True, server_default='false'))
    op.add_column('leads', sa.Column('opt_out_pending_at', sa.DateTime, nullable=True))


def downgrade():
    op.drop_column('leads', 'opt_out_pending_at')
    op.drop_column('leads', 'opt_out_pending')