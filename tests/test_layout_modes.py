"""
============================================================================
TESTES: Layout Modes por secao/polo (Etapa 2)
============================================================================

Sprint 12.x: vite_liquid_components.py expoe Services e Gallery display
modes alem do Hero. Cada polo (SOFT/BOLD/CLASSIC/MINIMAL) deve ter modos
proprios com caracteristicas visuais distintas.

Validacoes:
1. SERVICES_DISPLAY_MODES tem 4 polos com modos proprios
2. GALLERY_DISPLAY_MODES tem 4 polos com modos proprios
3. get_services_display_mode retorna default correto por polo
4. get_gallery_display_mode retorna default correto por polo
5. Cada polo tem caracteristicas visuais distintas (container/card_class)
6. get_liquid_component_guide inclui Services e Gallery alem do Hero
7. Renderer importa os novos helpers
============================================================================
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_PATH = _PROJECT_ROOT / "backend"
_SERVICES_PATH = _BACKEND_PATH / "services"
for _p in (str(_BACKEND_PATH), str(_SERVICES_PATH), str(_PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# 1. SERVICES_DISPLAY_MODES tem 4 polos
# ═══════════════════════════════════════════════════════════════════════════

class TestServicesDisplayModesExist:
    """SERVICES_DISPLAY_MODES define 4 polos com modos proprios."""

    def test_4_polos_definidos(self):
        from backend.services.vite_liquid_components import SERVICES_DISPLAY_MODES
        polos = set(SERVICES_DISPLAY_MODES.keys())
        assert polos == {"soft", "bold", "corporate", "minimal"}

    def test_soft_tem_pelo_menos_1_modo(self):
        from backend.services.vite_liquid_components import SERVICES_DISPLAY_MODES
        assert len(SERVICES_DISPLAY_MODES["soft"]) >= 1

    def test_bold_tem_pelo_menos_1_modo(self):
        from backend.services.vite_liquid_components import SERVICES_DISPLAY_MODES
        assert len(SERVICES_DISPLAY_MODES["bold"]) >= 1

    def test_corporate_tem_pelo_menos_1_modo(self):
        from backend.services.vite_liquid_components import SERVICES_DISPLAY_MODES
        assert len(SERVICES_DISPLAY_MODES["corporate"]) >= 1

    def test_minimal_tem_pelo_menos_1_modo(self):
        from backend.services.vite_liquid_components import SERVICES_DISPLAY_MODES
        assert len(SERVICES_DISPLAY_MODES["minimal"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# 2. GALLERY_DISPLAY_MODES tem 4 polos
# ═══════════════════════════════════════════════════════════════════════════

class TestGalleryDisplayModesExist:
    """GALLERY_DISPLAY_MODES define 4 polos com modos proprios."""

    def test_4_polos_definidos(self):
        from backend.services.vite_liquid_components import GALLERY_DISPLAY_MODES
        assert set(GALLERY_DISPLAY_MODES.keys()) == {"soft", "bold", "corporate", "minimal"}

    def test_cada_polo_tem_pelo_menos_1_modo(self):
        from backend.services.vite_liquid_components import GALLERY_DISPLAY_MODES
        for polo in ("soft", "bold", "corporate", "minimal"):
            assert len(GALLERY_DISPLAY_MODES[polo]) >= 1, f"Polo {polo} sem modos"


# ═══════════════════════════════════════════════════════════════════════════
# 3. get_services_display_mode retorna default correto por polo
# ═══════════════════════════════════════════════════════════════════════════

class TestGetServicesDisplayMode:
    """get_services_display_mode retorna modo default por polo."""

    def test_soft_default_stacked_cards(self):
        from backend.services.vite_liquid_components import get_services_display_mode
        config = get_services_display_mode("soft")
        assert config.get("name") == "Stacked Editorial Cards"

    def test_bold_default_mosaic(self):
        from backend.services.vite_liquid_components import get_services_display_mode
        config = get_services_display_mode("bold")
        assert config.get("name") == "Mosaic Aggressive"

    def test_corporate_default_three_column(self):
        from backend.services.vite_liquid_components import get_services_display_mode
        config = get_services_display_mode("corporate")
        assert config.get("name") == "Three Column Grid"

    def test_minimal_default_bento_grid(self):
        from backend.services.vite_liquid_components import get_services_display_mode
        config = get_services_display_mode("minimal")
        assert config.get("name") == "Bento Grid"

    def test_polo_desconhecido_caem_em_corporate(self):
        from backend.services.vite_liquid_components import get_services_display_mode
        config = get_services_display_mode("nicho_xyz")
        assert config.get("name") == "Three Column Grid"

    def test_modo_especifico(self):
        from backend.services.vite_liquid_components import get_services_display_mode
        config = get_services_display_mode("soft", mode="alternating_split")
        assert config.get("name") == "Alternating Split"

    def test_modo_invalido_caem_em_default(self):
        from backend.services.vite_liquid_components import get_services_display_mode
        config = get_services_display_mode("soft", mode="nao_existe")
        assert config.get("name") == "Stacked Editorial Cards"


# ═══════════════════════════════════════════════════════════════════════════
# 4. get_gallery_display_mode retorna default correto por polo
# ═══════════════════════════════════════════════════════════════════════════

class TestGetGalleryDisplayMode:
    """get_gallery_display_mode retorna modo default por polo."""

    def test_soft_default_masonry(self):
        from backend.services.vite_liquid_components import get_gallery_display_mode
        config = get_gallery_display_mode("soft")
        assert config.get("name") == "Masonry Soft"

    def test_bold_default_mosaic_chaos(self):
        from backend.services.vite_liquid_components import get_gallery_display_mode
        config = get_gallery_display_mode("bold")
        assert config.get("name") == "Mosaic Chaos"

    def test_corporate_default_grid_clean(self):
        from backend.services.vite_liquid_components import get_gallery_display_mode
        config = get_gallery_display_mode("corporate")
        assert config.get("name") == "Grid Clean"

    def test_minimal_default_bento_gallery(self):
        from backend.services.vite_liquid_components import get_gallery_display_mode
        config = get_gallery_display_mode("minimal")
        assert config.get("name") == "Bento Gallery"

    def test_polo_desconhecido_caem_em_corporate(self):
        from backend.services.vite_liquid_components import get_gallery_display_mode
        config = get_gallery_display_mode("xyz")
        assert config.get("name") == "Grid Clean"


# ═══════════════════════════════════════════════════════════════════════════
# 5. Caracteristicas visuais distintas entre polos
# ═══════════════════════════════════════════════════════════════════════════

class TestVisualIdentityPorPolo:
    """Cada polo tem caracteristicas visuais proprias (nao mistura tokens)."""

    def test_services_soft_tem_radius_grande(self):
        from backend.services.vite_liquid_components import get_services_display_mode
        cfg = get_services_display_mode("soft")
        assert "rounded" in cfg.get("card_class", "")
        assert "[40px]" in cfg.get("card_class", "") or "[32px]" in cfg.get("card_class", "")

    def test_services_bold_tem_radius_zero(self):
        from backend.services.vite_liquid_components import get_services_display_mode
        cfg = get_services_display_mode("bold")
        assert "rounded-none" in cfg.get("card_class", "")

    def test_services_corporate_tem_radius_md(self):
        from backend.services.vite_liquid_components import get_services_display_mode
        cfg = get_services_display_mode("corporate")
        assert "rounded-md" in cfg.get("card_class", "")

    def test_services_minimal_tem_glass_card(self):
        from backend.services.vite_liquid_components import get_services_display_mode
        cfg = get_services_display_mode("minimal")
        assert "glass-card" in cfg.get("card_class", "") or "rounded-xl" in cfg.get("card_class", "")

    def test_gallery_bold_grayscale(self):
        """BOLD gallery usa grayscale (image_treatment agressivo)."""
        from backend.services.vite_liquid_components import get_gallery_display_mode
        cfg = get_gallery_display_mode("bold")
        assert cfg.get("image_treatment") == "grayscale"

    def test_gallery_soft_warm(self):
        """SOFT gallery usa warm (image_treatment acolhedor)."""
        from backend.services.vite_liquid_components import get_gallery_display_mode
        cfg = get_gallery_display_mode("soft")
        assert cfg.get("image_treatment") == "warm"

    def test_gallery_minimal_glass(self):
        """MINIMAL gallery usa glass (image_treatment tech)."""
        from backend.services.vite_liquid_components import get_gallery_display_mode
        cfg = get_gallery_display_mode("minimal")
        assert cfg.get("image_treatment") == "glass"

    def test_container_class_diferente_entre_polos_services(self):
        """Cada polo tem container CSS diferente (nao compartilha o mesmo)."""
        from backend.services.vite_liquid_components import get_services_display_mode
        containers = {
            polo: get_services_display_mode(polo).get("container", "")
            for polo in ("soft", "bold", "corporate", "minimal")
        }
        # Pelo menos 3 devem ser diferentes (BOLD/CORPORATE/MINIMAL ja tem layouts distintos)
        unique_containers = len(set(containers.values()))
        assert unique_containers >= 3, f"Containers muito parecidos: {containers}"


# ═══════════════════════════════════════════════════════════════════════════
# 6. get_liquid_component_guide inclui Services e Gallery
# ═══════════════════════════════════════════════════════════════════════════

class TestLiquidComponentGuideIncluiServicesGallery:
    """Guide de polo inclui informacoes de Services e Gallery."""

    def test_guide_para_soft_contem_services(self):
        from backend.services.vite_liquid_components import get_liquid_component_guide
        guide = get_liquid_component_guide("soft")
        assert "SERVICES DISPLAY MODE" in guide

    def test_guide_para_soft_contem_gallery(self):
        from backend.services.vite_liquid_components import get_liquid_component_guide
        guide = get_liquid_component_guide("soft")
        assert "GALLERY DISPLAY MODE" in guide

    def test_guide_para_bold_contem_mosaic(self):
        from backend.services.vite_liquid_components import get_liquid_component_guide
        guide = get_liquid_component_guide("bold")
        assert "Mosaic Aggressive" in guide

    def test_guide_para_minimal_contem_bento(self):
        from backend.services.vite_liquid_components import get_liquid_component_guide
        guide = get_liquid_component_guide("minimal")
        assert "Bento" in guide


# ═══════════════════════════════════════════════════════════════════════════
# 7. Renderer importa os novos helpers
# ═══════════════════════════════════════════════════════════════════════════

class TestRendererImportaNovosHelpers:
    """vite_react_renderer importa get_services_display_mode e get_gallery_display_mode."""

    def test_renderer_tem_import_de_services(self):
        """Verifica que o renderer referencia o helper (estaticamente)."""
        from pathlib import Path
        p = Path("backend/services/vite_react_renderer.py")
        content = p.read_text(encoding="utf-8")
        assert "get_services_display_mode" in content

    def test_renderer_tem_import_de_gallery(self):
        from pathlib import Path
        p = Path("backend/services/vite_react_renderer.py")
        content = p.read_text(encoding="utf-8")
        assert "get_gallery_display_mode" in content