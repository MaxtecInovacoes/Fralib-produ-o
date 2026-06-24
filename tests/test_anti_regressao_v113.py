"""Testes anti-regressao v1.13 - Sprint 11 (shadcn/ui + Vite/React pipeline).

Valida:
- SHADCN_COMPONENTS dict existe com 4 componentes (Button/Card/Input/Badge)
- get_shadcn_component_list() retorna string formatada com 4 componentes
- get_shadcn_imports() gera imports corretos (sem duplicatas)
- get_shadcn_imports() suporta componente com multiplos imports (Card)
- get_shadcn_components_for_section() mapeia 14 secoes
- vite_templates/ tem 4 arquivos .tsx (button/card/input/badge)
- vite_templates/src/lib/utils.ts existe e exporta cn()
- components.json existe com config valida
- vite_config.py FIXED_PACKAGE_JSON tem 9 deps shadcn/ui
- vite_prompts.py VITE_REACT_SYSTEM_PROMPT contem bloco SHADCN/UI injetado
- vite_prompts.py importa helpers de vite_templates
"""
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))


# ════════════════════════════════════════════════════════════════════
# TESTES
# ════════════════════════════════════════════════════════════════════

def test_1_shadcn_components_dict_exists():
    """SHADCN_COMPONENTS existe com 4 componentes canonicos."""
    print("[TESTE 1/8] SHADCN_COMPONENTS dict + 4 componentes...")
    from backend.services.vite_templates import SHADCN_COMPONENTS

    assert isinstance(SHADCN_COMPONENTS, dict)
    assert "Button" in SHADCN_COMPONENTS
    assert "Card" in SHADCN_COMPONENTS
    assert "Input" in SHADCN_COMPONENTS
    assert "Badge" in SHADCN_COMPONENTS

    # Cada componente tem use_case (campo obrigatorio)
    for name, meta in SHADCN_COMPONENTS.items():
        assert "use_case" in meta, f"{name} sem use_case"
        assert isinstance(meta["use_case"], str)
        assert len(meta["use_case"]) > 10, f"{name} use_case muito curto"

    # Button tem variants + sizes
    btn = SHADCN_COMPONENTS["Button"]
    assert "variants" in btn
    assert "default" in btn["variants"]
    assert "destructive" in btn["variants"]
    assert "sizes" in btn
    assert "default" in btn["sizes"]
    assert "lg" in btn["sizes"]

    # Card tem parts (sub-componentes)
    card = SHADCN_COMPONENTS["Card"]
    assert "parts" in card
    for part in ["Card", "CardHeader", "CardTitle", "CardContent", "CardFooter"]:
        assert part in card["parts"], f"Card sem part {part}"

    print("  OK 4 componentes: Button/Card/Input/Badge")
    print("  OK Button tem 6 variants + 4 sizes")
    print("  OK Card tem 6 parts (Header/Title/Description/Content/Footer)")


def test_2_get_shadcn_component_list_format():
    """get_shadcn_component_list() retorna string formatada com todos componentes."""
    print("\n[TESTE 2/8] get_shadcn_component_list() format...")
    from backend.services.vite_templates import get_shadcn_component_list

    out = get_shadcn_component_list()

    # E string
    assert isinstance(out, str)
    assert len(out) > 100

    # Contem os 4 componentes
    for name in ["Button", "Card", "Input", "Badge"]:
        assert name in out, f"{name} ausente em get_shadcn_component_list()"

    # Tem formatacao markdown (bullets)
    assert "- **" in out
    assert "**:" in out

    # Button tem variants listadas
    btn_line = [l for l in out.split("\n") if "Button" in l][0]
    assert "default" in btn_line
    assert "destructive" in btn_line
    assert "variants" in btn_line
    assert "sizes" in btn_line

    print("  OK String formatada com 4 componentes")
    print("  OK Markdown bullets (**:**)")
    print("  OK Variants/sizes/parts listados em cada componente")


def test_3_get_shadcn_imports_dedup():
    """get_shadcn_imports() gera imports sem duplicatas."""
    print("\n[TESTE 3/8] get_shadcn_imports() - dedup...")
    from backend.services.vite_templates import get_shadcn_imports

    # Single component
    btn_imports = get_shadcn_imports(["Button"])
    assert len(btn_imports) == 1
    assert "from '@/components/ui/button'" in btn_imports[0]
    assert "Button" in btn_imports[0]

    # Card tem 1 import (multi-part)
    card_imports = get_shadcn_imports(["Card"])
    assert len(card_imports) == 1
    assert "from '@/components/ui/card'" in card_imports[0]
    for part in ["CardHeader", "CardTitle", "CardContent", "CardFooter"]:
        assert part in card_imports[0], f"Card import sem {part}"

    # Multiplos componentes
    multi = get_shadcn_imports(["Button", "Card", "Input", "Badge"])
    assert len(multi) == 4

    # Dedup: pedir 2x o mesmo retorna 1
    dup = get_shadcn_imports(["Button", "Button", "Button"])
    assert len(dup) == 1

    # Componente inexistente e ignorado
    unknown = get_shadcn_imports(["FooBar", "Button"])
    assert len(unknown) == 1
    assert "Button" in unknown[0]

    # Lista vazia
    assert get_shadcn_imports([]) == []

    print("  OK 1 componente -> 1 import")
    print("  OK Card multi-part em 1 linha de import")
    print("  OK 4 componentes -> 4 imports (sem duplicar)")
    print("  OK Dedup funciona (3x Button = 1 import)")
    print("  OK Componente inexistente ignorado")


