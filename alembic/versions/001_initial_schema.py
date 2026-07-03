"""001_initial_schema

Revision ID: 001_initial_schema
Revises: b278e17c0c0c
Create Date: 2026-07-03 12:00:00.000000

ATENCAO (2026-07-03): Esta migration foi criada para religar o grafo Alembic.
O arquivo b278e17c0c0c_initial_schema.py EXISTE mas 001_add_automation_columns.py
apontava para 001_initial_schema (que nao existia). Esta migration eh um NO-OP
(marca posicao no grafo sem mudar schema) - usada apenas para fazer Alembic
conseguir encadear 001_add_automation_columns corretamente.

Em prod: o banco ja tem o schema da b278e17c0c0c aplicada, entao esta migration
NAO faz nada alem de marcar a posicao. Alembic vai apenas registrar que foi
aplicada (upgrade vazio + downgrade vazio).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, Sequence[str], None] = 'b278e17c0c0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: schema ja existe, so marca posicao no grafo."""
    pass


def downgrade() -> None:
    """No-op: nada para reverter."""
    pass