"""site_generation_log_counter

Sprint 14.6: Tabela de log para anti-repeticao de sites por counter rotation.
Cada geracao registra subnicho + variants (layout/motion/copy) usados para
que o proximo lead do mesmo subnicho pegue variants DIFERENTES.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'site_generation_log_counter'
down_revision: Union[str, Sequence[str], None] = 'leads_optout_pending_v1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'site_generation_log',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.String(length=100), nullable=False),
        sa.Column('subnicho', sa.String(length=100), nullable=False),
        sa.Column('segmento', sa.String(length=100), nullable=False),
        sa.Column('layout_variant', sa.String(length=20), nullable=False),
        sa.Column('motion_variant', sa.String(length=20), nullable=False),
        sa.Column('copy_variant', sa.String(length=20), nullable=False),
        sa.Column('color_palette_hash', sa.String(length=64), nullable=False),
        sa.Column('hero_classes', sa.Text(), nullable=False),
        sa.Column('section_order_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='public',
    )
    op.create_index(
        'idx_site_gen_log_subnicho',
        'site_generation_log',
        ['subnicho', 'created_at'],
        schema='public',
    )
    op.create_index(
        'idx_site_gen_log_tenant_subnicho',
        'site_generation_log',
        ['tenant_id', 'subnicho'],
        schema='public',
    )


def downgrade() -> None:
    op.drop_index('idx_site_gen_log_tenant_subnicho', table_name='site_generation_log', schema='public')
    op.drop_index('idx_site_gen_log_subnicho', table_name='site_generation_log', schema='public')
    op.drop_table('site_generation_log', schema='public')
