"""Adiciona coluna estado a leads_cache (que estava faltando).

Revision ID: 2026_07_add_estado_leads_cache
Revises: 003_add_leads_plano_created_at
Create Date: 2026-07-03 14:15:00.000000

Contexto:
- Hunter V2 (backend/utils/agente1_hunter_v2.py:541) faz INSERT em
  leads_cache com coluna `estado` (sigla UF).
- Schema original da tabela nao tinha essa coluna.
- Resultado: toda tentativa de salvar no cache falhava com
  UndefinedColumn, e Hunter perdia todos os leads que encontrava.
- Fix: adicionar coluna `estado VARCHAR(2)` (sigla do estado brasileiro).

Em prod ja foi aplicado via psql direto (2026-07-03 14:13 UTC).
Esta migration formaliza a mudanca no grafo Alembic pra ambientes novos.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '2026_07_add_estado_leads_cache'
down_revision = '003_add_leads_plano_created_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Adiciona coluna estado VARCHAR(2) a leads_cache (idempotente)."""
    op.execute("""
        ALTER TABLE leads_cache
        ADD COLUMN IF NOT EXISTS estado VARCHAR(2)
    """)
    # Comentario pra documentar
    op.execute("""
        COMMENT ON COLUMN leads_cache.estado
        IS 'Sigla UF do estado (BR). Adicionado 2026-07-03 - Hunter V2.'
    """)


def downgrade() -> None:
    """Remove coluna estado."""
    op.execute("ALTER TABLE leads_cache DROP COLUMN IF EXISTS estado")