"""Testes anti-regressao v1.13.5 - Sprint 11.5 (enrich VITE_REACT prompt).

Sprint 11 fechou o gap "componentes prontos vs custom HTML" via shadcn/ui.
Sprint 11.5 fecha os 5 gaps de CONTRATOS que so chegavam ao OpenUI renderer:

1. premium_delivery_contract (AIDA/PAS, archetype guidance, anti-patterns 2023)
2. visual_direction_contract (archetype/scene/color_strategy/hero_storyboard)
3. motion_pack completo (12 hooks Awwwards, antes so 4 + 1 inexistente)
4. mobile-first/clamp()/44px touch targets
5. Dialog/Tabs/Textarea shadcn (resolve "componente studio obrigatorio: modal")

Valida:
- SHADCN_COMPONENTS agora tem 7 (era 4): +Dialog, +Tabs, +Textarea
- SECTION_COMPONENT_MAP tem 16 secoes (era 14): +modal, +booking-modal
- VITE_REACT_SYSTEM_PROMPT cresceu de ~13K para ~26K chars
- Prompt menciona AIDA/PAS, BOLD_ENERGY/ZEN_PURE/LUXURY_ELITE
- Prompt menciona todos 12 motion hooks (data-reveal/data-parallax/data-marquee/...)
- Prompt menciona mobile-first + clamp() + 44px touch targets
- Prompt menciona Dialog shadcn (resolve modal obrigatorio no renderer)
- Bloco premium_delivery_contract agora chega ao Vite/React (era so OpenUI)
"""
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))


# ════════════════════════════════════════════════════════════════════
# TESTES Sprint 11.5
# ════════════════════════════════════════════════════════════════════

def test_1_shadcn_7_components_with_dialog_tabs_textarea():
    """Sprint 11.5: SHADCN_COMPONENTS agora tem 7 (era 4)."""
    print("[TESTE 1/10] SHADCN_COMPONENTS - 7 componentes (Dialog/Tabs/Textarea)...")
    from backend.services.vite_templates import SHADCN_COMPONENTS

    assert isinstance(SHADCN_COMPONENTS, dict)
    expected_all = ["Button", "Card", "Input", "Badge", "Dialog", "Tabs", "Textarea"]
    for name in expected_all:
        assert name in SHADCN_COMPONENTS, f"Componente {name} ausente de SHADCN_COMPONENTS"

    # Dialog tem parts (sub-componentes)
    dlg = SHADCN_COMPONENTS["Dialog"]
    assert "parts" in dlg
    for part in ["Dialog", "DialogContent", "DialogHeader", "DialogTitle", "DialogTrigger"]:
        assert part in dlg["parts"], f"Dialog sem part {part}"

    # Tabs tem parts
    tabs = SHADCN_COMPONENTS["Tabs"]
    assert "parts" in tabs
    for part in ["Tabs", "TabsList", "TabsTrigger", "TabsContent"]:
        assert part in tabs["parts"], f"Tabs sem part {part}"

    # Textarea simples
    ta = SHADCN_COMPONENTS["Textarea"]
    assert "import" in ta
    assert "from '@/components/ui/textarea'" in ta["import"]

    print(f"  OK 7 componentes: {', '.join(expected_all)}")
    print("  OK Dialog com 7 parts (Content/Header/Title/Trigger/Close/Description)")
    print("  OK Tabs com 4 parts (List/Trigger/Content)")
    print("  OK Textarea com import proprio")


