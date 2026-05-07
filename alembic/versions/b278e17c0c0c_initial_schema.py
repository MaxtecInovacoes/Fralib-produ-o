"""initial_schema

Revision ID: b278e17c0c0c
Revises:
Create Date: 2026-04-29 04:10:14.245256

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b278e17c0c0c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Initial schema with all existing tables."""

    # Tabela de usuarios (schema public)
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        schema='public'
    )

    # Tabela de licencas (schema public)
    op.create_table(
        'licencas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('plano', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('data_inicio', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('data_fim', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['usuario_id'], ['public.users.id'], ondelete='CASCADE'),
        schema='public'
    )

    # Tabela de pipeline_state (schema public) - Multi-tenant
    op.create_table(
        'pipeline_state',
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('rodando', sa.Boolean(), server_default=sa.text('FALSE'), nullable=True),
        sa.Column('pausado', sa.Boolean(), server_default=sa.text('FALSE'), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('tenant_id'),
        schema='public'
    )

    # Nota: Tabelas tenant-specific (tenant_<id>.leads, tenant_<id>.ciclos, etc.)
    # sao criadas dinamicamente pelo codigo em database.py quando um novo tenant e criado.
    # Essas tabelas NAO sao gerenciadas por migrations do Alembic.


def downgrade() -> None:
    """Downgrade schema - Remove all tables."""

    op.drop_table('pipeline_state', schema='public')
    op.drop_table('licencas', schema='public')
    op.drop_table('users', schema='public')
