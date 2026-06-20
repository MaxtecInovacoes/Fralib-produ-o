"""
test_auth_core.py - Testes unitários para autenticação JWT

Testa as funções de criação e validação de tokens JWT.
"""
import pytest
import sys
import os
from datetime import datetime, timedelta
import jwt
from sqlalchemy import text

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'core'))

# Mock do SECRET_KEY para testes
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests-32-bytes-min"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SUPERADMIN_EMAIL", "admin@example.com")

from core import auth as auth_core
from core.auth import get_current_user, SECRET_KEY, ALGORITHM
from endpoints.auth_endpoints import create_access_token
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


@pytest.mark.unit
def test_secret_key_loaded():
    """Verifica que SECRET_KEY foi carregado do ambiente."""
    assert SECRET_KEY is not None
    assert len(SECRET_KEY) > 0


@pytest.mark.unit
def test_algorithm_is_hs256():
    """Verifica que o algoritmo JWT é HS256."""
    assert ALGORITHM == "HS256"


@pytest.mark.unit
def test_create_access_token_structure():
    """Testa que create_access_token gera token válido."""
    data = {"sub": "123", "email": "test@example.com"}
    token = create_access_token(data)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.unit
def test_create_access_token_payload():
    """Testa que o token contém os dados corretos."""
    data = {"sub": "123", "email": "test@example.com"}
    token = create_access_token(data)

    # Decodificar token
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["sub"] == "123"
    assert payload["email"] == "test@example.com"
    assert "exp" in payload


@pytest.mark.unit
def test_create_access_token_expiration():
    """Testa que o token tem expiração de 24 horas."""
    data = {"sub": "123", "email": "test@example.com"}
    token = create_access_token(data)

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    exp_timestamp = payload["exp"]
    exp_datetime = datetime.utcfromtimestamp(exp_timestamp)

    # Verificar que expira em ~24 horas (com margem de 1 minuto)
    expected_exp = datetime.utcnow() + timedelta(hours=24)
    time_diff = abs((exp_datetime - expected_exp).total_seconds())

    assert time_diff < 60, "Token deve expirar em 24 horas"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    """Testa get_current_user com token válido."""
    # Criar token válido
    data = {"sub": "123", "email": "test@example.com"}
    token = create_access_token(data)

    # Criar credentials mock
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with auth_core._shared_engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, role TEXT, status TEXT, tenant_id TEXT)"))
        conn.execute(
            text("INSERT OR REPLACE INTO users (id, role, status, tenant_id) VALUES ('123', 'user', 'ativa', '123')")
        )
        conn.commit()

    # Validar token
    user = await get_current_user(credentials)

    assert user["id"] == "123"
    assert user["email"] == "test@example.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_expired_token():
    """Testa get_current_user com token expirado."""
    # Criar token expirado
    data = {"sub": "123", "email": "test@example.com"}
    expired_data = data.copy()
    expired_data["exp"] = datetime.utcnow() - timedelta(hours=1)
    token = jwt.encode(expired_data, SECRET_KEY, algorithm=ALGORITHM)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    # Deve lançar HTTPException 401
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials)

    assert exc_info.value.status_code == 401
    assert "expirado" in exc_info.value.detail.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Testa get_current_user com token inválido."""
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid.token.here"
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials)

    assert exc_info.value.status_code == 401
    assert "inválido" in exc_info.value.detail.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_missing_sub():
    """Testa get_current_user com token sem 'sub'."""
    # Criar token sem 'sub'
    data = {"email": "test@example.com"}
    data["exp"] = datetime.utcnow() + timedelta(hours=24)
    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials)

    assert exc_info.value.status_code == 401
    assert "inválido" in exc_info.value.detail.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_wrong_secret():
    """Testa get_current_user com token assinado com secret errado."""
    # Criar token com secret diferente
    data = {"sub": "123", "email": "test@example.com"}
    data["exp"] = datetime.utcnow() + timedelta(hours=24)
    token = jwt.encode(data, "wrong-secret-key", algorithm=ALGORITHM)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials)

    assert exc_info.value.status_code == 401
