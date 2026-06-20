import sys
from pathlib import Path


AGENTS_DIR = Path(__file__).resolve().parents[2] / "backend" / "agents"
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))


def test_bloco_copy_returns_deterministic_copy_when_llms_timeout(monkeypatch):
    import bloco_copy

    def fail_call(*args, **kwargs):
        raise TimeoutError("llm timeout")

    monkeypatch.setattr(bloco_copy, "call_claude", fail_call)

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

    assert result["_fallback"] == "deterministic_copy"
    assert len(result["sections"]) == 6
    hero = result["sections"][0]["copy"]
    assert "Campina Grande do Sul" in hero["h1"]
    assert "High Fitness Academia" in hero["subtitulo"]
    services = next(s for s in result["sections"] if s["name"] == "servicos")
    assert services["copy"]["items"] == ""
    assert "Musculacao" not in str(result)
    location = next(s for s in result["sections"] if s["name"] == "localizacao")
    assert "Maria Augusta" in location["copy"]["body"]


def test_bloco_copy_deterministic_fallback_does_not_invent_address():
    import bloco_copy

    result = bloco_copy._copy_deterministica_fallback(
        nome="Studio Teste",
        cidade="Curitiba",
        segmento="Pilates",
        telefone="",
        endereco="",
        rating=0,
        total_av=0,
        secoes_nomes=["localizacao", "contato"],
        reviews_raw=[],
    )

    location = result["sections"][0]
    assert location["omitir"] is True
    assert location["copy"]["body"] == "Curitiba"
    assert "Rua" not in str(result)
