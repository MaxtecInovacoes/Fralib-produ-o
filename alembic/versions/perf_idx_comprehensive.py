"""perf: adiciona índices abrangentes para performance (PERF_003)

### Mudanças - 21 índices faltantes:
- leads.user_id, leads.status, leads.sdr_stage, leads.criado_em
- licencas.usuario_id
- ciclos.user_id
- sdr_learning.user_id, sdr_learning.lead_id
- pipeline_failures.tenant_id, pipeline_failures.criado_em
- jobs.status, jobs.tenant_id, jobs.worker_heartbeat
- interacoes.lead_id
- site_visitas.lead_id, site_visitas.criado_em
- llm_usage.user_id, llm_usage.criado_em
- audit_log.target_user_id
- provider_alerts.user_id_afetado
- mercadopago_events.user_id

Revisão: 2026-06-20
"""

from alembic import op


# revision identifiers
revision = "perf_idx_comprehensive"
down_revision = "perf_idx_2025_01_15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- leads (índices complementares) ---
    # user_id para queries por proprietário
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_user_id
        ON leads (user_id)
    """)
    # status para filtros por etapa
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_status
        ON leads (status)
    """)
    # sdr_stage para queries de pipeline SDR
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_sdr_stage
        ON leads (sdr_stage)
    """)
    # criado_em para ordenação temporal
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_criado_em
        ON leads (criado_em DESC)
    """)

    # --- licencas ---
    # usuario_id para lookups de licença
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_licencas_usuario_id
        ON licencas (usuario_id)
    """)

    # --- ciclos ---
    # user_id para queries por usuário
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ciclos_user_id_v2
        ON ciclos (user_id)
    """)

    # --- sdr_learning ---
    # user_id para queries de aprendizado
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sdr_learning_user_id_v2
        ON sdr_learning (user_id)
    """)
    # lead_id para consultas por lead
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sdr_learning_lead_id
        ON sdr_learning (lead_id)
    """)

    # --- pipeline_failures ---
    # tenant_id para isolamento multi-tenant
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pipeline_failures_tenant_id
        ON pipeline_failures (tenant_id)
    """)
    # criado_em para retenção e limpeza
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pipeline_failures_criado_em
        ON pipeline_failures (criado_em DESC)
    """)

    # --- jobs ---
    # status para monitoramento
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_status
        ON jobs (status)
    """)
    # tenant_id para isolamento multi-tenant
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_tenant_id
        ON jobs (tenant_id)
    """)
    # worker_heartbeat para detecção de workers órfãos
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_worker_heartbeat
        ON jobs (worker_heartbeat)
    """)

    # --- interacoes ---
    # lead_id para JOINs com leads
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interacoes_lead_id_v2
        ON interacoes (lead_id)
    """)

    # --- site_visitas ---
    # lead_id para consultas por lead
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_site_visitas_lead_id
        ON site_visitas (lead_id)
    """)
    # criado_em para análise temporal
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_site_visitas_criado_em
        ON site_visitas (criado_em DESC)
    """)

    # --- llm_usage ---
    # user_id para relatórios por usuário
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_llm_usage_user_id
        ON llm_usage (user_id)
    """)
    # criado_em para análise temporal e billing
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_llm_usage_criado_em
        ON llm_usage (criado_em DESC)
    """)

    # --- audit_log ---
    # target_user_id para auditoria por usuário afetado
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_target_user_id
        ON audit_log (target_user_id)
    """)

    # --- provider_alerts ---
    # user_id_afetado para alertas por usuário
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_provider_alerts_user_id_afetado
        ON provider_alerts (user_id_afetado)
    """)

    # --- mercadopago_events ---
    # user_id para eventos por usuário
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mercadopago_events_user_id
        ON mercadopago_events (user_id)
    """)

    print("[perf] 21 índices abrangentes criados com sucesso")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_leads_user_id")
    op.execute("DROP INDEX IF EXISTS idx_leads_status")
    op.execute("DROP INDEX IF EXISTS idx_leads_sdr_stage")
    op.execute("DROP INDEX IF EXISTS idx_leads_criado_em")
    op.execute("DROP INDEX IF EXISTS idx_licencas_usuario_id")
    op.execute("DROP INDEX IF EXISTS idx_ciclos_user_id_v2")
    op.execute("DROP INDEX IF EXISTS idx_sdr_learning_user_id_v2")
    op.execute("DROP INDEX IF EXISTS idx_sdr_learning_lead_id")
    op.execute("DROP INDEX IF EXISTS idx_pipeline_failures_tenant_id")
    op.execute("DROP INDEX IF EXISTS idx_pipeline_failures_criado_em")
    op.execute("DROP INDEX IF EXISTS idx_jobs_status")
    op.execute("DROP INDEX IF EXISTS idx_jobs_tenant_id")
    op.execute("DROP INDEX IF EXISTS idx_jobs_worker_heartbeat")
    op.execute("DROP INDEX IF EXISTS idx_interacoes_lead_id_v2")
    op.execute("DROP INDEX IF EXISTS idx_site_visitas_lead_id")
    op.execute("DROP INDEX IF EXISTS idx_site_visitas_criado_em")
    op.execute("DROP INDEX IF EXISTS idx_llm_usage_user_id")
    op.execute("DROP INDEX IF EXISTS idx_llm_usage_criado_em")
    op.execute("DROP INDEX IF EXISTS idx_audit_log_target_user_id")
    op.execute("DROP INDEX IF EXISTS idx_provider_alerts_user_id_afetado")
    op.execute("DROP INDEX IF EXISTS idx_mercadopago_events_user_id")
    print("[perf] 21 índices abrangentes removidos")
