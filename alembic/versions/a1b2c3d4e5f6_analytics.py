"""add analytics_events table

Revision ID: a1b2c3d4e5f6_analytics
Revises: 001_add_automation_columns
Create Date: 2026-06-26 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6_analytics'
down_revision = '001_add_automation_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Create analytics_events table
    op.create_table(
        'analytics_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('event_name', sa.String(length=100), nullable=False),
        sa.Column('event_data', sa.Text(), nullable=True),
        sa.Column('utm_source', sa.String(length=100), nullable=True),
        sa.Column('utm_medium', sa.String(length=100), nullable=True),
        sa.Column('utm_campaign', sa.String(length=100), nullable=True),
        sa.Column('utm_content', sa.String(length=100), nullable=True),
        sa.Column('utm_term', sa.String(length=100), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('referrer', sa.Text(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_analytics_events_session', 'session_id'),
        sa.Index('idx_analytics_events_event', 'event_name'),
        sa.Index('idx_analytics_events_date', 'created_at'),
        sa.Index('idx_analytics_events_utm', 'utm_source', 'utm_campaign')
    )

    # Create ad_spend table for KPI calculations
    op.create_table(
        'ad_spend',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('campaign', sa.String(length=100), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create index for ad_spend
    op.create_index(
        'idx_ad_spend_date',
        'ad_spend',
        ['date', 'source']
    )


def downgrade():
    op.drop_index('idx_ad_spend_date', table_name='ad_spend')
    op.drop_table('ad_spend')
    op.drop_table('analytics_events')
