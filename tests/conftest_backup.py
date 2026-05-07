"""
conftest.py - Fixtures compartilhadas para testes

Este arquivo contém fixtures do pytest que são compartilhadas
entre todos os testes do projeto.
"""
import pytest
import os
import sys
from typing import Generator
from httpx import AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from unittest.mock import patch

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Importar app FastAPI
from server import app


# ===== FIXTURES DE BANCO DE DADOS =====

@pytest.fixture(scope="session")
def test_database_url():
    """URL do banco de dados de teste."""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:fralib2024@localhost:5433/fralib_test"
    )


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """Engine do SQLAlchemy para testes."""
    engine = create_engine(test_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Factory de sessões para testes."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db_session(test_session_factory) -> Generator[Session, None, None]:
    """
    Sessão de banco de dados para testes.
    Cada teste recebe uma sessão limpa e faz rollback ao final.
    """
    session = test_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ===== FIXTURES DE API =====

@pytest.fixture
async def client() -> Generator[AsyncClient, None, None]:
    """
    Cliente HTTP assíncrono para testar a API.
    """
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers(test_user_token):
    """
    Headers de autenticação para requisições autenticadas.
    """
    return {"Authorization": f"Bearer {test_user_token}"}


# ===== FIXTURES DE USUÁRIOS =====

@pytest.fixture
def test_user_data():
    """Dados de um usuário de teste."""
    return {
        "email": "test@example.com",
        "password": "Test123!@#",
        "nome": "Test User"
    }


@pytest.fixture
def test_user(db_session, test_user_data):
    """
    Cria um usuário de teste no banco de dados.
    """
    from utils.password_utils import hash_password

    # Criar usuário
    query = text("""
        INSERT INTO users (email, password_hash, nome, tenant_id)
        VALUES (:email, :password_hash, :nome, :tenant_id)
        RETURNING id, email, nome, tenant_id
    """)

    result = db_session.execute(query, {
        "email": test_user_data["email"],
        "password_hash": hash_password(test_user_data["password"]),
        "nome": test_user_data["nome"],
        "tenant_id": 1
    })
    db_session.commit()

    user = result.fetchone()
    return {
        "id": user[0],
        "email": user[1],
        "nome": user[2],
        "tenant_id": user[3]
    }


@pytest.fixture
def test_user_token(test_user):
    """
    Token JWT válido para o usuário de teste.
    """
    from datetime import datetime, timedelta
    import jwt
    import os

    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "test-secret-key")

    payload = {
        "sub": str(test_user["id"]),
        "email": test_user["email"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }

    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


# ===== FIXTURES DE LIMPEZA =====

@pytest.fixture(autouse=True)
def cleanup_database(db_session):
    """
    Limpa o banco de dados após cada teste.
    """
    yield
    # Rollback é feito automaticamente pela fixture db_session


# ===== FIXTURES DE MOCK =====

@pytest.fixture
def mock_anthropic_response():
    """
    Mock de resposta da API Anthropic.
    """
    return {
        "content": [
            {
                "type": "text",
                "text": "Resposta mockada do Claude"
            }
        ],
        "model": "claude-3-5-sonnet-20241022",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50
        }
    }


# ===== FIXTURES DE CONFIGURAÇÃO =====

@pytest.fixture
def test_config():
    """
    Configuração de teste para o pipeline.
    """
    return {
        "nicho": "Agencias de Marketing",
        "localizacao": "Sao Paulo",
        "max_leads_por_ciclo": 5,
        "intervalo_minutos": 30,
        "score_minimo": 70
    }


# ===== FIXTURES DE CORREÇÃO =====

@pytest.fixture(autouse=True)
def disable_rate_limiter():
    Desabilita rate limiter durante os testes.
    with patch('slowapi.Limiter.check_request_limit', return_value=None):
        yield


@pytest.fixture(autouse=True)
def cleanup_test_database(db_session):
    
