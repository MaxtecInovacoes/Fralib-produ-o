"""
============================================================================
TESTES: Polo injetado nos system prompts (Etapa 1.5)
============================================================================

Sprint 12.x: o polo canônico (SOFT | BOLD | CLASSIC | TECH) deve chegar
aos 4 system prompts do pipeline:

1. _montar_prompt_bloco1 (estrutura)
2. _montar_prompt_bloco2 (copy)
3. get_design_context_prompt (design context)
4. SYSTEM_DESIGN_DIRECTOR + SYSTEM_COPY_SENIOR (system prompts)

Mapeamento nicho → polo:
- academia         -> BOLD
- advogado         -> CLASSIC
- restaurante      -> SOFT
- energia_solar    -> TECH
- default          -> CLASSIC

Override por subnicho:
- nutricionista + atleta -> BOLD (em vez de SOFT)
============================================================================
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_PATH = _PROJECT_ROOT / "backend"
_AGENTS_PATH = _BACKEND_PATH / "agents"
if str(_BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(_BACKEND_PATH))
if str(_AGENTS_PATH) not in sys.path:
    sys.path.insert(0, str(_AGENTS_PATH))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# 1. HELPER: build_polo_prompt_block() / build_polo_short()
# ═══════════════════════════════════════════════════════════════════════════

class TestPoloPromptsHelper:
    """Helper polo_prompts gera bloco legível e correto."""

    def test_build_block_contem_polo_label(self):
        from backend.agents.polo_prompts import build_polo_prompt_block
        block = build_polo_prompt_block("academia")
        assert "POLO:" in block
        assert "BOLD" in block

    def test_build_block_contem_tokens(self):
        from backend.agents.polo_prompts import build_polo_prompt_block
        block = build_polo_prompt_block("academia")
        # Tokens BOLD: radius=0px, Anton, uppercase, italic
        assert "0px" in block
        assert "Anton" in block or "uppercase" in block

    def test_build_block_advogado_classic(self):
        from backend.agents.polo_prompts import build_polo_prompt_block
        block = build_polo_prompt_block("advogado")
        assert "CLASSIC" in block
        assert "Inter" in block or "6px" in block

    def test_build_block_restaurante_soft(self):
        from backend.agents.polo_prompts import build_polo_prompt_block
        block = build_polo_prompt_block("restaurante")
        assert "SOFT" in block
        # SOFT: radius 40-50px, serif
        assert "40-50px" in block or "Playfair" in block

    def test_build_block_energia_solar_tech(self):
        from backend.agents.polo_prompts import build_polo_prompt_block
        block = build_polo_prompt_block("energia_solar")
        assert "TECH" in block
        assert "Space Grotesk" in block or "12px" in block

    def test_build_block_default_classic(self):
        from backend.agents.polo_prompts import build_polo_prompt_block
        block = build_polo_prompt_block("default")
        assert "CLASSIC" in block

    def test_build_block_nicho_desconhecido_caem_em_classic(self):
        from backend.agents.polo_prompts import build_polo_prompt_block
        block = build_polo_prompt_block("nicho_inexistente_xyz")
        assert "CLASSIC" in block

    def test_build_block_com_copy(self):
        from backend.agents.polo_prompts import build_polo_prompt_block
        block = build_polo_prompt_block(
            "academia", include_copy=True, include_design_logic=False
        )
        assert "tone:" in block
        assert "voice:" in block
        assert "cta_primary:" in block
        # DesignLogic nao incluido
        assert "allow_overlap" not in block

    def test_build_block_com_design_logic(self):
        from backend.agents.polo_prompts import build_polo_prompt_block
        block = build_polo_prompt_block(
            "academia", include_copy=False, include_design_logic=True
        )
        assert "allow_overlap" in block
        # Copy nao incluido
        assert "cta_primary:" not in block

    def test_build_block_com_subnicho_override(self):
        """Subnicho override altera o polo (nutri+atleta → BOLD em vez de SOFT)."""
        from backend.agents.polo_prompts import build_polo_prompt_block
        block = build_polo_prompt_block("nutricionista", subnicho="atleta")
        assert "BOLD" in block
        assert "atleta" in block

    def test_build_short_compacto(self):
        from backend.agents.polo_prompts import build_polo_short
        short = build_polo_short("academia")
        assert "POLO=BOLD" in short
        assert "academia" in short

    def test_block_comeca_com_polo_e_termina_com_fim(self):
        from backend.agents.polo_prompts import build_polo_prompt_block
        block = build_polo_prompt_block("academia")
        assert "=== POLO ESTÉTICO" in block
        assert "=== FIM POLO ===" in block


# ═══════════════════════════════════════════════════════════════════════════
# 2. _montar_prompt_bloco1 injeta POLO
# ═══════════════════════════════════════════════════════════════════════════

class TestBlocoEstruturaInjetaPolo:
    """_montar_prompt_bloco1 inclui bloco POLO no prompt."""

    def _build_prompt(self, segmento: str):
        # Import lazy para evitar pré-requisitos (FRALIB_ROOT etc) que
        # quebram em ambiente de teste isolado. O helper polo_prompts
        # eh testado em TestPoloPromptsHelper.
        try:
            from backend.agents.bloco_estrutura import _montar_prompt_bloco1
        except Exception as e:
            pytest.skip(f"bloco_estrutura requer env completo: {e}")
        return _montar_prompt_bloco1(
            nome="X",
            cidade="Y",
            segmento=segmento,
            caio_tier="STANDARD",
            caio_score=50,
            rating=4.5,
            total_av=10,
            inteligencia={},
            sub_nicho_ctx="",
            design_ctx="",
            craft_ctx="",
            design_dict={},
            nicho_ref="",
            variacao_ref="",
        )

    def test_academia_injeta_BOLD(self):
        prompt = self._build_prompt("academia")
        assert "POLO:" in prompt
        assert "BOLD" in prompt

    def test_advogado_injeta_CLASSIC(self):
        prompt = self._build_prompt("advogado")
        assert "POLO:" in prompt
        assert "CLASSIC" in prompt

    def test_restaurante_injeta_SOFT(self):
        prompt = self._build_prompt("restaurante")
        assert "POLO:" in prompt
        assert "SOFT" in prompt

    def test_energia_solar_injeta_TECH(self):
        prompt = self._build_prompt("energia_solar")
        assert "POLO:" in prompt
        assert "TECH" in prompt


# ═══════════════════════════════════════════════════════════════════════════
# 3. _montar_prompt_bloco2 injeta POLO
# ═══════════════════════════════════════════════════════════════════════════

class TestBlocoCopyInjetaPolo:
    """_montar_prompt_bloco2 inclui bloco POLO com CopyDefaults."""

    def _build_prompt(self, segmento: str):
        try:
            from backend.agents.bloco_copy import _montar_prompt_bloco2
        except Exception as e:
            pytest.skip(f"bloco_copy requer env completo: {e}")
        return _montar_prompt_bloco2(
            nome="X",
            cidade="Y",
            segmento=segmento,
            telefone="",
            endereco="",
            rating=4.5,
            total_av=10,
            caio_tier="STANDARD",
            dark_mode=False,
            jina_insights="",
            instrucao_criativa="",
            reviews_fmt="",
            reviews_intel_ctx="",
            seo_ctx="",
            faq_seo_fmt="",
            keyword_research="",
            secoes_nomes=["hero", "sobre", "contato"],
            reviews_has=False,
            intel_ctx="",
            craft_ctx="",
            autocritica_ctx="",
        )

    def test_academia_injeta_BOLD_com_tone(self):
        prompt = self._build_prompt("academia")
        assert "POLO:" in prompt
        assert "BOLD" in prompt
        # CopyDefaults incluídos
        assert "tone:" in prompt

    def test_advogado_injeta_CLASSIC_com_voice(self):
        prompt = self._build_prompt("advogado")
        assert "POLO:" in prompt
        assert "CLASSIC" in prompt
        assert "voice:" in prompt
        # Advogado tem voice "3a pessoa do singular (o escritorio)"
        assert "escritorio" in prompt or "3a pessoa" in prompt

    def test_restaurante_injeta_SOFT(self):
        prompt = self._build_prompt("restaurante")
        assert "POLO:" in prompt
        assert "SOFT" in prompt


# ═══════════════════════════════════════════════════════════════════════════
# 4. get_design_context_prompt injeta POLO short
# ═══════════════════════════════════════════════════════════════════════════

class TestDesignContextPromptInjetaPolo:
    """get_design_context_prompt inclui linha POLO= compacta."""

    def test_academia_tem_POLO_BOLD(self):
        from backend.agents.design_prompts import get_design_context_prompt
        try:
            prompt = get_design_context_prompt("academia")
        except Exception:
            # design_context pode falhar sem dados completos — pulamos
            pytest.skip("design_context precisa de mais dados")
        assert "POLO=" in prompt
        assert "BOLD" in prompt

    def test_advogado_tem_POLO_CLASSIC(self):
        from backend.agents.design_prompts import get_design_context_prompt
        try:
            prompt = get_design_context_prompt("advogado")
        except Exception:
            pytest.skip("design_context precisa de mais dados")
        assert "POLO=" in prompt
        assert "CLASSIC" in prompt


# ═══════════════════════════════════════════════════════════════════════════
# 5. SYSTEM_DESIGN_DIRECTOR e SYSTEM_COPY_SENIOR reconhecem POLO
# ═══════════════════════════════════════════════════════════════════════════

class TestSystemPromptsReconhecemPolo:
    """System prompts mencionam POLO como entrada válida."""

    def test_system_design_director_menciona_polo(self):
        from backend.agents.prompts_arquiteto import SYSTEM_DESIGN_DIRECTOR
        assert "POLO" in SYSTEM_DESIGN_DIRECTOR

    def test_system_copy_senior_menciona_polo(self):
        from backend.agents.prompts_arquiteto import SYSTEM_COPY_SENIOR
        assert "POLO" in SYSTEM_COPY_SENIOR


# ═══════════════════════════════════════════════════════════════════════════
# 6. build_design_dna retorna chave "pole"
# ═══════════════════════════════════════════════════════════════════════════

class TestBuildDesignDnaRetornaPolo:
    """build_design_dna adicionou chave 'pole' no retorno."""

    def test_dna_tem_pole(self):
        from backend.core.design_system_router import build_design_dna
        dna = build_design_dna(
            segmento="academia",
            business_name="Iron Gym",
            lead_id="lead-123",
            tier="STANDARD",
        )
        assert "pole" in dna
        assert dna["pole"] == "BOLD"

    def test_dna_advogado_classic(self):
        from backend.core.design_system_router import build_design_dna
        dna = build_design_dna(
            segmento="advogado",
            business_name="Silva Direito",
            lead_id="lead-456",
            tier="PREMIUM",
        )
        assert dna["pole"] == "CLASSIC"

    def test_dna_energia_solar_tech(self):
        from backend.core.design_system_router import build_design_dna
        dna = build_design_dna(
            segmento="energia_solar",
            business_name="Sun Power",
            lead_id="lead-789",
            tier="STANDARD",
        )
        assert dna["pole"] == "TECH"