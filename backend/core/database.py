# database.py - PostgreSQL Multi-Tenant

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os
import json

try:
    from .proxy_models import (
        ALLOWED_PROXY_MODELS,
        PROXY_BUILDER_MODEL,
        PROXY_DEFAULT_MODEL,
        PROXY_LIGHT_MODEL,
        PROXY_PROVIDER,
    )
except ImportError:  # compat quando backend/core esta no sys.path
    from proxy_models import (  # type: ignore
        ALLOWED_PROXY_MODELS,
        PROXY_BUILDER_MODEL,
        PROXY_DEFAULT_MODEL,
        PROXY_LIGHT_MODEL,
        PROXY_PROVIDER,
    )

# ===== CONFIGURAÇÃO =====
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL não configurado no .env")

_is_postgres = DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://"))
_connect_args = {"options": "-csearch_path=public"} if _is_postgres else {}

# Connection pool otimizado para produção
# pool_size: conexões mantidas abertas (default 5)
# max_overflow: conexões extras além do pool_size
# pool_recycle: reconecta após 1 hora para evitar conexões stale
# pool_timeout: tempo máximo esperando uma conexão disponível
_engine_kwargs = {
    "pool_pre_ping": True,
    "connect_args": _connect_args,
    "echo": False,  # Desabilitar em produção
}
if _is_postgres:
    _engine_kwargs.update(
        pool_size=20,
        max_overflow=30,
        pool_recycle=3600,
        pool_timeout=30,
    )

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
_SCHEMA_INIT_LOCK_KEY = "fralib_schema_init"

# ===== DEPENDENCY INJECTION =====


def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# LEGADO REMOVIDO 2026-06-20
# - criar_schema_tenant(): NUNCA chamada, schema por tenant é legacy
# - criar_tabelas_globais(): NUNCA chamada
# - classes LeadDB, CicloDB, LogDB, LicencaDB: NUNCA usadas pelo pipeline
# FONTE CANÔNICA: public.leads com user_id (multi-tenant row-level)
# VER: docs/SCHEMA_DUPLICATION_AUDIT.md
# ============================================================

# FIM DO CÓDIGO LEGADO - Vá para # ===== INICIALIZAÇÃO =====

# (Corpo removido: criar_schema_tenant, criar_tabelas_globais, LeadDB, CicloDB, LogDB, LicencaDB)
# VER docs/SCHEMA_DUPLICATION_AUDIT.md

# ===== INICIALIZAÇÃO =====