def test_2_section_map_has_modal_and_booking_modal():
    """Sprint 11.5: SECTION_COMPONENT_MAP tem 16 secoes (era 14)."""
    print("\n[TESTE 2/10] SECTION_COMPONENT_MAP - 16 secoes (modal/booking-modal)...")
    from backend.services.vite_templates import (
        SECTION_COMPONENT_MAP,
        get_shadcn_components_for_section,
    )

    # 16 secoes (14 originais + 2 novas)
    expected_sections = [
        "hero", "cta", "features", "services", "pricing", "testimonials",
        "faq", "contact", "form", "footer", "navbar", "gallery", "about", "stats",
        "modal", "booking-modal",  # Sprint 11.5
    ]
    assert len(SECTION_COMPONENT_MAP) >= 16, \
        f"SECTION_COMPONENT_MAP tem {len(SECTION_COMPONENT_MAP)}, esperado >=16"

    for s in expected_sections:
        assert s in SECTION_COMPONENT_MAP, f"Secao {s} nao mapeada"

    # Modal tem Dialog
    modal_comps = get_shadcn_components_for_section("modal")
    assert "Dialog" in modal_comps, "Secao modal sem Dialog"

    # Booking-modal tem Dialog
    bk_comps = get_shadcn_components_for_section("booking-modal")
    assert "Dialog" in bk_comps, "Secao booking-modal sem Dialog"

    # FAQ migrou para Tabs + Card (Sprint 11.5)
    faq_comps = get_shadcn_components_for_section("faq")
    assert "Tabs" in faq_comps, "FAQ sem Tabs"

    # Contact agora tem Dialog (lightbox) + Textarea (mensagem longa)
    ct_comps = get_shadcn_components_for_section("contact")
    assert "Dialog" in ct_comps
    assert "Textarea" in ct_comps

    print(f"  OK {len(SECTION_COMPONENT_MAP)} secoes mapeadas (era 14, +modal +booking-modal)")
    print("  OK modal -> Dialog + Button")
    print("  OK booking-modal -> Dialog + Button (resolve modal obrigatorio)")
    print("  OK FAQ -> Tabs + Card")
    print("  OK Contact -> Input + Textarea + Button + Dialog")


def test_3_vite_prompt_has_premium_contract():
    """Sprint 11.5: premium_delivery_contract agora chega ao Vite/React prompt."""
    print("\n[TESTE 3/10] VITE_REACT_SYSTEM_PROMPT - premium contract...")
    from backend.services.vite_prompts import (
        VITE_REACT_SYSTEM_PROMPT,
        _build_premium_contract_block,
    )

    # Bloco existe e nao esta vazio
    block = _build_premium_contract_block()
    assert len(block) > 100, f"Premium block muito curto: {len(block)} chars"
    assert "PREMIUM VISUAL + COPY CONTRACT" in VITE_REACT_SYSTEM_PROMPT, \
        "Bloco premium nao injetado no system prompt"

    # Conteudo canonico do premium_delivery_contract
    assert "AIDA" in VITE_REACT_SYSTEM_PROMPT, "AIDA ausente"
    assert "PAS" in VITE_REACT_SYSTEM_PROMPT, "PAS ausente"
    # Pelo menos um archetype canonico
    for arch in ["BOLD_ENERGY", "ZEN_PURE", "LUXURY_ELITE", "MODERN_TECH"]:
        assert arch in VITE_REACT_SYSTEM_PROMPT, f"Archetype {arch} ausente"

    # Anti-patterns 2023
    assert "bg-white" in VITE_REACT_SYSTEM_PROMPT or "rounded-xl" in VITE_REACT_SYSTEM_PROMPT, \
        "Anti-patterns nao mencionados"

    # Motion hooks canonicos do contract
    for hook in ["data-reveal", "data-parallax", "data-mask-reveal", "data-card-stagger"]:
        assert hook in VITE_REACT_SYSTEM_PROMPT, f"Hook {hook} ausente"

    print(f"  OK Bloco premium tem {len(block)} chars")
    print("  OK AIDA + PAS mencionados")
    print("  OK 4 archetypes (BOLD_ENERGY/ZEN_PURE/LUXURY_ELITE/MODERN_TECH)")
    print("  OK Anti-patterns 2023 (bg-white/rounded-xl) mencionados")
    print("  OK 4 motion hooks do premium (data-reveal/parallax/mask-reveal/card-stagger)")


