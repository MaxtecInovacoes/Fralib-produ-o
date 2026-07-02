"""
============================================================================
TESTES: DesignLogic + resolve_polo_for_lead — Camada de DNA Estrutural
============================================================================
Cobertura: presets por polo, DesignLogic por nicho, sub-nicho overrides.
============================================================================
"""

import pytest
import sys

sys.path.insert(0, ".")


# ────────────────────────────────────────────────────────────────────────
# 1. DESIGNLOGIC PRESETS
# ────────────────────────────────────────────────────────────────────────

class TestDesignLogicPresets:
    """Cada polo tem um DNA geométrico próprio."""

    def test_design_soft_tem_radius_maximo(self):
        from backend.config.nicho_registry import get_design_logic
        dl = get_design_logic("nutricionista")  # SOFT
        assert dl.radius_multiplier >= 1.5
        assert dl.spacing_multiplier >= 1.5
        assert dl.allow_overlap is False
        assert dl.allow_skew is False

    def test_design_bold_tem_radius_zero_e_overlap(self):
        from backend.config.nicho_registry import get_design_logic
        dl = get_design_logic("academia")  # BOLD
        assert dl.radius_multiplier == 0.0
        assert dl.spacing_multiplier <= 1.0
        assert dl.allow_overlap is True
        assert dl.allow_skew is True
        assert dl.allow_text_stroke is True

    def test_design_classic_balanceado(self):
        from backend.config.nicho_registry import get_design_logic
        dl = get_design_logic("advogado")  # CLASSIC
        assert 0.3 <= dl.radius_multiplier <= 0.7
        assert dl.allow_overlap is False
        assert dl.allow_skew is False

    def test_design_tech_tem_glass(self):
        from backend.config.nicho_registry import get_design_logic
        dl = get_design_logic("energia_solar")  # TECH
        assert dl.image_treatment == "glass"

    def test_design_bold_tem_grayscale(self):
        from backend.config.nicho_registry import get_design_logic
        dl = get_design_logic("academia")  # BOLD
        assert dl.image_treatment == "grayscale"

    def test_design_soft_tem_warm(self):
        from backend.config.nicho_registry import get_design_logic
        dl = get_design_logic("estetica")  # SOFT
        assert dl.image_treatment == "warm"


# ────────────────────────────────────────────────────────────────────────
# 2. DESIGNLOGIC GALLERY DENSITY
# ────────────────────────────────────────────────────────────────────────

class TestGalleryDensity:
    """Cada polo tem densidade de galeria própria."""

    def test_academia_tem_mosaic(self):
        from backend.config.nicho_registry import get_design_logic
        dl = get_design_logic("academia")
        assert dl.gallery_density == "mosaic"

    def test_estetica_tem_editorial(self):
        from backend.config.nicho_registry import get_design_logic
        dl = get_design_logic("estetica")
        assert dl.gallery_density == "editorial"

    def test_energia_solar_tem_tight(self):
        from backend.config.nicho_registry import get_design_logic
        dl = get_design_logic("energia_solar")
        assert dl.gallery_density == "tight"

    def test_advogado_tem_balanced(self):
        from backend.config.nicho_registry import get_design_logic
        dl = get_design_logic("advogado")
        assert dl.gallery_density == "balanced"


# ────────────────────────────────────────────────────────────────────────
# 3. RESOLVE_POLO_FOR_LEAD
# ────────────────────────────────────────────────────────────────────────

class TestResolvePoloForLead:
    """Hierarquia de resolução de polo."""

    def test_nivel_1_override_subnicho(self):
        """Override por subnicho tem prioridade sobre o default do nicho."""
        from backend.config.nicho_registry import resolve_polo_for_lead
        # academia/yoga → SOFT (override), embora academia default seja BOLD
        assert resolve_polo_for_lead("academia", "yoga") == "SOFT"

    def test_nivel_2_polo_do_nicho(self):
        """Sem override, usa polo_sugerido do nicho."""
        from backend.config.nicho_registry import resolve_polo_for_lead
        assert resolve_polo_for_lead("academia", None) == "BOLD"
        assert resolve_polo_for_lead("estetica", None) == "SOFT"
        assert resolve_polo_for_lead("advogado", None) == "CLASSIC"
        assert resolve_polo_for_lead("energia_solar", None) == "TECH"

    def test_nivel_3_inferido(self):
        """Se nicho é None, usa polo inferido."""
        from backend.config.nicho_registry import resolve_polo_for_lead
        assert resolve_polo_for_lead(None, None, "BOLD") == "BOLD"
        assert resolve_polo_for_lead(None, None, "SOFT") == "SOFT"

    def test_nivel_4_fallback(self):
        """Se nada definido, retorna CLASSIC."""
        from backend.config.nicho_registry import resolve_polo_for_lead
        assert resolve_polo_for_lead(None, None, None) == "CLASSIC"
        assert resolve_polo_for_lead("", "", "") == "CLASSIC"

    def test_override_normalizado_para_lowercase(self):
        from backend.config.nicho_registry import resolve_polo_for_lead
        assert resolve_polo_for_lead("Nutricionista", "ATLETA") == "BOLD"
        assert resolve_polo_for_lead("ACADEMIA", "Yoga") == "SOFT"


# ────────────────────────────────────────────────────────────────────────
# 4. SUB-NICHO OVERRIDES POR NICHO
# ────────────────────────────────────────────────────────────────────────

