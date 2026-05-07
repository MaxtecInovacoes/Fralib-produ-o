"""
test_auth_endpoints.py - Testes unitários para endpoints de autenticação

Testa os endpoints /api/auth/login e /api/auth/me.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch
from sqlalchemy import text

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

# Mock do SECRET_KEY para testes
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests"

from endpoints.auth_endpoints import create_access_token, verify_password
from utils.password_utils import hash_password


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_success(client, test_user, test_user_data):
    """Testa login com credenciais válidas."""
    response = await client.post("/api/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_invalid_email(client):
    """Testa login com email inexistente."""
    response = await client.post("/api/auth/login", json={
        "email": "naoexiste@example.com",
        "password": "SenhaQualquer123"
    })

    assert response.status_code == 401
    assert "inválidos" in response.json()["detail"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_invalid_password(client, test_user, test_user_data):
    """Testa login com senha incorreta."""
    response = await client.post("/api/auth/login", json={
        "email": test_user_data["email"],
        "password": "SenhaErrada123"
    })

    assert response.status_code == 401
    assert "inválidos" in response.json()["detail"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_missing_email(client):
    """Testa login sem email."""
    response = await client.post("/api/auth/login", json={
        "password": "Test123!@#"
    })

    assert response.status_code == 422  # Validation error


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_missing_password(client):
    """Testa login sem senha."""
    response = await client.post("/api/auth/login", json={
        "email": "test@example.com"
    })

    assert response.status_code == 422  # Validation error


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_invalid_email_format(client):
    """Testa login com email em formato inválido."""
    response = await client.post("/api/auth/login", json={
        "email": "not-an-email",
        "password": "Test123!@#"
    })

    assert response.status_code == 422  # Validation error


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_me_valid_token(client, test_user_token, test_user):
    """Testa /api/auth/me com token válido."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = await client.get("/api/auth/me", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["user_id"] == str(test_user["id"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_me_missing_token(client):
    """Testa /api/auth/me sem token."""
    response = await client.get("/api/auth/me")

    assert response.status_code == 403  # Forbidden (no auth header)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_me_invalid_token(client):
    """Testa /api/auth/me com token inválido."""
    headers = {"Authorization": "Bearer invalid.token.here"}
    response = await client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401
    assert "inválido" in response.json()["detail"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_me_expired_token(client):
    """Testa /api/auth/me com token expirado."""
    import jwt
    from datetime import datetime, timedelta

    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "test-secret-key-for-unit-tests")

    # Criar token expirado
    expired_payload = {
        "sub": "123",
        "email": "test@example.com",
        "exp": datetime.utcnow() - timedelta(hours=1)
    }
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm="HS256")

    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401
    # Aceitar tanto "expirado" quanto "inválido" (ambos são válidos para token expirado)
    detail_lower = response.json()["detail"].lower()
    assert "expirado" in detail_lower or "inválido" in detail_lower or "inv" in detail_lower


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_me_malformed_header(client):
    """Testa /api/auth/me com header malformado."""
    # Sem "Bearer" prefix
    headers = {"Authorization": "invalid-format-token"}
    response = await client.get("/api/auth/me", headers=headers)

    assert response.status_code == 403


@pytest.mark.unit
def test_verify_password_function():
    """Testa função verify_password diretamente."""
    password = "Test123!@#"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


@pytest.mark.unit
def test_create_access_token_function():
    """Testa função create_access_token diretamente."""
    data = {"sub": "123", "email": "test@example.com"}
    token = create_access_token(data)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0

    # Decodificar e verificar
    import jwt
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "test-secret-key-for-unit-tests")
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

    assert payload["sub"] == "123"
    assert payload["email"] == "test@example.com"
    assert "exp" in payload
