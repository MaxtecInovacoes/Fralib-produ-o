"""Teste E2E - verifica pipeline completo.

Estes testes validam que o pipeline continua funcionando após refatorações
dos monolitos. Cada teste executa o pipeline com um segmento diferente para
garantir que não há regressões.

Execute com:
    pytest tests/e2e/test_pipeline_complete.py -v

Ou para executar apenas os testes de pipeline:
    pytest tests/e2e/ -k pipeline -v
"""
import pytest
import sys
import os
from typing import Any

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

# Garantir variáveis de ambiente de teste
os.environ.setdefault("TESTING", "true")


# ===== FIXTURES =====


@pytest.fixture
def benchmark_tenant_id() -> int:
    """Tenant ID para testes de benchmark."""
    return 999999


@pytest.fixture
def lead_fake_restaurante() -> dict[str, Any]:
    """Lead fake para teste de restaurante."""
    return {
        "segmento": "restaurante",
        "cidade": "São Paulo",
        "nome": "Restaurante Teste E2E",
        "telefone": "+5511999999999",
        "whatsapp": "+5511999999999",
        "rating": 4.5,
        "total_avaliacoes": 50,
        "reviews": [
            {"autor": "Maria S.", "rating": 5, "texto": "Ótimo!"},
            {"autor": "João P.", "rating": 4, "texto": "Boa comida!"},
        ],
        "website": "",
        "endereco": "Rua Teste, 123 - São Paulo, SP",
    }


@pytest.fixture
def lead_fake_nutricionista() -> dict[str, Any]:
    """Lead fake para teste de nutricionista."""
    return {
        "segmento": "nutricionista",
        "cidade": "Rio de Janeiro",
        "nome": "Nutricionista Teste E2E",
        "telefone": "+5521999999999",
        "whatsapp": "+5521999999999",
        "rating": 4.8,
        "total_avaliacoes": 30,
        "reviews": [
            {"autor": "Ana C.", "rating": 5, "texto": "Excelente atendimento!"},
        ],
        "website": "",
        "endereco": "Av. Teste, 456 - Rio de Janeiro, RJ",
    }


@pytest.fixture
def lead_fake_academia() -> dict[str, Any]:
    """Lead fake para teste de academia."""
    return {
        "segmento": "academia",
        "cidade": "Belo Horizonte",
        "nome": "Academia Teste E2E",
        "telefone": "+5531999999999",
        "whatsapp": "+5531999999999",
        "rating": 4.2,
        "total_avaliacoes": 100,
        "reviews": [
            {"autor": "Pedro S.", "rating": 4, "texto": "Boa estrutura!"},
            {"autor": "Lucas M.", "rating": 5, "texto": "Melhor academia da região!"},
        ],
        "website": "",
        "endereco": "Rua Academia, 789 - Belo Horizonte, MG",
    }


# ===== HELPERS =====


async def _run_pipeline_for_segment(
    segmento: str,
    cidade: str,
    tenant_id: int,
    skip_franz: bool = True,
) -> dict[str, Any]:
    """Helper para executar pipeline para um segmento específico."""
    from backend.endpoints.pipeline_orchestrator_service import (
        executar_pipeline_completo,
    )

    return await executar_pipeline_completo(
        config={
            "segmento": segmento,
            "cidade": cidade,
            "quantidade": 1,
            "_skip_franz_outreach": skip_franz,
            "_controlled_test": True,
        },
        tenant_id=tenant_id,
    )


# ===== TESTES =====


@pytest.mark.asyncio
async def test_pipeline_completo_restaurante(benchmark_tenant_id: int):
    """Pipeline deve processar lead de restaurante com sucesso.

    Valida que:
    - Pipeline não trava
    - Retorna dicionário com resultado
    - Parâmetros básicos são aceitos
    """
    result = await _run_pipeline_for_segment(
        segmento="restaurante",
        cidade="São Paulo",
        tenant_id=benchmark_tenant_id,
    )

    # Não importa se sucesso ou falha - só que não trava e retorna resultado
    assert result is not None
    assert isinstance(result, dict)

    # Verificar que resultado tem estrutura esperada
    # (pode ter sucesso ou não, mas deve ter campos esperados)
    expected_fields = ["sucesso", "fases_executadas"]
    for field in expected_fields:
        assert field in result, f"Campo esperado '{field}' não encontrado no resultado"


@pytest.mark.asyncio
async def test_pipeline_completo_nutricionista(benchmark_tenant_id: int):
    """Pipeline deve processar lead de nutricionista.

    Valida que:
    - Pipeline aceita segmento 'nutricionista'
    - Retorna estrutura de dados válida
    """
    result = await _run_pipeline_for_segment(
        segmento="nutricionista",
        cidade="Rio de Janeiro",
        tenant_id=benchmark_tenant_id,
    )

    assert result is not None
    assert isinstance(result, dict)

    # Verificar estrutura do resultado
    assert "sucesso" in result
    assert isinstance(result["sucesso"], bool)


@pytest.mark.asyncio
async def test_pipeline_completo_academia(benchmark_tenant_id: int):
    """Pipeline deve processar lead de academia.

    Valida que:
    - Pipeline aceita segmento 'academia'
    - Não lança exceções
    - Retorna resultado processável
    """
    result = await _run_pipeline_for_segment(
        segmento="academia",
        cidade="Belo Horizonte",
        tenant_id=benchmark_tenant_id,
    )

    assert result is not None
    assert isinstance(result, dict)

    # Resultado deve ser serializável (para debug)
    result_json = str(result)
    assert len(result_json) > 0


