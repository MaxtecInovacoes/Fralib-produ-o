"""outbound_queue: fila de mensagens outbound com cooldown.

Usuario pediu: max 2 msgs a cada 10 min, com tempo aleatorio entre
msgs (nunca perto), pra proteger numero do wpp de bloqueio.

Implementa:
- Tabela outbound_queue com status, scheduled_at, sent_at
- Rate limit global (janela 10min, max 2 msgs)
- Cleanup de msgs enviadas (manter 7 dias)

ATENCAO (2026-07-03): A tabela outbound_rate_limit (criada nesta migration)
nao tem nenhuma referencia em codigo Python - ela eh DEPRECATED.
Rate limiting ativo usa rate_limit_counters (criado em 2026_07_phone_health.sql).
Manter outbound_rate_limit por seguranca; NAO usar em codigo novo.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'outbound_queue_v1'
down_revision: Union[str, Sequence[str], None] = 'site_generation_log_counter'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'outbound_queue',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True),  # 'franz', 'cron', 'human'
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        # pending | sending | sent | failed | cancelled
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        # 1=highest, 10=lowest
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    # Indice pra processar fila eficientemente
    op.create_index('ix_outbound_queue_status_scheduled', 'outbound_queue', ['status', 'scheduled_at'])
    op.create_index('ix_outbound_queue_tenant_lead', 'outbound_queue', ['tenant_id', 'lead_id'])
    op.create_index('ix_outbound_queue_created', 'outbound_queue', ['created_at'])

    # Tabela de rate limit global (por tenant)
    # Conta msgs enviadas nos ultimos N minutos
    op.create_table(
        'outbound_rate_limit',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id'),
    )


def downgrade() -> None:
    op.drop_index('ix_outbound_queue_created', table_name='outbound_queue')
    op.drop_index('ix_outbound_queue_tenant_lead', table_name='outbound_queue')
    op.drop_index('ix_outbound_queue_status_scheduled', table_name='outbound_queue')
    op.drop_table('outbound_queue')
    op.drop_table('outbound_rate_limit')