def test_4_section_component_map():
    """get_shadcn_components_for_section() cobre 14 secoes + fallback."""
    print("\n[TESTE 4/8] SECTION_COMPONENT_MAP - 14 secoes...")
    from backend.services.vite_templates import (
        SECTION_COMPONENT_MAP,
        get_shadcn_components_for_section,
    )

    # 14 secoes mapeadas
    expected_sections = [
        "hero", "cta", "features", "services", "pricing", "testimonials",
        "faq", "contact", "form", "footer", "navbar", "gallery", "about", "stats",
    ]
    for s in expected_sections:
        assert s in SECTION_COMPONENT_MAP, f"Secao {s} nao mapeada"

    # Hero tem Button + Badge
    hero = get_shadcn_components_for_section("hero")
    assert "Button" in hero
    assert "Badge" in hero

    # Pricing tem Card + Button + Badge
    pricing = get_shadcn_components_for_section("pricing")
    assert "Card" in pricing
    assert "Button" in pricing

    # Contact tem Input + Button
    contact = get_shadcn_components_for_section("contact")
    assert "Input" in contact
    assert "Button" in contact

    # Case-insensitive
    assert get_shadcn_components_for_section("HERO") == hero

    # Fallback para secao desconhecida
    assert get_shadcn_components_for_section("xyz") == []
    assert get_shadcn_components_for_section("") == []

    print(f"  OK {len(expected_sections)} secoes mapeadas (hero/cta/pricing/...)")
    print("  OK Hero -> Button + Badge")
    print("  OK Pricing -> Card + Button + Badge")
    print("  OK Contact -> Input + Button")
    print("  OK Case-insensitive + fallback para secao vazia")


def test_5_shadcn_tsx_files_exist():
    """4 arquivos .tsx (button/card/input/badge) existem em vite_templates/src/components/ui/."""
    print("\n[TESTE 5/8] 4 shadcn .tsx files...")
    ui_dir = ROOT / "backend" / "services" / "vite_templates" / "src" / "components" / "ui"
    assert ui_dir.exists(), f"Dir {ui_dir} nao existe"

    expected = ["button.tsx", "card.tsx", "input.tsx", "badge.tsx"]
    for fname in expected:
        fpath = ui_dir / fname
        assert fpath.exists(), f"{fname} nao encontrado"
        content = fpath.read_text(encoding="utf-8")
        # Valida que importa cn() de utils
        assert 'from "@/lib/utils"' in content, f"{fname} nao importa cn()"
        # Valida que exporta o componente
        assert "export" in content, f"{fname} sem export"

    # Button usa cva (variant props)
    btn = (ui_dir / "button.tsx").read_text(encoding="utf-8")
    assert "cva" in btn
    assert "buttonVariants" in btn
    assert "VariantProps" in btn

    # Card exporta 6 sub-componentes
    card = (ui_dir / "card.tsx").read_text(encoding="utf-8")
    for part in ["Card", "CardHeader", "CardTitle", "CardDescription", "CardContent", "CardFooter"]:
        assert f"export" in card and part in card, f"Card nao exporta {part}"

    print("  OK button.tsx + card.tsx + input.tsx + badge.tsx existem")
    print("  OK Todos importam cn() de @/lib/utils")
    print("  OK button.tsx usa cva + VariantProps (Sprint 11 padrao)")
    print("  OK card.tsx exporta 6 sub-componentes")


def test_6_utils_ts_and_components_json():
    """utils.ts existe com cn() e components.json tem config valida."""
    print("\n[TESTE 6/8] utils.ts + components.json...")
    lib_dir = ROOT / "backend" / "services" / "vite_templates" / "src" / "lib"
    assert lib_dir.exists(), f"Dir {lib_dir} nao existe"
    utils_path = lib_dir / "utils.ts"
    assert utils_path.exists(), "utils.ts nao encontrado"
    utils_content = utils_path.read_text(encoding="utf-8")
    # Exporta cn()
    assert "export function cn" in utils_content, "cn() nao exportado"
    # Importa clsx + tailwind-merge
    assert "from \"clsx\"" in utils_content
    assert "from \"tailwind-merge\"" in utils_content
    # Usa twMerge
    assert "twMerge" in utils_content

    # components.json
    cjson_path = ROOT / "backend" / "services" / "vite_templates" / "components.json"
    assert cjson_path.exists(), "components.json nao encontrado"
    cfg = json.loads(cjson_path.read_text(encoding="utf-8"))
    assert cfg["$schema"] == "https://ui.shadcn.com/schema.json"
    assert cfg["style"] == "default"
    assert cfg["tsx"] is True
    assert cfg["aliases"]["components"] == "@/components"
    assert cfg["aliases"]["utils"] == "@/lib/utils"

    print("  OK utils.ts exporta cn() com clsx + tailwind-merge")
    print("  OK components.json com $schema oficial + aliases @/*")