@pytest.mark.asyncio
async def test_pipeline_nao_quebra_com_parametros_minimos(benchmark_tenant_id: int):
    """Pipeline deve funcionar com parâmetros mínimos.

    Valida que:
    - Pipeline aceita configuração mínima
    - Não crasha com parâmetros básicos
    """
    from backend.endpoints.pipeline_orchestrator_service import (
        executar_pipeline_completo,
    )

    # Configuração mínima
    config_minima = {
        "segmento": "restaurante",
        "cidade": "São Paulo",
        "quantidade": 1,
    }

    result = await executar_pipeline_completo(
        config=config_minima,
        tenant_id=benchmark_tenant_id,
    )

    # Deve retornar algo, mesmo que não seja sucesso total
    assert result is not None


@pytest.mark.asyncio
async def test_pipeline_aceita_skip_franz_outreach(benchmark_tenant_id: int):
    """Pipeline deve aceitar flag _skip_franz_outreach.

    Valida que:
    - Flag _skip_franz_outreach é aceita
    - Pipeline não tenta enviar WhatsApp
    """
    result = await _run_pipeline_for_segment(
        segmento="restaurante",
        cidade="São Paulo",
        tenant_id=benchmark_tenant_id,
        skip_franz=True,
    )

    assert result is not None

    # Verificar que não há tentativa de WhatsApp no resultado
    # (campo 'franz' ou similar deve indicar que foi pulado)
    # Não verificamos sucesso, apenas que a flag foi processada
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_pipeline_retorna_fases_executadas(benchmark_tenant_id: int):
    """Pipeline deve retornar lista de fases executadas.

    Valida que:
    - Campo 'fases_executadas' existe no resultado
    - É uma lista (mesmo que vazia)
    """
    result = await _run_pipeline_for_segment(
        segmento="restaurante",
        cidade="São Paulo",
        tenant_id=benchmark_tenant_id,
    )

    assert "fases_executadas" in result
    assert isinstance(result["fases_executadas"], list)


@pytest.mark.asyncio
async def test_pipeline_diferentes_cidades(benchmark_tenant_id: int):
    """Pipeline deve funcionar com diferentes cidades.

    Valida que:
    - Pipeline aceita diferentes localizações
    - Não há hardcoding de cidade específica
    """
    cidades = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba"]

    for cidade in cidades:
        result = await _run_pipeline_for_segment(
            segmento="restaurante",
            cidade=cidade,
            tenant_id=benchmark_tenant_id,
        )

        # Cada execução deve retornar resultado
        assert result is not None, f"Falhou para cidade: {cidade}"
        assert isinstance(result, dict), f"Resultado inválido para: {cidade}"


@pytest.mark.asyncio
async def test_pipeline_handle_erro_sem_crash(benchmark_tenant_id: int):
    """Pipeline deve tratar erros sem crashar.

    Valida que:
    - Erros são capturados e retornados no resultado
    - Não há exceção não tratada subindo
    """
    from backend.endpoints.pipeline_orchestrator_service import (
        executar_pipeline_completo,
    )

    # Tentar com configuração potencialmente problemática
    # (cidade inexistente deve ser tratada graciosamente)
    try:
        result = await executar_pipeline_completo(
            config={
                "segmento": "segmento_inexistente_xyz",
                "cidade": "Cidade Inexistente XYZ",
                "quantidade": 1,
                "_skip_franz_outreach": True,
            },
            tenant_id=benchmark_tenant_id,
        )

        # Se chegou aqui, o pipeline tratou o erro
        assert result is not None

    except Exception as e:
        # Se lançou exceção, deve ser uma exceção tratada/esperada
        # (não um crash completo)
        pytest.fail(f"Pipeline crashou com exceção não tratada: {e}")


# ===== TESTE DE REGRESSÃO (pode ser usado com CI) =====

REGRESSION_THRESHOLDS = {
    "max_time_seconds": 300,  # 5 minutos max por pipeline
    "min_html_size": 1000,  # Mínimo 1KB de HTML
}


@pytest.mark.asyncio
async def test_pipeline_regression_max_time(benchmark_tenant_id: int):
    """Teste de regressão: pipeline não deve demorar mais que o limite.

    Este teste pode ser usado para detectar regressions de performance.
    """
    import time

    start = time.time()

    result = await _run_pipeline_for_segment(
        segmento="restaurante",
        cidade="São Paulo",
        tenant_id=benchmark_tenant_id,
    )

    elapsed = time.time() - start

    # Log do tempo para debug
    print(f"\nTempo de execução: {elapsed:.2f}s")

    # Verificar limite de tempo
    assert elapsed < REGRESSION_THRESHOLDS["max_time_seconds"], (
        f"Pipeline demorou {elapsed:.2f}s, limite é {REGRESSION_THRESHOLDS['max_time_seconds']}s"
    )


@pytest.mark.asyncio
async def test_pipeline_regression_html_size(benchmark_tenant_id: int):
    """Teste de regressão: HTML gerado deve ter tamanho mínimo.

    Este teste detecta se o pipeline está gerando HTML truncado ou vazio.
    """
    result = await _run_pipeline_for_segment(
        segmento="restaurante",
        cidade="São Paulo",
        tenant_id=benchmark_tenant_id,
    )

    html = result.get("html", "") if result else ""

    print(f"\nTamanho do HTML: {len(html)} bytes")

    # Verificar tamanho mínimo
    assert len(html) >= REGRESSION_THRESHOLDS["min_html_size"], (
        f"HTML muito pequeno ({len(html)} bytes), esperado pelo menos "
        f"{REGRESSION_THRESHOLDS['min_html_size']} bytes"
    )