class TestSubNichoOverrides:
    """Casos críticos de override."""

    @pytest.mark.parametrize("nicho,subnicho,polo_esperado", [
        # Nutri
        ("nutricionista", "atleta", "BOLD"),
        ("nutricionista", "atletas", "BOLD"),
        ("nutricionista", "performance", "BOLD"),
        ("nutricionista", "esportivo", "BOLD"),
        ("nutricionista", "infantil", "SOFT"),
        ("nutricionista", "crianca", "SOFT"),
        ("nutricionista", "gestante", "SOFT"),
        ("nutricionista", "emagrecimento", "CLASSIC"),

        # Academia
        ("academia", "yoga", "SOFT"),
        ("academia", "pilates", "SOFT"),
        ("academia", "alongamento", "SOFT"),
        ("academia", "funcional", "BOLD"),
        ("academia", "crossfit", "BOLD"),
        ("academia", "musculacao", "BOLD"),
        ("academia", "boxe", "BOLD"),
        ("academia", "mma", "BOLD"),
        ("academia", "jiu_jitsu", "BOLD"),

        # Estética
        ("estetica", "harmonizacao", "SOFT"),
        ("estetica", "botox", "SOFT"),
        ("estetica", "preenchimento", "SOFT"),
        ("estetica", "limpeza_de_pele", "SOFT"),
        ("estetica", "cirurgia", "CLASSIC"),
        ("estetica", "clinica_medica", "CLASSIC"),

        # Advogado
        ("advogado", "criminal", "CLASSIC"),
        ("advogado", "trabalhista", "CLASSIC"),
        ("advogado", "civil", "CLASSIC"),
        ("advogado", "familia", "CLASSIC"),
        ("advogado", "empresarial", "TECH"),
        ("advogado", "tributario", "TECH"),
        ("advogado", "compliance", "TECH"),

        # Restaurante
        ("restaurante", "vegetariano", "SOFT"),
        ("restaurante", "vegano", "SOFT"),
        ("restaurante", "natural", "SOFT"),
        ("restaurante", "fast_food", "BOLD"),
        ("restaurante", "hamburgueria", "BOLD"),
        ("restaurante", "pizzaria", "BOLD"),
        ("restaurante", "executivo", "CLASSIC"),
        ("restaurante", "fine_dining", "CLASSIC"),
    ])
    def test_override_subnicho(self, nicho, subnicho, polo_esperado):
        from backend.config.nicho_registry import resolve_polo_for_lead
        result = resolve_polo_for_lead(nicho, subnicho)
        assert result == polo_esperado, \
            f"{nicho}/{subnicho} → {result}, esperado {polo_esperado}"


# ────────────────────────────────────────────────────────────────────────
# 5. CONSISTÊNCIA: DESIGNLOGIC BATE COM POLO
# ────────────────────────────────────────────────────────────────────────

class TestConsistenciaPoloDesign:
    """DesignLogic deve refletir o polo_sugerido do nicho."""

    @pytest.mark.parametrize("nicho,polo_esperado,multiplicador_max_radius", [
        ("academia", "BOLD", 0.3),       # BOLD tem radius próximo de 0
        ("estetica", "SOFT", 2.0),        # SOFT tem radius máximo
        ("advogado", "CLASSIC", 0.7),     # CLASSIC tem radius médio
        ("energia_solar", "TECH", 1.5),   # TECH tem radius intermediário
    ])
    def test_radius_bate_com_polo(self, nicho, polo_esperado, multiplicador_max_radius):
        from backend.config.nicho_registry import get_nicho_config, get_design_logic
        cfg = get_nicho_config(nicho)
        dl = get_design_logic(nicho)
        assert cfg.polo_sugerido == polo_esperado
        assert dl.radius_multiplier <= multiplicador_max_radius


# ────────────────────────────────────────────────────────────────────────
# 6. TODOS OS NICHOS TÊM DESIGNLOGIC
# ────────────────────────────────────────────────────────────────────────

class TestTodosNichosTemDesignLogic:
    """DesignLogic é obrigatório em todas as entradas."""

    def test_todos_nichos_tem_design_logic(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        for key, cfg in NICHO_CONFIG.items():
            assert cfg.design_logic is not None, f"{key} sem design_logic"
            assert isinstance(cfg.design_logic.radius_multiplier, float)
            assert isinstance(cfg.design_logic.spacing_multiplier, float)
            assert isinstance(cfg.design_logic.allow_overlap, bool)
            assert isinstance(cfg.design_logic.allow_skew, bool)
            assert isinstance(cfg.design_logic.allow_text_stroke, bool)
            assert cfg.design_logic.image_treatment in {
                "clean", "grayscale", "grain", "warm", "glass"
            }
            assert cfg.design_logic.gallery_density in {
                "tight", "balanced", "editorial", "mosaic"
            }


# ────────────────────────────────────────────────────────────────────────
# 7. IMUTABILIDADE DO DESIGNLOGIC
# ────────────────────────────────────────────────────────────────────────

class TestDesignLogicImutavel:
    """DesignLogic é frozen=True."""

    def test_design_logic_imutavel(self):
        from backend.config.nicho_registry import get_design_logic
        dl = get_design_logic("academia")
        with pytest.raises(Exception):
            dl.radius_multiplier = 99.0  # type: ignore

    def test_multiplicadores_sao_float(self):
        from backend.config.nicho_registry import get_design_logic
        for nicho in ("academia", "estetica", "advogado", "energia_solar"):
            dl = get_design_logic(nicho)
            assert isinstance(dl.radius_multiplier, float)
            assert isinstance(dl.spacing_multiplier, float)