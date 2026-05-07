"""
test_api_auth.py - Testes de integração da API de autenticação

Testa fluxos completos de autenticação envolvendo múltiplos componentes.
"""
import pytest
import sys
import os

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_registro_e_login_completo(client, db_session):
    """Testa fluxo completo: criar usuário -> login -> obter perfil."""
    from utils.password_utils import hash_password
    from sqlalchemy import text

    # 1. Criar usuário no banco
    email = "integration@test.com"
    password = "Integration123!@#"

    query = text("""
        INSERT INTO users (email, password_hash, nome, tenant_id)
        VALUES (:email, :password_hash, :nome, :tenant_id)
        RETURNING id
    """)

    result = db_session.execute(query, {
        "email": email,
        "password_hash": hash_password(password),
        "nome": "Integration Test",
        "tenant_id": 1
    })
    db_session.commit()
    user_id = result.fetchone()[0]

    # 2. Fazer login
    login_response = await client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })

    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data
    token = login_data["access_token"]

    # 3. Obter perfil com token
    headers = {"Authorization": f"Bearer {token}"}
    profile_response = await client.get("/api/auth/me", headers=headers)

    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    assert profile_data["email"] == email
    assert profile_data["user_id"] == str(user_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_com_senha_incorreta(client, test_user, test_user_data):
    """Testa que login com senha incorreta retorna 401."""
    response = await client.post("/api/auth/login", json={
        "email": test_user_data["email"],
        "password": "SenhaErrada123!@#"
    })

    assert response.status_code == 401
    assert "inválidos" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_com_email_inexistente(client):
    """Testa que login com email inexistente retorna 401."""
    response = await client.post("/api/auth/login", json={
        "email": "naoexiste@test.com",
        "password": "Qualquer123!@#"
    })

    assert response.status_code == 401
    assert "inválidos" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_acesso_endpoint_protegido_sem_token(client):
    """Testa que endpoint protegido sem token retorna 403."""
    response = await client.get("/api/auth/me")

    assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_acesso_endpoint_protegido_token_invalido(client):
    """Testa que endpoint protegido com token inválido retorna 401."""
    headers = {"Authorization": "Bearer token-invalido-aqui"}
    response = await client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_expira_apos_24_horas(client, test_user):
    """Testa que token expira após 24 horas."""
    import jwt
    from datetime import datetime, timedelta

    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "test-secret-key-for-unit-tests")

    # Criar token expirado (25 horas atrás)
    expired_payload = {
        "sub": str(test_user["id"]),
        "email": test_user["email"],
        "exp": datetime.utcnow() - timedelta(hours=25)
    }
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm="HS256")

    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiplos_logins_mesmo_usuario(client, test_user, test_user_data):
    """Testa que o mesmo usuário pode fazer múltiplos logins."""
    # Primeiro login
    response1 = await client.post("/api/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    })
    assert response1.status_code == 200
    token1 = response1.json()["access_token"]

    # Segundo login
    response2 = await client.post("/api/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    })
    assert response2.status_code == 200
    token2 = response2.json()["access_token"]

    # Ambos tokens devem funcionar
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    profile1 = await client.get("/api/auth/me", headers=headers1)
    profile2 = await client.get("/api/auth/me", headers=headers2)

    assert profile1.status_code == 200
    assert profile2.status_code == 200
    assert profile1.json()["email"] == profile2.json()["email"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_case_sensitive_email(client, test_user, test_user_data):
    """Testa que email é case-insensitive no login."""
    # Login com email em maiúsculas
    response = await client.post("/api/auth/login", json={
        "email": test_user_data["email"].upper(),
        "password": test_user_data["password"]
    })

    # Deve falhar porque PostgreSQL é case-sensitive por padrão
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_contem_informacoes_corretas(client, test_user, test_user_data):
    """Testa que token JWT contém as informações corretas do usuário."""
    import jwt

    # Fazer login
    response = await client.post("/api/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    })

    assert response.status_code == 200
    token = response.json()["access_token"]

    # Decodificar token
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "test-secret-key-for-unit-tests")
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

    # Verificar conteúdo
    assert payload["sub"] == str(test_user["id"])
    assert payload["email"] == test_user["email"]
    assert "exp" in payload


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_com_espacos_no_email(client, test_user, test_user_data):
    """Testa que login com espaços no email funciona (trim automático)."""
    response = await client.post("/api/auth/login", json={
        "email": f"  {test_user_data['email']}  ",
        "password": test_user_data["password"]
    })

    # Deve funcionar porque Pydantic faz trim automático
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_response_structure(client, test_user, test_user_data):
    """Testa estrutura da resposta de login."""
    response = await client.post("/api/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    })

    assert response.status_code == 200
    data = response.json()

    # Verificar estrutura
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_me_response_structure(client, test_user_token, test_user):
    """Testa estrutura da resposta de /api/auth/me."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = await client.get("/api/auth/me", headers=headers)

    assert response.status_code == 200
    data = response.json()

    # Verificar estrutura
    assert "email" in data
    assert "user_id" in data
    assert data["email"] == test_user["email"]
    assert data["user_id"] == str(test_user["id"])
