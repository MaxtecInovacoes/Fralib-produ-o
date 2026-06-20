from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BRYAN = ROOT / "backend" / "agents" / "bryan.py"
pytestmark = [
    pytest.mark.legacy,
    pytest.mark.skipif(not BRYAN.exists(), reason="Bryan runtime is legacy and absent from active pipeline"),
]


def _source() -> str:
    return BRYAN.read_text(encoding="utf-8")


def test_bryan_history_loader_is_tenant_scoped():
    source = _source()
    start = source.index("def _carregar_historico_interacoes")
    end = source.index("# Função criar_agente_bryan")
    block = source[start:end]

    assert "user_id: int | None = None" in block
    assert "not user_id" in block
    assert "l.user_id = :uid" in block
    assert "COALESCE(i.user_id, l.user_id) = :uid" in block
    assert '"uid": user_id' in block


def test_bryan_history_calls_pass_user_id():
    source = _source()

    assert source.count("_carregar_historico_interacoes(") == 4
    assert "user_id=user_id" in source[
        source.index("historico_raw = _carregar_historico_interacoes") :
    ]


def test_bryan_has_segment_guardrail_fallback():
    source = _source()

    assert "def aplicar_guardrail_segmento" in source
    assert "G12_segment_contamination" in source
    assert "aplicar_guardrail_segmento(" in source


def test_intro_exception_fallback_persists_memory():
    source = _source()
    start = source.index("except Exception as e:")
    start = source.index("Fallback hardcoded", start)
    end = source.index("def _consultar_aprendizado_segmento")
    block = source[start:end]

    assert "intro_fallback_memory" in block
    assert "salvar_memoria(" in block
    assert '"lead": lead.model_dump()' in block
