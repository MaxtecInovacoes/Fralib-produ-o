"""Add paleta_cores to leads table for SDR visual consistency.

Revision ID: add_paleta_cores_to_leads
Revises: 003_add_leads_plano_created_at
Create Date: 2026-06-26

ATENCAO (2026-07-03): Esta migration tinha down_revision=None (raiz
fantasma), religada para 003_add_leads_plano_created_at (outra migration
que altera a tabela leads). Resolve bug do grafo Alembic quebrado.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_paleta_cores_to_leads'
down_revision = '003_add_leads_plano_created_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add column for paleta_cores (JSON field for color palette)
    op.add_column(
        'leads',
        sa.Column('paleta_cores', sa.JSON, nullable=True, comment='Paleta de cores do site gerado (SDR usa para identidade visual)')
    )

    # Update existing leads with default palette (if they have sites)
    op.execute("""
        UPDATE leads
        SET paleta_cores = '{"primary": "#374151", "secondary": "#f9fafb", "accent": "#6366f1"}'
        WHERE site_url IS NOT NULL AND site_url != '' AND paleta_cores IS NULL
    """)


def downgrade() -> None:
    op.drop_column('leads', 'paleta_cores')