def inicializar_database():
    """Inicializa o banco de dados criando tabelas base"""
    with engine.connect() as conn:
        conn.execute(text("SET lock_timeout TO '3s'"))
        conn.execute(text("SET statement_timeout TO '60s'"))
        lock_acquired = conn.execute(
            text("SELECT pg_try_advisory_lock(hashtext(:lock_key))"),
            {"lock_key": _SCHEMA_INIT_LOCK_KEY},
        ).scalar()
        if not lock_acquired:
            print("[Startup] inicializar_database skipped (schema lock ocupado)")
            return False
        # Criar tabela de usuários (schema public)
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                nome VARCHAR(255),
                tenant_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        )
        # Keep fresh/test databases aligned with the public auth and dashboard
        # contract. Production may already have these columns from older
        # migrations, so every statement must remain idempotent.
        for statement in (
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS senha_hash VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS plano VARCHAR(50) DEFAULT 'free'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(50) DEFAULT 'free'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(30) DEFAULT 'user'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'ativa'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS creditos INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS creditos_max INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_expires_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS criado_em TIMESTAMP DEFAULT NOW()",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_confirmado BOOLEAN DEFAULT TRUE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS confirm_token TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS confirm_expires TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS registro_ip VARCHAR(120)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS telefone VARCHAR(50)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_expires TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_version VARCHAR(80)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS privacy_accepted_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS privacy_version VARCHAR(80)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS legal_acceptance_ip VARCHAR(120)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS payment_provider VARCHAR(40)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS mercadopago_payer_id VARCHAR(120)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS mercadopago_subscription_id VARCHAR(120)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS mercadopago_last_payment_id VARCHAR(120)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS niche VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS nicho VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS endereco TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS origem VARCHAR(120)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS cep VARCHAR(20)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS rua VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS bairro VARCHAR(120)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS cidade VARCHAR(120)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS estado VARCHAR(10)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS sdr_horario_config JSONB",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ultimo_deploy_at TIMESTAMP",
        ):
            conn.execute(text(statement))

        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS user_configs (
                user_id INTEGER NOT NULL,
                config_key VARCHAR(120) NOT NULL,
                config_value TEXT,
                updated_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, config_key)
            )
            """)
        )

        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS leads (
                id VARCHAR(100) PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                cidade VARCHAR(120),
                segmento VARCHAR(120),
                telefone VARCHAR(50),
                whatsapp VARCHAR(50),
                telefone_whatsapp VARCHAR(50),
                rating FLOAT DEFAULT 0,
                score INTEGER DEFAULT 0,
                tier VARCHAR(30),
                status VARCHAR(50) DEFAULT 'pendente',
                url_site VARCHAR(500),  -- LEGADO: manter para compat, usar site_url
                site_url VARCHAR(500),  -- CANONICO: fonte de verdade para URL do site
                html_gerado TEXT,
                dados_completos JSONB,
                user_id INTEGER,
                ciclo INTEGER DEFAULT 0,
                criado_em TIMESTAMP DEFAULT NOW(),
                atualizado_em TIMESTAMP DEFAULT NOW(),
                processado BOOLEAN DEFAULT FALSE,
                tentativas INTEGER DEFAULT 0,
                observacoes TEXT,
                valor_venda NUMERIC(12,2) DEFAULT 0
            )
        """)
        )
        for statement in (
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS valor_venda NUMERIC(12,2) DEFAULT 0",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS url_site VARCHAR(500)",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS user_id INTEGER",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS ciclo INTEGER DEFAULT 0",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS processado BOOLEAN DEFAULT FALSE",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS tentativas INTEGER DEFAULT 0",
        ):
            conn.execute(text(statement))
        conn.execute(text("DROP INDEX IF EXISTS idx_leads_unique"))
        conn.execute(
            text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_tenant_phone_city_unique
            ON leads (user_id, telefone, cidade)
            WHERE telefone IS NOT NULL AND trim(telefone) <> ''
              AND cidade IS NOT NULL AND trim(cidade) <> ''
        """)
        )

        # Criar tabela de licenças
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS licencas (
                id VARCHAR(100) PRIMARY KEY,
                cliente VARCHAR(255),
                email VARCHAR(255),
                plano VARCHAR(50),
                valor NUMERIC(12,2) DEFAULT 0,
                chave VARCHAR(255),
                status VARCHAR(50) DEFAULT 'ativa',
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expira TIMESTAMP,
                ultimo_acesso TIMESTAMP
            )
        """)
        )

        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS config_pipeline (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                nicho VARCHAR(255) DEFAULT '',
                cidade VARCHAR(255) DEFAULT '',
                pipeline_status VARCHAR(30) DEFAULT 'parado',
                volume_leads_target INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        )

        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS ciclos (
                id SERIAL PRIMARY KEY,
                numero INTEGER,
                cidade VARCHAR(120),
                segmento VARCHAR(120),
                leads_buscados INTEGER DEFAULT 0,
                sites_gerados INTEGER DEFAULT 0,
                enviados INTEGER DEFAULT 0,
                erros INTEGER DEFAULT 0,
                iniciado_em TIMESTAMP DEFAULT NOW(),
                concluido_em TIMESTAMP,
                user_id INTEGER
            )
        """)
        )

        # Criar tabela pipeline_queue (fila persistente de jobs)
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS pipeline_queue (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                segmento VARCHAR(100),
                cidade VARCHAR(100),
                quantidade INTEGER DEFAULT 10,
                score_minimo INTEGER DEFAULT 45,
                status VARCHAR(20) DEFAULT 'pendente',
                criado_em TIMESTAMP DEFAULT NOW(),
                iniciado_em TIMESTAMP,
                concluido_em TIMESTAMP,
                erro TEXT
            )
        """)
        )

        # Tabela pipeline_state: lock de pipeline por tenant (1 pipeline por vez)
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS pipeline_state (
                tenant_id INTEGER PRIMARY KEY,
                rodando BOOLEAN DEFAULT FALSE,
                pausado BOOLEAN DEFAULT FALSE,
                config JSONB DEFAULT '{}'::jsonb,
                updated_at TIMESTAMP DEFAULT NOW(),
                iniciado_em TIMESTAMP
            )
        """)
        )

        # Criar tabela sdr_learning (aprendizado do Franz SDR)
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS sdr_learning (
                id SERIAL PRIMARY KEY,
                lead_id TEXT,
                user_id INTEGER,
                segmento TEXT,
                tier TEXT,
                mensagem_usada TEXT,
                resultado TEXT,
                observacao TEXT,
                nicho TEXT,
                intent TEXT,
                reply TEXT,
                next_stage TEXT,
                criado_em TEXT
            )
        """)
        )
        conn.execute(text("ALTER TABLE sdr_learning ADD COLUMN IF NOT EXISTS variant VARCHAR(10)"))
        conn.execute(text("ALTER TABLE sdr_learning ADD COLUMN IF NOT EXISTS stage VARCHAR(40)"))
        conn.execute(text("ALTER TABLE sdr_learning ADD COLUMN IF NOT EXISTS price_tier INTEGER DEFAULT 0"))

        # ===== JOB QUEUE PERSISTENTE =====
        # Tabela `jobs`: fila generica de tarefas em background com retry e crash recovery.
        # status: pending | running | completed | failed_retriable | failed_permanent
        # Worker daemon faz SELECT FOR UPDATE SKIP LOCKED em (status='pending' AND next_retry_at <= NOW())
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                tipo VARCHAR(80) NOT NULL,
                payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                tenant_id INTEGER,
                status VARCHAR(30) NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                last_error TEXT,
                last_phase VARCHAR(80),
                idempotency_key VARCHAR(120) UNIQUE,
                run_id VARCHAR(100),
                checkpoint_id VARCHAR(120),
                worker_id VARCHAR(80),
                worker_heartbeat TIMESTAMP,
                next_retry_at TIMESTAMP DEFAULT NOW(),
                criado_em TIMESTAMP DEFAULT NOW(),
                iniciado_em TIMESTAMP,
                concluido_em TIMESTAMP,
                priority INTEGER NOT NULL DEFAULT 2
            )
        """)
        )
        conn.execute(
            text(
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 2"
            )
        )
        conn.execute(
            text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS run_id VARCHAR(100)")
        )
        conn.execute(
            text("ALTER TABLE IF EXISTS jobs ALTER COLUMN run_id TYPE VARCHAR(100)")
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_jobs_claim
            ON jobs (status, next_retry_at)
            WHERE status = 'pending'
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_jobs_run_id
            ON jobs (run_id)
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_jobs_tenant
            ON jobs (tenant_id, status)
        """)
        )

        # Tabela `pipeline_failures`: jobs que esgotaram os retries automaticos.
        # Aparece pro cliente no dashboard com botao "tentar de novo manualmente".
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS pipeline_failures (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
                lead_id TEXT,
                lead_nome TEXT,
                fase VARCHAR(80),
                mensagem_amigavel TEXT,
                erro_tecnico TEXT,
                tentativas_automaticas INTEGER DEFAULT 0,
                checkpoint_id VARCHAR(120),
                payload JSONB,
                criado_em TIMESTAMP DEFAULT NOW(),
                visto_pelo_usuario BOOLEAN DEFAULT FALSE,
                resolvido BOOLEAN DEFAULT FALSE,
                resolvido_em TIMESTAMP
            )
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_failures_tenant
            ON pipeline_failures (tenant_id, resolvido, criado_em DESC)
        """)
        )

        # PR8: BYOK Anthropic - cliente do plano Pro guarda a propria
        # API key criptografada (Fernet). O pipeline le esta coluna
        # quando _current_user_id e Pro, senao usa ANTHROPIC_API_KEY do .env.
        conn.execute(
            text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS anthropic_key_encrypted TEXT
        """)
        )

        # Configuracao canonica de modelos por agente. Provider "anthropic"
        # usa ANTHROPIC_BASE_URL, que em producao aponta para o LiteLLM da VPS.
        _allowed_proxy_model_sql = ", ".join(
            f"'{model.replace(chr(39), chr(39) + chr(39))}'"
            for model in sorted(ALLOWED_PROXY_MODELS)
        )
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS agent_model_configs (
                agent_name VARCHAR(80) PRIMARY KEY,
                provider VARCHAR(50) NOT NULL DEFAULT 'anthropic',
                model_id VARCHAR(120) NOT NULL,
                fallback_provider VARCHAR(50),
                fallback_model_id VARCHAR(120),
                temperature NUMERIC(4,2),
                top_p NUMERIC(4,2),
                max_tokens INTEGER,
                enabled BOOLEAN DEFAULT TRUE,
                atualizado_em TIMESTAMP DEFAULT NOW(),
                atualizado_por INTEGER
            )
        """)
        )
        conn.execute(text("ALTER TABLE agent_model_configs ADD COLUMN IF NOT EXISTS fallback_provider VARCHAR(50)"))
        conn.execute(text("ALTER TABLE agent_model_configs ADD COLUMN IF NOT EXISTS fallback_model_id VARCHAR(120)"))
        conn.execute(text("ALTER TABLE agent_model_configs ADD COLUMN IF NOT EXISTS top_p NUMERIC(4,2)"))
        conn.execute(text("ALTER TABLE agent_model_configs ADD COLUMN IF NOT EXISTS atualizado_por INTEGER"))
        for _agent_name, _model_id, _temperature, _max_tokens in (
            ("agente_nicho", PROXY_LIGHT_MODEL, 0.30, 4000),
            ("agente_variacao", PROXY_LIGHT_MODEL, 0.40, 1500),
            ("arquiteto_mestre", PROXY_DEFAULT_MODEL, 0.35, 6000),
            ("designer_prd", PROXY_DEFAULT_MODEL, 0.35, 6000),
            ("builder_renderer", PROXY_BUILDER_MODEL, 0.75, 16000),
            ("franz", PROXY_DEFAULT_MODEL, 0.55, 1200),
            ("validador", PROXY_LIGHT_MODEL, 0.20, 2000),
            ("curadoria", PROXY_DEFAULT_MODEL, 0.40, 3000),
        ):
            conn.execute(
                text("""
                INSERT INTO agent_model_configs (
                    agent_name, provider, model_id, temperature, max_tokens,
                    enabled, atualizado_em
                )
                VALUES (
                    :agent_name, 'anthropic', :model_id,
                    :temperature, :max_tokens, TRUE, NOW()
                )
                ON CONFLICT (agent_name) DO NOTHING
            """),
                {
                    "agent_name": _agent_name,
                    "model_id": _model_id,
                    "temperature": _temperature,
                    "max_tokens": _max_tokens,
                },
            )
        for statement, params in (
            (
                """
                UPDATE agent_model_configs
                   SET provider = :provider,
                       model_id = :light_model,
                       fallback_provider = NULL,
                       fallback_model_id = NULL,
                       atualizado_em = NOW()
                 WHERE agent_name IN (
                       'agente_nicho', 'agente_variacao',
                       'validador'
                 )
                   AND (
                       provider <> :provider
                       OR model_id LIKE '%/%'
                       OR model_id NOT IN (""" + _allowed_proxy_model_sql + """)
                       OR model_id = 'gemini-2.5-flash'
                       OR fallback_provider IS NOT NULL
                       OR fallback_model_id IS NOT NULL
                   )
                """,
                {"provider": PROXY_PROVIDER, "light_model": PROXY_LIGHT_MODEL},
            ),
            (
                """
                UPDATE agent_model_configs
                   SET provider = :provider,
                       model_id = :default_model,
                       fallback_provider = NULL,
                       fallback_model_id = NULL,
                       atualizado_em = NOW()
                 WHERE agent_name IN (
                       'alex', 'arquiteto_mestre',
                       'curadoria', 'designer_prd', 'franz', 'jina_intel', 'liam', 'liz',
                       'open_design', 'section_editor', 'skill_renderer', 'theo'
                 )
                   AND (
                       provider <> :provider
                       OR model_id LIKE '%/%'
                       OR model_id NOT IN (""" + _allowed_proxy_model_sql + """)
                       OR model_id = 'deepseek-v4-flash'
                       OR fallback_provider IS NOT NULL
                       OR fallback_model_id IS NOT NULL
                   )
                """,
                {"provider": PROXY_PROVIDER, "default_model": PROXY_DEFAULT_MODEL},
            ),
            (
                """
                UPDATE agent_model_configs
                   SET provider = :provider,
                       model_id = :builder_model,
                       fallback_provider = NULL,
                       fallback_model_id = NULL,
                       atualizado_em = NOW()
                 WHERE agent_name = 'builder_renderer'
                   AND (
                       provider <> :provider
                       OR model_id LIKE '%/%'
                       OR model_id NOT IN (""" + _allowed_proxy_model_sql + """)
                       OR model_id IN ('deepseek-v4-flash', 'gemini-3.5-flash', 'gemini-2.5-flash')
                       OR fallback_provider IS NOT NULL
                       OR fallback_model_id IS NOT NULL
                   )
                """,
                {"provider": PROXY_PROVIDER, "builder_model": PROXY_BUILDER_MODEL},
            ),
        ):
            conn.execute(text(statement), params)
        conn.execute(text("DELETE FROM agent_model_configs WHERE agent_name = 'bryan'"))

        # Idempotencia + auditoria dos webhooks do Mercado Pago.
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS mercadopago_events (
                event_id VARCHAR(180) PRIMARY KEY,
                tipo VARCHAR(120),
                user_id INTEGER,
                payment_id VARCHAR(120),
                processado BOOLEAN DEFAULT FALSE,
                erro TEXT,
                raw_payload TEXT,
                criado_em TIMESTAMP DEFAULT NOW(),
                processado_em TIMESTAMP
            )
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_mercadopago_events_payment
            ON mercadopago_events (payment_id, criado_em DESC)
        """)
        )

        # Hermes watchdog: append-only operational incidents. The watchdog is
        # read-only for runtime state; this table records evidence and blocked
        # actions without changing queues/checkpoints.
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS hermes_incidents (
                id SERIAL PRIMARY KEY,
                severity VARCHAR(20) NOT NULL,
                incident_type VARCHAR(80) NOT NULL,
                title TEXT NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'open',
                evidence JSONB DEFAULT '{}'::jsonb,
                recommended_action TEXT,
                source VARCHAR(80) DEFAULT 'hermes',
                actor_id INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_hermes_incidents_created
            ON hermes_incidents (created_at DESC)
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_hermes_incidents_status
            ON hermes_incidents (status, severity, created_at DESC)
        """)
        )

        # ===== TABELAS DE OBSERVABILIDADE =====
        # PRD #10: pipeline_traces — traces completos por run
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS pipeline_traces (
                trace_id VARCHAR(30) PRIMARY KEY,
                run_id VARCHAR(100),
                tenant_id INTEGER,
                lead_nome VARCHAR(255),
                nicho VARCHAR(100),
                tier VARCHAR(30),
                complexidade VARCHAR(30),
                duracao_total_ms INTEGER,
                status VARCHAR(30),
                total_input_tokens INTEGER DEFAULT 0,
                total_output_tokens INTEGER DEFAULT 0,
                total_cache_hit INTEGER DEFAULT 0,
                custo_total_usd NUMERIC(10,4) DEFAULT 0,
                total_chamadas_llm INTEGER DEFAULT 0,
                spans_json JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        )
        conn.execute(text("ALTER TABLE pipeline_traces ADD COLUMN IF NOT EXISTS run_id VARCHAR(100)"))
        conn.execute(text("ALTER TABLE IF EXISTS pipeline_traces ALTER COLUMN run_id TYPE VARCHAR(100)"))
        conn.execute(text("ALTER TABLE pipeline_traces ADD COLUMN IF NOT EXISTS tenant_id INTEGER"))
        conn.execute(text("ALTER TABLE pipeline_traces ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()"))
        conn.execute(text("ALTER TABLE pipeline_traces ADD COLUMN IF NOT EXISTS status VARCHAR(30)"))
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_traces_tenant
            ON pipeline_traces (tenant_id, created_at DESC)
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_traces_status
            ON pipeline_traces (status, created_at DESC)
        """)
        )

        # PRD #4: pipeline_token_usage — custo LLM agregado por run
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS pipeline_token_usage (
                id SERIAL PRIMARY KEY,
                run_id VARCHAR(100) UNIQUE,
                tenant_id INTEGER,
                lead_nome VARCHAR(255),
                nicho VARCHAR(100),
                duracao_s NUMERIC(10,1),
                total_input_tokens INTEGER DEFAULT 0,
                total_output_tokens INTEGER DEFAULT 0,
                cache_hit_ratio NUMERIC(5,1) DEFAULT 0,
                custo_total_usd NUMERIC(10,4) DEFAULT 0,
                por_agente JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        )
        conn.execute(text("ALTER TABLE IF EXISTS pipeline_token_usage ALTER COLUMN run_id TYPE VARCHAR(100)"))
        conn.execute(text("ALTER TABLE pipeline_token_usage ADD COLUMN IF NOT EXISTS tenant_id INTEGER"))
        conn.execute(text("ALTER TABLE pipeline_token_usage ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()"))
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_token_usage_tenant
            ON pipeline_token_usage (tenant_id, created_at DESC)
        """)
        )

        # ===== LLM BUDGET LEDGER =====
        # Registro por chamada LLM para custo, auditoria e controle futuro de rate limit.
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS llm_budget_ledger (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER,
                job_id INTEGER,
                run_id VARCHAR(100),
                phase VARCHAR(80),
                agent VARCHAR(80),
                provider VARCHAR(50) DEFAULT 'anthropic',
                model VARCHAR(100) NOT NULL,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cache_read_tokens INTEGER DEFAULT 0,
                cache_created_tokens INTEGER DEFAULT 0,
                cost_usd NUMERIC(12,6) DEFAULT 0,
                latency_ms INTEGER,
                status VARCHAR(30) DEFAULT 'success',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        )
        conn.execute(text("ALTER TABLE llm_budget_ledger ADD COLUMN IF NOT EXISTS tenant_id INTEGER"))
        conn.execute(text("ALTER TABLE llm_budget_ledger ADD COLUMN IF NOT EXISTS job_id INTEGER"))
        conn.execute(text("ALTER TABLE llm_budget_ledger ADD COLUMN IF NOT EXISTS run_id VARCHAR(100)"))
        conn.execute(text("ALTER TABLE llm_budget_ledger ADD COLUMN IF NOT EXISTS phase VARCHAR(80)"))
        conn.execute(text("ALTER TABLE llm_budget_ledger ADD COLUMN IF NOT EXISTS provider VARCHAR(50) DEFAULT 'anthropic'"))
        conn.execute(text("ALTER TABLE llm_budget_ledger ADD COLUMN IF NOT EXISTS latency_ms INTEGER"))
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_llm_budget_tenant_created
            ON llm_budget_ledger (tenant_id, created_at DESC)
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_llm_budget_run
            ON llm_budget_ledger (run_id, created_at DESC)
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_llm_budget_agent_model
            ON llm_budget_ledger (agent, model, created_at DESC)
        """)
        )

        # Provider keys podem ter sido criadas por migration antiga com CHECK
        # restrito. Mantem o banco compativel com o provider OpenRouter.
        conn.execute(
            text("""
            ALTER TABLE IF EXISTS provider_keys
            DROP CONSTRAINT IF EXISTS provider_keys_provider_chk
        """)
        )
        conn.execute(
            text("""
            ALTER TABLE IF EXISTS provider_keys
            ADD CONSTRAINT provider_keys_provider_chk
            CHECK (provider IN ('anthropic', 'openai', 'google', 'groq', 'openrouter', 'deepseek', 'moonshot', 'qwen', 'custom'))
        """)
        )

        # ===== PROVIDER RATE LIMITS =====
        # Fonte DB para limites/custos por provider/modelo; usada antes de aumentar paralelismo.
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS provider_rate_limits (
                id SERIAL PRIMARY KEY,
                provider VARCHAR(50) NOT NULL,
                model VARCHAR(100) NOT NULL,
                rpm INTEGER DEFAULT 60,
                tpm INTEGER DEFAULT 40000,
                max_concurrency INTEGER DEFAULT 1,
                daily_budget_usd NUMERIC(12,2) DEFAULT 50.00,
                cooldown_seconds INTEGER DEFAULT 60,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(provider, model)
            )
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_provider_rate_limits_provider_model
            ON provider_rate_limits (provider, model)
        """)
        )
        conn.execute(
            text("""
            INSERT INTO provider_rate_limits
                (provider, model, rpm, tpm, max_concurrency, daily_budget_usd, cooldown_seconds)
            VALUES
                ('anthropic', 'claude-opus-4-7', 30, 30000, 1, 150.00, 90),
                ('anthropic', 'claude-opus-4-8', 30, 30000, 1, 150.00, 90),
                ('anthropic', 'claude-opus-4-20250514', 30, 30000, 1, 150.00, 90),
                ('anthropic', 'claude-sonnet-4-6', 45, 40000, 1, 75.00, 60),
                ('anthropic', 'claude-sonnet-4-20250514', 45, 40000, 1, 75.00, 60),
                ('anthropic', 'claude-haiku-4-5', 90, 50000, 1, 35.00, 30),
                ('anthropic', 'claude-haiku-4-20250514', 90, 50000, 1, 35.00, 30),
                ('anthropic', 'fralib-fast-cheap', 60, 50000, 1, 0.00, 900),
                ('anthropic', 'fralib-json-repair', 45, 50000, 1, 0.00, 900),
                ('anthropic', 'fralib-agent-balanced', 30, 40000, 1, 0.00, 900),
                ('anthropic', 'fralib-research', 20, 40000, 1, 0.00, 900),
                ('anthropic', 'fralib-builder-strong', 10, 40000, 1, 0.00, 900),
                ('anthropic', 'fast', 90, 50000, 1, 35.00, 30),
                ('anthropic', 'gpt-5.4-mini', 90, 50000, 1, 35.00, 30),
                ('anthropic', 'deepseek-v4-flash', 45, 40000, 1, 75.00, 60),
                ('anthropic', 'gemini-2.5-flash', 90, 50000, 1, 35.00, 30)
            ON CONFLICT (provider, model) DO NOTHING
        """)
        )

        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS llm_cost_estimate NUMERIC(12,6) DEFAULT 0"))
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS llm_tokens_used INTEGER DEFAULT 0"))

        # Lead Supply: motor separado Hunter/Caio -> inventario -> pipeline unitária.
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS lead_supply_config (
                tenant_id INTEGER PRIMARY KEY,
                segmentos JSONB NOT NULL DEFAULT '[]'::jsonb,
                cidades JSONB NOT NULL DEFAULT '[]'::jsonb,
                meta_diaria INTEGER NOT NULL DEFAULT 1,
                estoque_minimo INTEGER NOT NULL DEFAULT 3,
                estoque_alvo INTEGER NOT NULL DEFAULT 10,
                score_minimo INTEGER NOT NULL DEFAULT 45,
                provider VARCHAR(40) NOT NULL DEFAULT 'hunter',
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                hunter_pausado BOOLEAN NOT NULL DEFAULT FALSE,
                producao_pausada BOOLEAN NOT NULL DEFAULT FALSE,
                criado_em TIMESTAMP DEFAULT NOW(),
                atualizado_em TIMESTAMP DEFAULT NOW()
            )
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS lead_inventory (
                id VARCHAR(80) PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                origem VARCHAR(40) DEFAULT 'hunter',
                segmento VARCHAR(120),
                cidade VARCHAR(120),
                nome VARCHAR(255) NOT NULL,
                telefone VARCHAR(60),
                whatsapp VARCHAR(60),
                rating NUMERIC(3,1) DEFAULT 0,
                reviews_count INTEGER DEFAULT 0,
                website VARCHAR(500),
                endereco VARCHAR(700),
                maps_url VARCHAR(700),
                place_id VARCHAR(180),
                dedupe_key VARCHAR(80) NOT NULL,
                status VARCHAR(40) NOT NULL DEFAULT 'raw',
                score_caio INTEGER DEFAULT 0,
                tier VARCHAR(40),
                caio_motivo TEXT,
                lead_id VARCHAR(100),
                dados JSONB NOT NULL DEFAULT '{}'::jsonb,
                erro TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                locked_by VARCHAR(80),
                locked_until TIMESTAMP,
                reservado_em TIMESTAMP,
                produzido_em TIMESTAMP,
                criado_em TIMESTAMP DEFAULT NOW(),
                atualizado_em TIMESTAMP DEFAULT NOW()
            )
        """)
        )
        conn.execute(
            text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_lead_inventory_tenant_dedupe
            ON lead_inventory (tenant_id, dedupe_key)
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_lead_inventory_tenant_status
            ON lead_inventory (tenant_id, status, atualizado_em DESC)
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS lead_supply_events (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                source VARCHAR(40) NOT NULL,
                level VARCHAR(20) NOT NULL DEFAULT 'info',
                message TEXT NOT NULL,
                payload JSONB DEFAULT '{}'::jsonb,
                criado_em TIMESTAMP DEFAULT NOW()
            )
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_lead_supply_events_tenant
            ON lead_supply_events (tenant_id, criado_em DESC)
        """)
        )

        # PRD #10: pipeline_run_spans — spans individuais por fase (observabilidade real)
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS pipeline_run_spans (
                id SERIAL PRIMARY KEY,
                run_id VARCHAR(100) NOT NULL,
                trace_id VARCHAR(30),
                tenant_id INTEGER,
                lead_id VARCHAR(100),
                fase_num INTEGER,
                fase_nome VARCHAR(80) NOT NULL,
                agente VARCHAR(80),
                modelo VARCHAR(50),
                started_at TIMESTAMP DEFAULT NOW(),
                finished_at TIMESTAMP,
                duracao_ms INTEGER,
                status VARCHAR(30) DEFAULT 'running',
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cache_read_tokens INTEGER DEFAULT 0,
                cache_created_tokens INTEGER DEFAULT 0,
                custo_usd NUMERIC(10,6) DEFAULT 0,
                erro TEXT,
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """)
        )
        conn.execute(text("ALTER TABLE IF EXISTS pipeline_run_spans ALTER COLUMN run_id TYPE VARCHAR(100)"))
        conn.execute(text("ALTER TABLE IF EXISTS pipeline_ledgers ALTER COLUMN run_id TYPE VARCHAR(100)"))
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_spans_run
            ON pipeline_run_spans (run_id, fase_num)
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_spans_tenant
            ON pipeline_run_spans (tenant_id, started_at DESC)
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_spans_status
            ON pipeline_run_spans (status, started_at DESC)
        """)
        )

        conn.commit()
        try:
            conn.execute(
                text("SELECT pg_advisory_unlock(hashtext(:lock_key))"),
                {"lock_key": _SCHEMA_INIT_LOCK_KEY},
            )
        except Exception:
            pass

    print("[Database] ✅ Banco inicializado")
    return True


# ===== PIPELINE STATE (Multi-tenant) =====


def get_pipeline_state(db: Session, tenant_id: int):
    """Retorna o estado do pipeline para um tenant especifico"""
    query = text("""
        SELECT rodando, pausado, config, updated_at, iniciado_em
        FROM public.pipeline_state
        WHERE tenant_id = :tenant_id
    """)
    result = db.execute(query, {"tenant_id": tenant_id}).fetchone()

    if result:
        return {
            "rodando": result[0],
            "pausado": result[1],
            "config": result[2] or {},
            "updated_at": result[3],
            "iniciado_em": result[4],
        }
    else:
        return {
            "rodando": False,
            "pausado": False,
            "config": {},
            "updated_at": None,
            "iniciado_em": None,
        }


def update_pipeline_state(
    db: Session, tenant_id: int, rodando=None, pausado=None, config=None
):
    """Atualiza o estado do pipeline para um tenant específico"""
    # Verificar se já existe registro
    check_query = text(
        "SELECT tenant_id FROM public.pipeline_state WHERE tenant_id = :tenant_id"
    )
    exists = db.execute(check_query, {"tenant_id": tenant_id}).fetchone()

    if exists:
        # UPDATE
        updates = []
        params = {"tenant_id": tenant_id}

        if rodando is not None:
            updates.append("rodando = :rodando")
            params["rodando"] = rodando
            if rodando:
                updates.append("iniciado_em = NOW()")
            else:
                updates.append("iniciado_em = NULL")

        if pausado is not None:
            updates.append("pausado = :pausado")
            params["pausado"] = pausado

        if config is not None:
            updates.append("config = :config")
            params["config"] = json.dumps(config)

        if updates:
            updates.append("updated_at = NOW()")
            query = text(
                f"UPDATE public.pipeline_state SET {', '.join(updates)} WHERE tenant_id = :tenant_id"
            )
            db.execute(query, params)
            db.commit()
    else:
        # INSERT
        query = text("""
            INSERT INTO public.pipeline_state (tenant_id, rodando, pausado, config, updated_at, iniciado_em)
            VALUES (:tenant_id, :rodando, :pausado, :config, NOW(), CASE WHEN :rodando THEN NOW() ELSE NULL END)
        """)
        db.execute(
            query,
            {
                "tenant_id": tenant_id,
                "rodando": rodando if rodando is not None else False,
                "pausado": pausado if pausado is not None else False,
                "config": json.dumps(config if config is not None else {}),
            },
        )
        db.commit()


def reset_stale_pipeline_locks(
    db: Session, older_than_minutes: int = 5, tenant_id=None
):
    """Compat legado: retorna locks antigos sem mutar pipeline_state.

    A fonte canonica de execucao e `jobs`; recuperacao real deve usar
    job_queue.reap_dead_workers(). `pipeline_state.rodando` permanece apenas
    para auditoria de divergencia durante a fase de migracao.
    """
    params = {"mins": older_than_minutes}
    tenant_filter = ""
    if tenant_id is not None:
        tenant_filter = "AND tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id

    query = text(f"""
        SELECT tenant_id
        FROM public.pipeline_state
        WHERE rodando = true
          {tenant_filter}
          AND COALESCE(updated_at, iniciado_em, NOW() - (:mins || ' minutes')::interval - interval '1 second')
              < NOW() - (:mins || ' minutes')::interval
    """)
    rows = db.execute(query, params).fetchall()
    return [r[0] for r in rows]