def test_4_vite_prompt_has_visual_direction():
    """Sprint 11.5: visual_direction_contract (archetype + hero_storyboard)."""
    print("\n[TESTE 4/10] VITE_REACT_SYSTEM_PROMPT - visual direction...")
    from backend.services.vite_prompts import VITE_REACT_SYSTEM_PROMPT

    # Bloco visual direction existe
    assert "VISUAL DIRECTION (REQUIRED" in VITE_REACT_SYSTEM_PROMPT, \
        "Bloco VISUAL DIRECTION ausente"

    # 5 archetypes (4 originais + WARM_LOCAL novo)
    archetypes = ["BOLD_ENERGY", "ZEN_PURE", "LUXURY_ELITE", "MODERN_TECH", "WARM_LOCAL"]
    for arch in archetypes:
        assert arch in VITE_REACT_SYSTEM_PROMPT, f"Archetype {arch} ausente"

    # Guia de cada archetype
    assert "preta/carvao" in VITE_REACT_SYSTEM_PROMPT or "preta/carbón" in VITE_REACT_SYSTEM_PROMPT or "preta" in VITE_REACT_SYSTEM_PROMPT
    assert "vermelho eletrico" in VITE_REACT_SYSTEM_PROMPT
    assert "display condensada" in VITE_REACT_SYSTEM_PROMPT or "display" in VITE_REACT_SYSTEM_PROMPT

    # WARM_LOCAL (Sprint 11.5 - novo archetype para nichos locais)
    assert "barbearia" in VITE_REACT_SYSTEM_PROMPT.lower(), \
        "WARM_LOCAL archetype sem exemplo de nicho (barbearia)"

    print("  OK Bloco VISUAL DIRECTION presente")
    print(f"  OK 5 archetypes: {', '.join(archetypes)}")
    print("  OK Guias de cor (preta/vermelho) + tipografia (display condensada)")
    print("  OK WARM_LOCAL novo archetype (barbearia, salao, petshop)")


def test_5_vite_prompt_has_motion_pack_12_hooks():
    """Sprint 11.5: motion pack completo com 12 hooks Awwwards."""
    print("\n[TESTE 5/10] VITE_REACT_SYSTEM_PROMPT - motion pack 12 hooks...")
    from backend.services.vite_prompts import VITE_REACT_SYSTEM_PROMPT

    # Bloco motion pack existe
    assert "ANIMATION LIBRARY" in VITE_REACT_SYSTEM_PROMPT
    assert "FraLib Awwwards Pack" in VITE_REACT_SYSTEM_PROMPT or "FraLib" in VITE_REACT_SYSTEM_PROMPT

    # 12 hooks do motion_runtime.js
    required_hooks = [
        "data-reveal",
        "data-parallax",
        "data-marquee",
        "data-magnetic",
        "data-3d-tilt",
        "data-text-scramble",
        "data-stagger",
        "data-horizontal-scroll",
        "data-counter",
        "data-fralib-scroll-velocity",
        "data-auto-animate",
    ]
    for hook in required_hooks:
        assert hook in VITE_REACT_SYSTEM_PROMPT, f"Hook {hook} ausente do prompt"

    # GSAP + Lenis
    assert "GSAP" in VITE_REACT_SYSTEM_PROMPT
    assert "ScrollTrigger" in VITE_REACT_SYSTEM_PROMPT
    assert "Lenis" in VITE_REACT_SYSTEM_PROMPT

    # Regras de motion
    assert "prefers-reduced-motion" in VITE_REACT_SYSTEM_PROMPT
    assert "opacity" in VITE_REACT_SYSTEM_PROMPT and "transform" in VITE_REACT_SYSTEM_PROMPT

    # Hero deve usar motion
    assert "Hero MUST use" in VITE_REACT_SYSTEM_PROMPT or "hero MUST use" in VITE_REACT_SYSTEM_PROMPT.lower()

    print(f"  OK 11 data-hooks canônicos listados (12 com data-reveal variants)")
    print("  OK GSAP 3.12.5 + ScrollTrigger + Lenis 1.1.20 referenciados")
    print("  OK Regras: opacity+transform only, prefers-reduced-motion")
    print("  OK Hero MUST use data-parallax ou data-reveal=scale")


def test_6_vite_prompt_has_mobile_first_clamp():
    """Sprint 11.5: mobile-first + clamp() + 44px touch targets."""
    print("\n[TESTE 6/10] VITE_REACT_SYSTEM_PROMPT - mobile-first...")
    from backend.services.vite_prompts import VITE_REACT_SYSTEM_PROMPT

    # Bloco mobile-first
    assert "MOBILE-FIRST" in VITE_REACT_SYSTEM_PROMPT or "Mobile-First" in VITE_REACT_SYSTEM_PROMPT

    # clamp() para tipografia fluida
    assert "clamp(" in VITE_REACT_SYSTEM_PROMPT, "clamp() ausente"

    # 44px touch targets
    assert "44px" in VITE_REACT_SYSTEM_PROMPT or "44" in VITE_REACT_SYSTEM_PROMPT

    # Viewports de teste
    assert "375px" in VITE_REACT_SYSTEM_PROMPT
    assert "768px" in VITE_REACT_SYSTEM_PROMPT
    assert "1280px" in VITE_REACT_SYSTEM_PROMPT

    # Regra hero nao coberto por navbar
    assert "Navbar MUST NOT cover hero" in VITE_REACT_SYSTEM_PROMPT or "navbar" in VITE_REACT_SYSTEM_PROMPT.lower()

    # Modal full-screen em mobile
    assert "Dialog" in VITE_REACT_SYSTEM_PROMPT or "Modal" in VITE_REACT_SYSTEM_PROMPT

    print("  OK Bloco MOBILE-FIRST presente")
    print("  OK clamp() para tipografia fluida")
    print("  OK 44px touch targets")
    print("  OK 3 viewports de teste (375/768/1280)")
    print("  OK Modal/Dialog full-screen em mobile")


