"""sync one-truth mirrors and job 577 ledger consolidation

Revision ID: 72bd68b42efe
Revises: legal_payment_hardening
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '72bd68b42efe'
down_revision = 'legal_payment_hardening'
branch_labels = None
depends_on = None


def upgrade():
    # 1. users.plan <- users.plano
    op.execute("""
        UPDATE users
        SET plan = plano
        WHERE COALESCE(plano, '') <> COALESCE(plan, '')
          AND plano IS NOT NULL
    """)

    # 2. leads.pipeline_stage <- leads.status
    op.execute("""
        UPDATE leads
        SET pipeline_stage = status
        WHERE COALESCE(status, '') <> COALESCE(pipeline_stage, '')
          AND status IS NOT NULL
    """)

    # 3. Job 577 consolidation: llm_tokens_used and llm_cost_estimate from llm_budget_ledger
    op.execute("""
        UPDATE jobs j
        SET
          llm_tokens_used = COALESCE(NULLIF(j.llm_tokens_used, 0), agg.tokens),
          llm_cost_estimate = COALESCE(NULLIF(j.llm_cost_estimate::numeric, 0), agg.cost)
        FROM (
          SELECT
            job_id,
            SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS tokens,
            SUM(COALESCE(cost_usd, 0)) AS cost
          FROM llm_budget_ledger
          WHERE job_id = 577
          GROUP BY job_id
        ) agg
        WHERE j.id = agg.job_id
          AND j.id = 577
    """)


def downgrade():
    # Cannot reverse this migration safely because we don't have original
    # llm_tokens_used=0 vs ledger value. Operators should restore from
    # snapshot taken before the migration.
    pass
