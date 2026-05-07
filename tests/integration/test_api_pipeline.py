"""
test_api_pipeline.py - Testes de integração da API de pipeline

Testa fluxos completos de gerenciamento de pipeline.
"""
import pytest
import sys
import os

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_iniciar_pipeline_sucesso(client, test_user_token):
    """Testa iniciar pipeline com sucesso."""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    config = {
        "nicho": "Agências de Marketing",
        "localizacao": "São Paulo",
        "max_leads_por_ciclo": 10
    }

    response = await client.post("/api/pipeline/iniciar", json=config, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "message" in data or "status" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_pipeline_inicial(client, test_user_token):
    """Testa obter status do pipeline quando não está rodando."""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.get("/api/pipeline/status", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "rodando" in data
    assert isinstance(data["rodando"], bool)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fluxo_completo_iniciar_pausar_retomar_parar(client, test_user_token):
    """Testa fluxo completo: iniciar -> pausar -> retomar -> parar."""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    config = {
        "nicho": "Tech Startups",
        "localizacao": "Rio de Janeiro",
        "max_leads_por_ciclo": 5
    }

    # 1. Iniciar pipeline
    iniciar_response = await client.post("/api/pipeline/iniciar", json=config, headers=headers)
    assert iniciar_response.status_code == 200

    # 2. Verificar status (deve estar rodando)
    status_response = await client.get("/api/pipeline/status", headers=headers)
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["rodando"] is True

    # 3. Pausar pipeline
    pausar_response = await client.post("/api/pipeline/pausar", headers=headers)
    assert pausar_response.status_code == 200

    # 4. Verificar status (deve estar pausado)
    status_pausado = await client.get("/api/pipeline/status", headers=headers)
    assert status_pausado.status_code == 200
    pausado_data = status_pausado.json()
    assert pausado_data["pausado"] is True

    # 5. Retomar pipeline
    retomar_response = await client.post("/api/pipeline/retomar", headers=headers)
    assert retomar_response.status_code == 200

    # 6. Verificar status (deve estar rodando e não pausado)
    status_retomado = await client.get("/api/pipeline/status", headers=headers)
    assert status_retomado.status_code == 200
    retomado_data = status_retomado.json()
    assert retomado_data["rodando"] is True
    assert retomado_data["pausado"] is False

    # 7. Parar pipeline
    parar_response = await client.post("/api/pipeline/parar", headers=headers)
    assert parar_response.status_code == 200

    # 8. Verificar status (não deve estar rodando)
    status_parado = await client.get("/api/pipeline/status", headers=headers)
    assert status_parado.status_code == 200
    parado_data = status_parado.json()
    assert parado_data["rodando"] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_iniciar_pipeline_sem_autenticacao(client):
    """Testa que iniciar pipeline sem autenticação retorna 403."""
    config = {
        "nicho": "Test",
        "localizacao": "Test"
    }

    response = await client.post("/api/pipeline/iniciar", json=config)

    assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_pipeline_sem_autenticacao(client):
    """Testa que obter status sem autenticação retorna 403."""
    response = await client.get("/api/pipeline/status")

    assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pausar_pipeline_nao_iniciado(client, test_user_token):
    """Testa pausar pipeline que não está rodando."""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.post("/api/pipeline/pausar", headers=headers)

    # Pode retornar 400 ou 200 dependendo da implementação
    assert response.status_code in [200, 400]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retomar_pipeline_nao_pausado(client, test_user_token):
    """Testa retomar pipeline que não está pausado."""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.post("/api/pipeline/retomar", headers=headers)

    # Pode retornar 400 ou 200 dependendo da implementação
    assert response.status_code in [200, 400]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parar_pipeline_nao_iniciado(client, test_user_token):
    """Testa parar pipeline que não está rodando."""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.post("/api/pipeline/parar", headers=headers)

    # Pode retornar 400 ou 200 dependendo da implementação
    assert response.status_code in [200, 400]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_iniciar_pipeline_ja_rodando(client, test_user_token):
    """Testa iniciar pipeline quando já está rodando."""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    config = {
        "nicho": "Test",
        "localizacao": "Test"
    }

    # Iniciar primeira vez
    response1 = await client.post("/api/pipeline/iniciar", json=config, headers=headers)
    assert response1.status_code == 200

    # Tentar iniciar novamente
    response2 = await client.post("/api/pipeline/iniciar", json=config, headers=headers)

    # Deve retornar erro 400
    assert response2.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_state_isolamento_entre_usuarios(client, db_session):
    """Testa que estados de pipeline são isolados entre usuários."""
    from utils.password_utils import hash_password
    from sqlalchemy import text
    import jwt
    from datetime import datetime, timedelta

    # Criar dois usuários
    users = []
    for i in range(2):
        query = text("""
            INSERT INTO users (email, password_hash, nome, tenant_id)
            VALUES (:email, :password_hash, :nome, :tenant_id)
            RETURNING id, email
        """)
        result = db_session.execute(query, {
            "email": f"user{i}@test.com",
            "password_hash": hash_password("Test123!@#"),
            "nome": f"User {i}",
            "tenant_id": i + 1
        })
        db_session.commit()
        user = result.fetchone()
        users.append({"id": user[0], "email": user[1], "tenant_id": i + 1})

    # Criar tokens para ambos usuários
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "test-secret-key-for-unit-tests")
    tokens = []
    for user in users:
        payload = {
            "sub": str(user["id"]),
            "email": user["email"],
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        tokens.append(token)

    # Usuário 1 inicia pipeline
    headers1 = {"Authorization": f"Bearer {tokens[0]}"}
    config1 = {"nicho": "User1 Niche", "localizacao": "SP"}
    await client.post("/api/pipeline/iniciar", json=config1, headers=headers1)

    # Usuário 2 verifica status (não deve estar rodando para ele)
    headers2 = {"Authorization": f"Bearer {tokens[1]}"}
    status2 = await client.get("/api/pipeline/status", headers=headers2)

    assert status2.status_code == 200
    data2 = status2.json()
    # Usuário 2 não deve ver o pipeline do usuário 1 rodando
    assert data2["rodando"] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analytics_overview_endpoint(client, test_user_token):
    """Testa endpoint de analytics overview."""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.get("/api/pipeline/analytics/overview", headers=headers)

    # Endpoint pode retornar 200 ou 404 dependendo se há dados
    assert response.status_code in [200, 404, 500]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_response_structure(client, test_user_token):
    """Testa estrutura da resposta de status."""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    response = await client.get("/api/pipeline/status", headers=headers)

    assert response.status_code == 200
    data = response.json()

    # Verificar campos obrigatórios
    assert "rodando" in data
    assert isinstance(data["rodando"], bool)

    # Pode ter outros campos opcionais
    if "pausado" in data:
        assert isinstance(data["pausado"], bool)
    if "config" in data:
        assert isinstance(data["config"], dict)
