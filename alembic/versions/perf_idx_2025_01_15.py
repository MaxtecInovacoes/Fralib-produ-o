"""perf: adiciona índices críticos para performance (PERF_002)

### Mudanças:
- leads.criado_em: índice para ORDER BY sem full scan
- interacoes.lead_id: índice para JOINs e lookups
- interacoes.user_id + direcao: índice composto para queries do SDR
- ciclos.user_id: índice para queries de ciclos
- sdr_learning.user_id: índice para queries de aprendizado

Revisão: 2025-01-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "perf_idx_2025_01_15"
down_revision = "72bd68b42efe"  # última migração
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CRÍTICO: leads.criado_em para ORDER BY sem full scan
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_user_criado_em
        ON leads (user_id, criado_em DESC)
    """)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_user_status_criado
        ON leads (user_id, status, criado_em)
    """)

    # CRÍTICO: interacoes.lead_id para JOINs
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interacoes_lead_id
        ON interacoes (lead_id)
    """)
    # HIGH: índice composto para queries mais comuns do SDR
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interacoes_lead_user_direcao
        ON interacoes (lead_id, user_id, direcao, criado_em DESC)
    """)

    # HIGH: ciclos.user_id para queries por tenant
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ciclos_user_id
        ON ciclos (user_id, id DESC)
    """)

    # HIGH: sdr_learning.user_id para queries de aprendizado
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sdr_learning_user_id
        ON sdr_learning (user_id, criado_em DESC)
    """)

    # MEDIUM: leads.segmento para GROUP BY
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_user_segmento
        ON leads (user_id, segmento)
        WHERE segmento IS NOT NULL AND segmento != ''
    """)

    # MEDIUM: leads.cidade para GROUP BY
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_user_cidade
        ON leads (user_id, cidade)
        WHERE cidade IS NOT NULL AND cidade != ''
    """)

    # MEDIUM: interacoes.direcao para filtros
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interacoes_direcao
        ON interacoes (direcao, criado_em DESC)
        WHERE direcao IS NOT NULL
    """)

    print("[perf] Índices de performance criados com sucesso")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_leads_user_criado_em")
    op.execute("DROP INDEX IF EXISTS idx_leads_user_status_criado")
    op.execute("DROP INDEX IF EXISTS idx_interacoes_lead_id")
    op.execute("DROP INDEX IF EXISTS idx_interacoes_lead_user_direcao")
    op.execute("DROP INDEX IF EXISTS idx_ciclos_user_id")
    op.execute("DROP INDEX IF EXISTS idx_sdr_learning_user_id")
    op.execute("DROP INDEX IF EXISTS idx_leads_user_segmento")
    op.execute("DROP INDEX IF EXISTS idx_leads_user_cidade")
    op.execute("DROP INDEX IF EXISTS idx_interacoes_direcao")
    print("[perf] Índices de performance removidos")