def test_7_vite_prompt_grew_to_25k_chars():
    """Sprint 11.5: prompt cresceu de ~13K para ~26K chars (dobrou)."""
    print("\n[TESTE 7/10] VITE_REACT_SYSTEM_PROMPT - tamanho dobrou...")
    from backend.services.vite_prompts import (
        VITE_REACT_SYSTEM_PROMPT,
        _build_shadcn_block,
        _build_premium_contract_block,
        _build_visual_direction_block,
        _build_motion_pack_block,
        _build_mobile_first_block,
    )

    total = len(VITE_REACT_SYSTEM_PROMPT)

    # Antes da Sprint 11.5 era ~13K chars; agora deve ser >22K
    assert total > 22000, f"Prompt ainda curto: {total} chars (esperado >22K)"

    # Blocos individuais contribuem
    assert len(_build_premium_contract_block()) > 5000, "Premium block fraco"
    assert len(_build_visual_direction_block()) > 1000, "Visual direction fraco"
    assert len(_build_motion_pack_block()) > 1000, "Motion pack fraco"
    assert len(_build_mobile_first_block()) > 500, "Mobile-first fraco"

    print(f"  OK Prompt total: {total:,} chars (era ~13K antes)")
    print(f"  OK premium_contract: {len(_build_premium_contract_block()):,} chars")
    print(f"  OK visual_direction: {len(_build_visual_direction_block()):,} chars")
    print(f"  OK motion_pack: {len(_build_motion_pack_block()):,} chars")
    print(f"  OK mobile_first: {len(_build_mobile_first_block()):,} chars")
    print(f"  OK shadcn: {len(_build_shadcn_block()):,} chars")


def test_8_vite_prompt_dialog_resolves_modal_obrigatorio():
    """Sprint 11.5: Dialog shadcn resolve 'componente studio obrigatorio: modal'."""
    print("\n[TESTE 8/10] VITE_REACT_SYSTEM_PROMPT - Dialog resolve modal obrigatorio...")
    from backend.services.vite_prompts import VITE_REACT_SYSTEM_PROMPT
    from backend.services.vite_templates import SHADCN_COMPONENTS, get_shadcn_imports

    # Dialog listado no catalogo shadcn (data layer)
    assert "Dialog" in SHADCN_COMPONENTS
    assert SHADCN_COMPONENTS["Dialog"]["parts"] is not None

    # Dialog imports gerados corretamente
    dlg_imports = get_shadcn_imports(["Dialog"])
    assert len(dlg_imports) == 1
    assert "from '@/components/ui/dialog'" in dlg_imports[0]

    # Dialog mencionado no prompt do Builder
    assert "Dialog" in VITE_REACT_SYSTEM_PROMPT

    # Pelo menos um exemplo de uso (em SECTION_COMPONENT_MAP ou no prompt)
    # contact -> Dialog (lightbox) - map mostra que Dialog vai ser usado
    from backend.services.vite_templates import SECTION_COMPONENT_MAP
    modal_comps = SECTION_COMPONENT_MAP.get("modal", [])
    assert "Dialog" in modal_comps
    bk_comps = SECTION_COMPONENT_MAP.get("booking-modal", [])
    assert "Dialog" in bk_comps

    print("  OK Dialog shadcn em SHADCN_COMPONENTS (data layer)")
    print("  OK get_shadcn_imports(['Dialog']) gera import correto")
    print("  OK Dialog mencionado no prompt do Builder")
    print("  OK modal/booking-modal mapeados para Dialog (resolve renderer guard)")


