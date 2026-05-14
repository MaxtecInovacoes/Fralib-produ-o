"""fase4_multitenant_hardening — índices, interacoes.user_id e audit_log

Revision ID: fase4_multitenant_hardening
Revises: baseline_real_prod
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa  # noqa: F401


revision = 'fase4_multitenant_hardening'
down_revision = 'baseline_real_prod'
branch_labels = None
depends_on = None


def upgrade():
    # 4.1 — Índice composto leads (FK + user_id NOT NULL já existem em prod)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_leads_user_status
        ON leads(user_id, status)
    """)

    # 4.2 — interacoes.user_id (add coluna, backfill, guard, NOT NULL, FK, index)
    op.execute("ALTER TABLE interacoes ADD COLUMN IF NOT EXISTS user_id BIGINT")
    op.execute("""
        UPDATE interacoes i
        SET user_id = l.user_id
        FROM leads l
        WHERE l.id = i.lead_id AND i.user_id IS NULL
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM interacoes WHERE user_id IS NULL) THEN
                RAISE EXCEPTION 'interacoes orfas (lead_id sem match em leads) — corrija antes';
            END IF;
        END $$
    """)
    op.execute("ALTER TABLE interacoes ALTER COLUMN user_id SET NOT NULL")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_interacoes_user_id'
            ) THEN
                ALTER TABLE interacoes ADD CONSTRAINT fk_interacoes_user_id
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
            END IF;
        END $$
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_interacoes_user_id ON interacoes(user_id)")

    # 4.4 — audit_log (genérica; coexiste com lead_audit que é específica)
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id BIGSERIAL PRIMARY KEY,
            actor_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            target_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            action VARCHAR(64) NOT NULL,
            target_type VARCHAR(64),
            target_id VARCHAR(120),
            metadata JSONB DEFAULT '{}'::jsonb,
            ip VARCHAR(64),
            user_agent TEXT,
            criado_em TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor_id, criado_em DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action, criado_em DESC)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS audit_log")
    op.execute("ALTER TABLE interacoes DROP CONSTRAINT IF EXISTS fk_interacoes_user_id")
    op.execute("DROP INDEX IF EXISTS idx_interacoes_user_id")
    op.execute("ALTER TABLE interacoes DROP COLUMN IF EXISTS user_id")
    op.execute("DROP INDEX IF EXISTS idx_leads_user_status")
