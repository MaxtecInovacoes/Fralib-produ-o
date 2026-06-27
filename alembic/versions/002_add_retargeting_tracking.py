"""Migration: Add visitor retargeting tracking

Revision ID: 002_add_retargeting_tracking
Revises: 001_add_automation_columns
Create Date: 2026-06-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_retargeting_tracking'
down_revision = '001_add_automation_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Tabela de visitantes anônimos
    op.create_table(
        'visitor_tracking',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(100), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=True, index=True),
        sa.Column('telefone', sa.String(30), nullable=True),
        sa.Column('utm_source', sa.String(100), nullable=True),
        sa.Column('utm_medium', sa.String(100), nullable=True),
        sa.Column('utm_campaign', sa.String(100), nullable=True),
        sa.Column('pagina_visitada', sa.String(500), nullable=True),
        sa.Column('tempo_permanencia_s', sa.Integer, default=0),
        sa.Column('scroll_depth_pct', sa.Integer, default=0),
        sa.Column('clicou_cta', sa.Boolean, default=False),
        sa.Column('submeteu_form', sa.Boolean, default=False),
        sa.Column('converteu_cadastro', sa.Boolean, default=False),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('ip_hash', sa.String(32), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('ultimo_acesso', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Índices para queries de retargeting
    op.create_index('idx_visitor_session', 'visitor_tracking', ['session_id'])
    op.create_index('idx_visitor_email', 'visitor_tracking', ['email'])
    op.create_index('idx_visitor_converted', 'visitor_tracking', ['converteu_cadastro', 'ultimo_acesso'])
    op.create_index('idx_visitor_utm', 'visitor_tracking', ['utm_source', 'utm_campaign'])

    # Tabela de emails de retargeting enviados
    op.create_table(
        'retargeting_emails',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('visitor_id', sa.Integer, sa.ForeignKey('visitor_tracking.id'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('etapa', sa.String(50), nullable=False),  # 30min, 24h, 72h
        sa.Column('template_id', sa.String(100), nullable=True),
        sa.Column('enviado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('aberto_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clicou_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('converteu_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('brevo_message_id', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), default='enviado'),  # enviado, aberto, clicado, bounce
    )

    op.create_index('idx_retarget_visitor', 'retargeting_emails', ['visitor_id'])
    op.create_index('idx_retarget_etapa', 'retargeting_emails', ['etapa', 'enviado_em'])


def downgrade():
    op.drop_index('idx_retarget_etapa')
    op.drop_index('idx_retarget_visitor')
    op.drop_table('retargeting_emails')
    op.drop_index('idx_visitor_utm')
    op.drop_index('idx_visitor_converted')
    op.drop_index('idx_visitor_email')
    op.drop_index('idx_visitor_session')
    op.drop_table('visitor_tracking')