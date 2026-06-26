"""add_wpp_lock_to_leads

Adiciona coluna wpp_lock_until na tabela leads para evitar que
duas instâncias do whatsapp_listener processem a mesma mensagem
de um lead simultaneamente.

Lock: SELECT FOR UPDATE SKIP LOCKED no whatsapp_listener.py antes
de qualquer processamento de mensagem.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_wpp_lock_to_leads'
down_revision: Union[str, Sequence[str], None] = 'interacoes_idempotency_v1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'leads',
        sa.Column('wpp_lock_until', sa.TIMESTAMP(timezone=True), nullable=True),
        schema='public',
    )
    op.create_index(
        'idx_leads_wpp_lock',
        'leads',
        ['wpp_lock_until'],
        schema='public',
        postgresql_where=sa.text('wpp_lock_until IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('idx_leads_wpp_lock', table_name='leads', schema='public')
    op.drop_column('leads', 'wpp_lock_until', schema='public')
