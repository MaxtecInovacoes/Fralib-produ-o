# database.py - PostgreSQL Multi-Tenant

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os
import json

# ===== CONFIGURAÇÃO =====
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL não configurado no .env")

engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True,
    connect_args={"options": "-csearch_path=public"}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ===== DEPENDENCY INJECTION =====

def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===== SCHEMAS MULTI-TENANT =====

async def criar_schema_tenant(schema_name: str):
    """Cria schema PostgreSQL isolado para um tenant"""
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.leads (
                id VARCHAR(100) PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                cidade VARCHAR(100),
                segmento VARCHAR(100),
                telefone VARCHAR(50),
                whatsapp VARCHAR(50),
                rating FLOAT DEFAULT 0,
                score INTEGER DEFAULT 0,
                tier VARCHAR(20),
                status VARCHAR(50) DEFAULT 'pendente',
                site_url VARCHAR(500),
                html_gerado TEXT,
                dados_completos JSONB
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.ciclos (
                id SERIAL PRIMARY KEY,
                numero INTEGER,
                cidade VARCHAR(100),
                segmento VARCHAR(100),
                quantidade INTEGER,
                criado_em TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.logs (
                id SERIAL PRIMARY KEY,
                mensagem TEXT,
                tipo VARCHAR(50) DEFAULT 'info',
                criado_em TIMESTAMP DEFAULT NOW()
            )
        """))

def criar_tabelas_globais():
    """Cria tabelas globais (usuários, licenças)"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.usuarios (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                senha_hash VARCHAR(255) NOT NULL,
                nome VARCHAR(255) NOT NULL,
                empresa VARCHAR(255),
                plano VARCHAR(50) DEFAULT 'FREE',
                schema_name VARCHAR(100) UNIQUE NOT NULL,
                whatsapp_instance VARCHAR(100),
                telegram_chat_id VARCHAR(100),
                ativo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.licencas (
                id VARCHAR(100) PRIMARY KEY,
                usuario_id INT NOT NULL,
                plano VARCHAR(50),
                valor FLOAT,
                status VARCHAR(50),
                leads_mes INT,
                sites_mes INT,
                whatsapp_incluido BOOLEAN,
                telegram_incluido BOOLEAN,
                data_inicio TIMESTAMP DEFAULT NOW(),
                renovacao_automatica BOOLEAN DEFAULT TRUE
            )
        """))

# ===== CLASSES DE ACESSO =====

class LeadDB:
    def __init__(self, db):
        self.db = db
        # Whitelist de colunas permitidas (proteção SQL Injection)
        self.ALLOWED_COLUMNS_LEADS = {"nome", "email", "telefone", "whatsapp", "cidade", "segmento", "status", "rating", "score", "tier", "qualificacao", "observacoes", "data_atualizacao"}
        self.ALLOWED_COLUMNS_CICLOS = {"status", "leads_processados", "leads_qualificados", "data_fim", "resultado"}

    def criar(self, lead: Dict[str, Any]) -> str:
        """Cria novo lead no banco de dados"""
        # Garantir valores padrão para campos obrigatórios
        lead.setdefault('rating', 0.0)
        lead.setdefault('score', 0)
        lead.setdefault('tier', 'STANDARD')
        lead.setdefault('status', 'pendente')
        lead.setdefault('whatsapp', lead.get('telefone', ''))

        query = text("""
            INSERT INTO leads (id, nome, cidade, segmento, telefone, whatsapp,
                               rating, score, tier, status)
            VALUES (:id, :nome, :cidade, :segmento, :telefone, :whatsapp,
                   :rating, :score, :tier, :status)
            RETURNING id
        """)
        result = self.db.execute(query, lead)
        self.db.commit()
        return result.fetchone()[0]

    def atualizar(self, lead_id: str, dados: Dict[str, Any]):
        # Validar colunas contra whitelist (proteção SQL Injection)

        invalid_cols = set(dados.keys()) - self.ALLOWED_COLUMNS_LEADS

        if invalid_cols:

            raise ValueError(f"❌ Colunas não permitidas: {invalid_cols}")

        set_clause = ", ".join([f"{k} = :{k}" for k in dados.keys()])
        query = text(f"UPDATE leads SET {set_clause} WHERE id = :lead_id")
        self.db.execute(query, {"lead_id": lead_id, **dados})
        self.db.commit()

    def buscar_por_id(self, lead_id: str) -> Optional[Dict[str, Any]]:
        query = text("SELECT * FROM leads WHERE id = :lead_id")
        result = self.db.execute(query, {"lead_id": lead_id}).fetchone()
        return dict(result._mapping) if result else None

    def listar_todos(self, limite: int = 100) -> List[Dict[str, Any]]:
        query = text("SELECT * FROM leads ORDER BY nome ASC LIMIT :limite")
        result = self.db.execute(query, {"limite": limite}).fetchall()
        return [dict(r._mapping) for r in result]

    def listar(self, limite: int = 200) -> List[Dict[str, Any]]:
        query = text("SELECT * FROM leads LIMIT :limite")
        result = self.db.execute(query, {"limite": limite})
        return [dict(row._mapping) for row in result.fetchall()]

    def listar_por_status(self, status: str, limite: int = 100) -> List[Dict[str, Any]]:
        """Lista leads filtrando pelo status"""
        query = text("SELECT * FROM leads WHERE status = :status LIMIT :limite")
        result = self.db.execute(query, {"status": status, "limite": limite})
        return [dict(row._mapping) for row in result.fetchall()]

    def buscar_nomes_existentes(self, cidade: str, segmento: str, user_id: int) -> set:
        """Retorna set de nomes normalizados (lower+strip) já salvos para cidade+segmento+user."""
        query = text("""
            SELECT lower(trim(nome)) FROM leads
            WHERE lower(cidade) = lower(:cidade)
              AND lower(segmento) = lower(:segmento)
              AND user_id = :user_id
        """)
        result = self.db.execute(query, {"cidade": cidade, "segmento": segmento, "user_id": user_id})
        return {row[0] for row in result.fetchall()}

class CicloDB:
    def __init__(self, db):
        self.db = db
        # Whitelist de colunas permitidas (proteção SQL Injection)
        self.ALLOWED_COLUMNS_CICLOS = {"numero", "cidade", "segmento", "quantidade", "criado_em"}

        query = text("""
            INSERT INTO ciclos (numero, cidade, segmento, quantidade)
            VALUES (:numero, :cidade, :segmento, :quantidade)
            RETURNING id
        """)
        result = self.db.execute(query, ciclo)
        self.db.commit()
        return result.fetchone()[0]

    def atualizar(self, ciclo_id: int, dados: Dict[str, Any]):
        # Validar colunas contra whitelist (proteção SQL Injection)

        invalid_cols = set(dados.keys()) - self.ALLOWED_COLUMNS_CICLOS

        if invalid_cols:

            raise ValueError(f"❌ Colunas não permitidas: {invalid_cols}")

        set_clause = ", ".join([f"{k} = :{k}" for k in dados.keys()])
        query = text(f"UPDATE ciclos SET {set_clause} WHERE id = :ciclo_id")
        self.db.execute(query, {"ciclo_id": ciclo_id, **dados})
        self.db.commit()

    def finalizar(self, ciclo_id: int, resultado: Dict[str, Any]):
        # Validar colunas contra whitelist (proteção SQL Injection)

        invalid_cols = set(resultado.keys()) - self.ALLOWED_COLUMNS_CICLOS

        if invalid_cols:

            raise ValueError(f"❌ Colunas não permitidas: {invalid_cols}")

        set_clause = ", ".join([f"{k} = :{k}" for k in resultado.keys()])
        query = text(f"UPDATE ciclos SET {set_clause} WHERE id = :ciclo_id")
        self.db.execute(query, {"ciclo_id": ciclo_id, **resultado})
        self.db.commit()

    def listar(self, limite: int = 200) -> List[Dict[str, Any]]:
        query = text("SELECT * FROM ciclos LIMIT :limite")
        result = self.db.execute(query, {"limite": limite})
        return [dict(row._mapping) for row in result.fetchall()]

class LogDB:
    def __init__(self, db):
        self.db = db

    def criar(self, mensagem: str, tipo: str = "info"):
        query = text("""
            INSERT INTO logs (mensagem, tipo)
            VALUES (:mensagem, :tipo)
        """)
        self.db.execute(query, {"mensagem": mensagem, "tipo": tipo})
        self.db.commit()

    def listar(self, limite: int = 200, tipo: Optional[str] = None) -> List[Dict[str, Any]]:
        if tipo:
            query = text("""
                SELECT * FROM logs
                WHERE tipo = :tipo
                ORDER BY criado_em DESC
                LIMIT :limite
            """)
            result = self.db.execute(query, {"tipo": tipo, "limite": limite})
        else:
            query = text("SELECT * FROM logs ORDER BY criado_em DESC LIMIT :limite")
            result = self.db.execute(query).fetchall()
        return [dict(r._mapping) for r in result]

class LicencaDB:
    def __init__(self, db):
        self.db = db

    def criar(self, licenca: Dict[str, Any]) -> str:
        query = text("""
            INSERT INTO public.licencas
            (id, usuario_id, plano, valor, status, leads_mes, sites_mes,
             whatsapp_incluido, telegram_incluido, data_inicio, renovacao_automatica)
            VALUES (:id, :usuario_id, :plano, :valor, :status, :leads_mes, :sites_mes,
                   :whatsapp_incluido, :telegram_incluido, :data_inicio, :renovacao_automatica)
            RETURNING id
        """)
        result = self.db.execute(query, licenca)
        self.db.commit()
        return result.fetchone()[0]

    def buscar_por_usuario(self, usuario_id: int) -> Optional[Dict[str, Any]]:
        query = text("""
            SELECT * FROM public.licencas
            WHERE usuario_id = :usuario_id
            AND status = 'ATIVA'
            ORDER BY data_inicio DESC
        """)
        result = self.db.execute(query, {"usuario_id": usuario_id}).fetchone()
        return dict(result._mapping) if result else None


# ===== INICIALIZAÇÃO =====

def inicializar_database():
    """Inicializa o banco de dados criando tabelas base"""
    with engine.connect() as conn:
        # Criar tabela de usuários (schema public)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                nome VARCHAR(255),
                tenant_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Criar tabela de licenças
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS licencas (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                plano VARCHAR(50) NOT NULL,
                status VARCHAR(50) DEFAULT 'ativa',
                data_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_fim TIMESTAMP,
                max_leads INTEGER DEFAULT 100,
                max_sites INTEGER DEFAULT 10
            )
        """))
        
        # Criar tabela pipeline_queue (fila persistente de jobs)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pipeline_queue (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                segmento VARCHAR(100),
                cidade VARCHAR(100),
                quantidade INTEGER DEFAULT 10,
                score_minimo INTEGER DEFAULT 60,
                status VARCHAR(20) DEFAULT 'pendente',
                criado_em TIMESTAMP DEFAULT NOW(),
                iniciado_em TIMESTAMP,
                concluido_em TIMESTAMP,
                erro TEXT
            )
        """))

        # Criar tabela sdr_learning (aprendizado do Bryan SDR)
        conn.execute(text("""
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
        """))

        # ===== JOB QUEUE PERSISTENTE =====
        # Tabela `jobs`: fila generica de tarefas em background com retry e crash recovery.
        # status: pending | running | completed | failed_retriable | failed_permanent
        # Worker daemon faz SELECT FOR UPDATE SKIP LOCKED em (status='pending' AND next_retry_at <= NOW())
        conn.execute(text("""
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
                checkpoint_id VARCHAR(120),
                worker_id VARCHAR(80),
                worker_heartbeat TIMESTAMP,
                next_retry_at TIMESTAMP DEFAULT NOW(),
                criado_em TIMESTAMP DEFAULT NOW(),
                iniciado_em TIMESTAMP,
                concluido_em TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_jobs_claim
            ON jobs (status, next_retry_at)
            WHERE status = 'pending'
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_jobs_tenant
            ON jobs (tenant_id, status)
        """))

        # Tabela `pipeline_failures`: jobs que esgotaram os retries automaticos.
        # Aparece pro cliente no dashboard com botao "tentar de novo manualmente".
        conn.execute(text("""
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
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_failures_tenant
            ON pipeline_failures (tenant_id, resolvido, criado_em DESC)
        """))

        # PR8: BYOK Anthropic - cliente do plano Pro guarda a propria
        # API key criptografada (Fernet). O pipeline le esta coluna
        # quando _current_user_id e Pro, senao usa ANTHROPIC_API_KEY do .env.
        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS anthropic_key_encrypted TEXT
        """))

        # PR7: idempotencia + auditoria dos webhooks da Stripe.
        # Cada evento da Stripe traz um id unico ("evt_..."); guardar aqui
        # evita reprocessamento se a Stripe reenviar (acontece em retries
        # automaticos quando nosso 2xx demora demais ou cai).
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stripe_events (
                event_id VARCHAR(120) PRIMARY KEY,
                tipo VARCHAR(120),
                user_id INTEGER,
                stripe_customer_id VARCHAR(120),
                processado BOOLEAN DEFAULT FALSE,
                erro TEXT,
                criado_em TIMESTAMP DEFAULT NOW(),
                processado_em TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_stripe_events_customer
            ON stripe_events (stripe_customer_id, criado_em DESC)
        """))

        conn.commit()

    print("[Database] ✅ Banco inicializado")


# ===== PIPELINE STATE (Multi-tenant) =====

def get_pipeline_state(db: Session, tenant_id: int):
    """Retorna o estado do pipeline para um tenant especifico"""
    query = text("""
        SELECT rodando, pausado, config, updated_at
        FROM public.pipeline_state
        WHERE tenant_id = :tenant_id
    """)
    result = db.execute(query, {"tenant_id": tenant_id}).fetchone()

    if result:
        return {
            "rodando": result[0],
            "pausado": result[1],
            "config": result[2] or {},
            "updated_at": result[3]
        }
    else:
        # Estado padrão se não existir
        return {
            "rodando": False,
            "pausado": False,
            "config": {},
            "updated_at": None
        }

def update_pipeline_state(db: Session, tenant_id: int, rodando=None, pausado=None, config=None):
    """Atualiza o estado do pipeline para um tenant específico"""
    # Verificar se já existe registro
    check_query = text("SELECT tenant_id FROM public.pipeline_state WHERE tenant_id = :tenant_id")
    exists = db.execute(check_query, {"tenant_id": tenant_id}).fetchone()

    if exists:
        # UPDATE
        updates = []
        params = {"tenant_id": tenant_id}

        if rodando is not None:
            updates.append("rodando = :rodando")
            params["rodando"] = rodando

        if pausado is not None:
            updates.append("pausado = :pausado")
            params["pausado"] = pausado

        if config is not None:
            updates.append("config = :config")
            params["config"] = json.dumps(config)

        if updates:
            updates.append("updated_at = NOW()")
            query = text(f"UPDATE public.pipeline_state SET {', '.join(updates)} WHERE tenant_id = :tenant_id")
            db.execute(query, params)
            db.commit()
    else:
        # INSERT
        query = text("""
            INSERT INTO public.pipeline_state (tenant_id, rodando, pausado, config, updated_at)
            VALUES (:tenant_id, :rodando, :pausado, :config, NOW())
        """)
        db.execute(query, {
            "tenant_id": tenant_id,
            "rodando": rodando if rodando is not None else False,
            "pausado": pausado if pausado is not None else False,
            "config": json.dumps(config if config is not None else {})
        })
        db.commit()
