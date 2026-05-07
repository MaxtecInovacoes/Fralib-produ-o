"""
test_database.py - Testes unitários para funções de banco de dados

Testa as funções do módulo database.py.
"""
import pytest
import sys
import os
from sqlalchemy import text

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from core.database import get_pipeline_state, update_pipeline_state


@pytest.mark.unit
@pytest.mark.database
def test_get_pipeline_state_new_tenant(db_session):
    """Testa get_pipeline_state para tenant novo (sem estado)."""
    tenant_id = 999

    state = get_pipeline_state(db_session, tenant_id)

    assert state is not None
    assert state['rodando'] is False
    assert state['pausado'] is False
    assert state['config'] == {}
    assert state['updated_at'] is None


@pytest.mark.unit
@pytest.mark.database
def test_get_pipeline_state_existing_tenant(db_session):
    """Testa get_pipeline_state para tenant existente."""
    tenant_id = 1

    # Criar estado inicial
    db_session.execute(text("""
        INSERT INTO pipeline_state (tenant_id, rodando, pausado, config)
        VALUES (:tenant_id, :rodando, :pausado, :config)
    """), {
        'tenant_id': tenant_id,
        'rodando': True,
        'pausado': False,
        'config': '{"nicho": "test"}'
    })
    db_session.commit()

    # Buscar estado
    state = get_pipeline_state(db_session, tenant_id)

    assert state is not None
    assert state['rodando'] is True
    assert state['pausado'] is False
    assert state['config'] == {"nicho": "test"}
    assert state['updated_at'] is not None


@pytest.mark.unit
@pytest.mark.database
def test_update_pipeline_state_new_tenant(db_session):
    """Testa update_pipeline_state para tenant novo."""
    tenant_id = 1

    # Atualizar estado (deve criar novo registro)
    update_pipeline_state(
        db_session,
        tenant_id,
        rodando=True,
        pausado=False,
        config={"nicho": "Marketing"}
    )

    # Verificar se foi criado
    state = get_pipeline_state(db_session, tenant_id)

    assert state['rodando'] is True
    assert state['pausado'] is False
    assert state['config'] == {"nicho": "Marketing"}


@pytest.mark.unit
@pytest.mark.database
def test_update_pipeline_state_existing_tenant(db_session):
    """Testa update_pipeline_state para tenant existente."""
    tenant_id = 1

    # Criar estado inicial
    update_pipeline_state(db_session, tenant_id, rodando=False, pausado=False, config={})

    # Atualizar estado
    update_pipeline_state(
        db_session,
        tenant_id,
        rodando=True,
        config={"nicho": "Tech"}
    )

    # Verificar atualização
    state = get_pipeline_state(db_session, tenant_id)

    assert state['rodando'] is True
    assert state['pausado'] is False  # Não foi alterado
    assert state['config'] == {"nicho": "Tech"}


@pytest.mark.unit
@pytest.mark.database
def test_update_pipeline_state_partial_update(db_session):
    """Testa update_pipeline_state com atualização parcial."""
    tenant_id = 1

    # Criar estado inicial
    update_pipeline_state(
        db_session,
        tenant_id,
        rodando=True,
        pausado=False,
        config={"nicho": "Marketing", "localizacao": "SP"}
    )

    # Atualizar apenas 'rodando'
    update_pipeline_state(db_session, tenant_id, rodando=False)

    # Verificar que apenas 'rodando' mudou
    state = get_pipeline_state(db_session, tenant_id)

    assert state['rodando'] is False
    assert state['pausado'] is False
    assert state['config'] == {"nicho": "Marketing", "localizacao": "SP"}


@pytest.mark.unit
@pytest.mark.database
def test_update_pipeline_state_config_merge(db_session):
    """Testa que config é substituído completamente, não merged."""
    tenant_id = 1

    # Criar estado inicial
    update_pipeline_state(
        db_session,
        tenant_id,
        config={"nicho": "Marketing", "localizacao": "SP"}
    )

    # Atualizar config (deve substituir, não fazer merge)
    update_pipeline_state(
        db_session,
        tenant_id,
        config={"nicho": "Tech"}
    )

    # Verificar que config foi substituído
    state = get_pipeline_state(db_session, tenant_id)

    assert state['config'] == {"nicho": "Tech"}
    assert "localizacao" not in state['config']


@pytest.mark.unit
@pytest.mark.database
def test_pipeline_state_isolation_between_tenants(db_session):
    """Testa que estados de diferentes tenants são isolados."""
    tenant1 = 1
    tenant2 = 2

    # Criar estados para 2 tenants
    update_pipeline_state(db_session, tenant1, rodando=True, config={"tenant": "1"})
    update_pipeline_state(db_session, tenant2, rodando=False, config={"tenant": "2"})

    # Verificar isolamento
    state1 = get_pipeline_state(db_session, tenant1)
    state2 = get_pipeline_state(db_session, tenant2)

    assert state1['rodando'] is True
    assert state1['config'] == {"tenant": "1"}

    assert state2['rodando'] is False
    assert state2['config'] == {"tenant": "2"}


@pytest.mark.unit
@pytest.mark.database
def test_update_pipeline_state_updated_at_changes(db_session):
    """Testa que updated_at é atualizado em cada update."""
    import time
    tenant_id = 1

    # Criar estado inicial
    update_pipeline_state(db_session, tenant_id, rodando=True)
    state1 = get_pipeline_state(db_session, tenant_id)
    updated_at_1 = state1['updated_at']

    # Aguardar um pouco
    time.sleep(0.1)

    # Atualizar estado
    update_pipeline_state(db_session, tenant_id, rodando=False)
    state2 = get_pipeline_state(db_session, tenant_id)
    updated_at_2 = state2['updated_at']

    # Verificar que updated_at mudou
    assert updated_at_2 > updated_at_1


@pytest.mark.unit
@pytest.mark.database
def test_get_db_returns_session(db_session):
    """Testa que get_db retorna uma sessão válida."""
    # db_session já é uma sessão válida do get_db
    assert db_session is not None

    # Testar que consegue executar query
    result = db_session.execute(text("SELECT 1 as test"))
    row = result.fetchone()

    assert row[0] == 1


@pytest.mark.unit
@pytest.mark.database
def test_pipeline_state_config_json_serialization(db_session):
    """Testa que config aceita diferentes tipos de dados JSON."""
    tenant_id = 1

    complex_config = {
        "nicho": "Marketing",
        "localizacao": "São Paulo",
        "max_leads": 100,
        "ativo": True,
        "tags": ["tag1", "tag2"],
        "nested": {
            "key": "value"
        }
    }

    update_pipeline_state(db_session, tenant_id, config=complex_config)
    state = get_pipeline_state(db_session, tenant_id)

    assert state['config'] == complex_config
    assert state['config']['max_leads'] == 100
    assert state['config']['ativo'] is True
    assert state['config']['tags'] == ["tag1", "tag2"]
    assert state['config']['nested']['key'] == "value"
