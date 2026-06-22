"""sdr_studio_versions

Revision ID: a1b2c3d4e5f6
Revises: perf_idx_comprehensive
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = 'perf_idx_comprehensive'
branch_labels = None
depends_on = None


def upgrade():
    """Tabela de versionamento dos 3 blocos de prompt do SDR Studio."""
    op.create_table(
        'sdr_studio_versions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('layer', sa.String(32), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'), nullable=False),
        sa.Column('note', sa.String(255), nullable=True),
    )
    op.create_index(
        'ix_sdr_studio_versions_layer_time',
        'sdr_studio_versions',
        ['layer', sa.text('created_at DESC')],
    )


def downgrade():
    op.drop_index('ix_sdr_studio_versions_layer_time', table_name='sdr_studio_versions')
    op.drop_table('sdr_studio_versions')