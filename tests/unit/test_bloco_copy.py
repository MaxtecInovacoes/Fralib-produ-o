import sys
from pathlib import Path


AGENTS_DIR = Path(__file__).resolve().parents[2] / "backend" / "agents"
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))


def test_bloco_copy_raises_when_llms_fail(monkeypatch):
    """Test that bloco_copy raises CopyGenerationError when LLM fails (fail-fast)."""
    import bloco_copy
    from backend.pipeline_exceptions import CopyGenerationError

    def fail_call(*args, **kwargs):
        raise TimeoutError("llm timeout")

    monkeypatch.setattr(bloco_copy, "call_claude", fail_call)

    try:
        result = bloco_copy.executar_bloco_copy(
            nome="High Fitness Academia",
            cidade="Campina Grande do Sul",
            segmento="Academia",
            telefone="(41) 99111-4140",
            endereco="R. Maria Augusta de Oliveira Santana, 29 - Jardim Paulista",
            rating=4.6,
            total_av=89,
            caio_tier="STANDARD",
            dark_mode=False,
            jina_insights="",
            instrucao_criativa="",
            reviews_raw=[{"text": "Atendimento bom e ambiente limpo", "author": "Ana"}],
            seo_ctx="",
            faq_seo_fmt="",
            keyword_research="",
            secoes_nomes=["hero", "sobre", "servicos", "depoimentos", "localizacao", "contato"],
            intel_ctx="",
            craft_ctx="",
            autocritica_ctx="",
        )
        # Should have raised CopyGenerationError
        assert False, "Expected CopyGenerationError to be raised"
    except CopyGenerationError as e:
        # This is the expected behavior - fail-fast, no fallback
        assert "High Fitness Academia" in str(e)
        assert "Campina Grande do Sul" in str(e)
        assert "llm timeout" in str(e)


def test_bloco_copy_no_deterministic_fallback():
    """Test that _copy_deterministica_fallback no longer exists (removed - fail-fast)."""
    import bloco_copy

    # The function should no longer exist - we fail-fast instead
    assert not hasattr(bloco_copy, "_copy_deterministica_fallback"), \
        "_copy_deterministica_fallback should be removed (fail-fast)"


def test_bloco_copy_imports_correctly():
    """Test that bloco_copy module imports without errors."""
    import bloco_copy

    # Module should import successfully
    assert hasattr(bloco_copy, "executar_bloco_copy")
    assert hasattr(bloco_copy, "CopyGenerationError")