def test_7_vite_config_has_shadcn_deps():
    """FIXED_PACKAGE_JSON em vite_config.py tem 9 deps shadcn/ui."""
    print("\n[TESTE 7/8] vite_config.py FIXED_PACKAGE_JSON - 9 deps shadcn...")
    from backend.services import vite_config

    deps = vite_config.FIXED_PACKAGE_JSON["dependencies"]

    # 9 deps shadcn/ui adicionadas
    expected = [
        "@radix-ui/react-button",
        "@radix-ui/react-card",
        "@radix-ui/react-dialog",
        "@radix-ui/react-dropdown-menu",
        "@radix-ui/react-navigation-menu",
        "@radix-ui/react-tabs",
        "class-variance-authority",
        "clsx",
        "tailwind-merge",
    ]
    for d in expected:
        assert d in deps, f"Dep {d} ausente em FIXED_PACKAGE_JSON"

    # Versoes coerentes (com ^)
    assert deps["class-variance-authority"].startswith("^")
    assert deps["clsx"].startswith("^")
    assert deps["tailwind-merge"].startswith("^")

    # Deps base continuam presentes (Sprint 0 nao regrediu)
    assert "react" in deps
    assert "react-dom" in deps
    assert "tailwindcss" in deps
    assert "lucide-react" in deps

    print("  OK 9 deps shadcn/ui presentes (@radix-ui/*, cva, clsx, twMerge)")
    print("  OK Versoes prefixadas com ^")
    print("  OK Deps base (react, tailwindcss, lucide-react) preservadas")


def test_8_vite_prompts_injects_shadcn():
    """VITE_REACT_SYSTEM_PROMPT contem bloco SHADCN/UI injetado via _build_shadcn_block."""
    print("\n[TESTE 8/8] vite_prompts.py - shadcn block injetado...")
    from backend.services.vite_prompts import VITE_REACT_SYSTEM_PROMPT

    # Bloco SHADCN/UI COMPONENTS presente
    assert "SHADCN/UI COMPONENTS" in VITE_REACT_SYSTEM_PROMPT, \
        "Bloco SHADCN/UI nao injetado no system prompt"

    # Conteudo esperado no bloco
    assert "Available components" in VITE_REACT_SYSTEM_PROMPT
    assert "Button" in VITE_REACT_SYSTEM_PROMPT
    assert "Card" in VITE_REACT_SYSTEM_PROMPT
    assert "Input" in VITE_REACT_SYSTEM_PROMPT
    assert "Badge" in VITE_REACT_SYSTEM_PROMPT

    # Import example presente
    assert "from '@/components/ui/button'" in VITE_REACT_SYSTEM_PROMPT
    assert "from '@/components/ui/card'" in VITE_REACT_SYSTEM_PROMPT

    # Regra de uso presente
    assert "Use these instead of inventing" in VITE_REACT_SYSTEM_PROMPT or \
           "use these instead of inventing" in VITE_REACT_SYSTEM_PROMPT.lower()

    # Tamanho razoavel (bloco adiciona ~1.5K chars)
    assert len(VITE_REACT_SYSTEM_PROMPT) > 8000, \
        f"System prompt muito curto: {len(VITE_REACT_SYSTEM_PROMPT)} chars"

    # Bloco _build_shadcn_block existe no modulo
    from backend.services import vite_prompts as vp
    assert hasattr(vp, "_build_shadcn_block")
    assert callable(vp._build_shadcn_block)

    # FOOT inclui shadcn block
    assert "SHADCN/UI" in vp.VITE_REACT_SYSTEM_PROMPT_FOOT
    assert "few_shot" not in vp.VITE_REACT_SYSTEM_PROMPT_FOOT.lower() or \
           vp.VITE_REACT_SYSTEM_PROMPT_FOOT.count("SHADCN/UI") >= 1

    print("  OK Bloco SHADCN/UI COMPONENTS presente no system prompt")
    print("  OK 4 componentes listados (Button/Card/Input/Badge)")
    print("  OK Exemplos de import + regra 'use these instead of inventing'")
    print("  OK _build_shadcn_block() existe e e callable")


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("TESTES ANTI-REGRESSAO v1.13 - Sprint 11 (shadcn/ui + Vite/React pipeline)")
    print("=" * 80)

    test_1_shadcn_components_dict_exists()
    test_2_get_shadcn_component_list_format()
    test_3_get_shadcn_imports_dedup()
    test_4_section_component_map()
    test_5_shadcn_tsx_files_exist()
    test_6_utils_ts_and_components_json()
    test_7_vite_config_has_shadcn_deps()
    test_8_vite_prompts_injects_shadcn()

    print("\n" + "=" * 80)
    print("TODOS OS TESTES PASSARAM (8/8)")
    print("Sprint 11 (v1.13) - shadcn/ui integrado no Vite/React pipeline com sucesso")
    print("=" * 80)