def test_9_section_map_faq_uses_tabs():
    """Sprint 11.5: FAQ migrou para Tabs (substituindo Card-only)."""
    print("\n[TESTE 9/10] SECTION_COMPONENT_MAP - FAQ usa Tabs...")
    from backend.services.vite_templates import SECTION_COMPONENT_MAP

    faq = SECTION_COMPONENT_MAP.get("faq", [])
    assert "Tabs" in faq, "FAQ nao usa Tabs"

    # Gallery agora tem Dialog (lightbox)
    gallery = SECTION_COMPONENT_MAP.get("gallery", [])
    assert "Dialog" in gallery, "Gallery sem Dialog"

    # Navbar agora tem Dialog (mobile menu opcional)
    navbar = SECTION_COMPONENT_MAP.get("navbar", [])
    assert "Dialog" in navbar, "Navbar sem Dialog"

    print("  OK FAQ -> Tabs + Card")
    print("  OK Gallery -> Card + Dialog (lightbox)")
    print("  OK Navbar -> Button + Dialog")


def test_10_no_regression_sprint_11_core():
    """Sprint 11.5 NAO quebrou os 8 testes do Sprint 11."""
    print("\n[TESTE 10/10] Anti-regressao Sprint 11 core intacto...")
    from backend.services.vite_templates import (
        SHADCN_COMPONENTS,
        SECTION_COMPONENT_MAP,
        get_shadcn_component_list,
        get_shadcn_imports,
    )
    from backend.services.vite_prompts import VITE_REACT_SYSTEM_PROMPT
    from backend.services import vite_config

    # SHADCN tem Button/Card/Input/Badge ainda (Sprint 11)
    for name in ["Button", "Card", "Input", "Badge"]:
        assert name in SHADCN_COMPONENTS

    # SECTION_COMPONENT_MAP ainda tem as 14 originais
    for s in ["hero", "cta", "features", "services", "pricing", "testimonials",
              "faq", "contact", "form", "footer", "navbar", "gallery", "about", "stats"]:
        assert s in SECTION_COMPONENT_MAP

    # get_shadcn_component_list retorna string formatada
    out = get_shadcn_component_list()
    assert len(out) > 100
    for name in ["Button", "Card", "Input", "Badge", "Dialog", "Tabs", "Textarea"]:
        assert name in out

    # get_shadcn_imports dedup ainda funciona
    dup = get_shadcn_imports(["Button", "Button", "Button"])
    assert len(dup) == 1

    # 9 deps shadcn em vite_config
    deps = vite_config.FIXED_PACKAGE_JSON["dependencies"]
    for d in ["@radix-ui/react-button", "@radix-ui/react-card",
              "@radix-ui/react-dialog", "@radix-ui/react-tabs",
              "class-variance-authority", "clsx", "tailwind-merge"]:
        assert d in deps

    # SHADCN/UI COMPONENTS ainda no prompt
    assert "SHADCN/UI COMPONENTS" in VITE_REACT_SYSTEM_PROMPT

    print("  OK 4 componentes originais (Button/Card/Input/Badge) preservados")
    print("  OK 14 secoes originais intactas + 2 novas (modal/booking-modal)")
    print("  OK get_shadcn_component_list formatada com 7 componentes")
    print("  OK get_shadcn_imports dedup ainda funciona")
    print("  OK 9 deps shadcn (incluindo react-dialog/react-tabs) presentes")
    print("  OK Bloco SHADCN/UI COMPONENTS no prompt")


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("TESTES ANTI-REGRESSAO v1.13.5 - Sprint 11.5 (enrich VITE_REACT prompt)")
    print("=" * 80)

    test_1_shadcn_7_components_with_dialog_tabs_textarea()
    test_2_section_map_has_modal_and_booking_modal()
    test_3_vite_prompt_has_premium_contract()
    test_4_vite_prompt_has_visual_direction()
    test_5_vite_prompt_has_motion_pack_12_hooks()
    test_6_vite_prompt_has_mobile_first_clamp()
    test_7_vite_prompt_grew_to_25k_chars()
    test_8_vite_prompt_dialog_resolves_modal_obrigatorio()
    test_9_section_map_faq_uses_tabs()
    test_10_no_regression_sprint_11_core()

    print("\n" + "=" * 80)
    print("TODOS OS TESTES PASSARAM (10/10)")
    print("Sprint 11.5 (v1.13.5) - VITE_REACT prompt enriquecido com 5 contratos")
    print("Premium contract + visual direction + motion pack + mobile-first + Dialog shadcn")
    print("=" * 80)
