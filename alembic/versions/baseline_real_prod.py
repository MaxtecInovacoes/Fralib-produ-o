"""baseline_real_prod — snapshot do estado real de prod (2026-05-13)

Revision ID: baseline_real_prod
Revises: b278e17c0c0c
Create Date: 2026-05-13
"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision = 'baseline_real_prod'
down_revision = 'b278e17c0c0c'
branch_labels = None
depends_on = None


def upgrade():
    # Snapshot do estado real de prod capturado em 2026-05-13.
    # 50+ tabelas criadas por inicializar_database(); Alembic apenas marca posição.
    pass


def downgrade():
    pass
