"""
ROLL 9 — Surgical patches for vite_react_renderer.py + vite_templates.py.
Idempotent: each patch checks for an existing marker comment before editing.
"""
from pathlib import Path

PROJECT_ROOT = Path(r"C:\fralib")
RENDERER = PROJECT_ROOT / "backend" / "services" / "vite_react_renderer.py"
TEMPLATES = PROJECT_ROOT / "backend" / "services" / "vite_templates.py"


# ════════════════════════════════════════════════════════════════════════════
# PATCH 9.1a — Strip hardcoded Google Fonts import from _default_index_css
# ════════════════════════════════════════════════════════════════════════════

HARDCODED_FONTS_IMPORT = (
    '@import url(\'https://fonts.googleapis.com/css2?'
    'family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700;800&display=swap\');'
)
CSS_NO_HARDCODED = "@import url('https://fonts.googleapis.com/css2?display=swap');"

# Marker to find the body font-family override that hardcodes Inter.
HARDCODED_BODY_FONT = "font-family: Inter, system-ui, sans-serif;"
CSS_BODY_FONT_DEFAULT = "font-family: var(--pole-body-font, system-ui, sans-serif);"


def patch_9_1a_strip_hardcoded_fonts() -> bool:
    src = RENDERER.read_text(encoding="utf-8")
    marker = "/* ROLL 9: hardcoded fonts stripped */"
    if marker in src:
        print("[9.1a] already applied — skipping")
        return False
    if HARDCODED_FONTS_IMPORT not in src:
        print("[9.1a] hardcoded import not found — already stripped? skipping")
        return False
    new_src = src.replace(
        HARDCODED_FONTS_IMPORT,
        f'{CSS_NO_HARDCODED} {marker}',
        1,
    )
    new_src = new_src.replace(
        HARDCODED_BODY_FONT,
        CSS_BODY_FONT_DEFAULT,
        1,
    )
    RENDERER.write_text(new_src, encoding="utf-8")
    print("[9.1a] stripped hardcoded Cormorant+Inter import + body font override")
    return True


# ════════════════════════════════════════════════════════════════════════════
# PATCH 9.1b — Add _strip_inline_font_family_in_css + wire into prepare_vite_project_files
# ════════════════════════════════════════════════════════════════════════════

NEW_HELPERS_91B = '''
# ═══════════════════════════════════════════════════════════════════════════
# ROLL 9.1b — Strip inline font-family from LLM-generated CSS
# ═══════════════════════════════════════════════════════════════════════════

# Fontes canonicas (mesmas que _GOOGLE_FONT_FAMILIES em vite_templates.py).
# Usado para detectar e remover font-family hardcoded em CSS/TSX gerado pela LLM.
_ROLL9_KNOWN_FONTS = (
    "Bebas Neue", "Oswald", "Anton", "Roboto Condensed", "Roboto",
    "Inter", "Manrope", "DM Sans", "Playfair Display", "Libre Baskerville",
    "Source Serif 4", "Lora", "Merriweather", "Crimson Pro", "Nunito",
    "Cormorant Garamond", "Space Grotesk", "Archivo", "IBM Plex Sans",
    "IBM Plex Serif", "Source Sans 3", "Pacifico", "Cairo",
    "Poppins", "Lato", "Montserrat", "Open Sans", "Raleway",
    "Work Sans", "Karla", "Rubik",
)

_ROLL9_FONT_FAMILY_RE = re.compile(
    r"font-family\\s*:\\s*[\"']?(?:[^\"';}]+)[\"']?\\s*(?:!important)?\\s*;",
    re.IGNORECASE,
)


def _strip_inline_font_family_in_css(css: str) -> str:
    """ROLL 9.1b: remove font-family inline declarations que a LLM insiste
    em inserir no CSS gerado (sobrescreve --pole-heading-font / --pole-body-font).

    Substitui por uma declaracao no-op (font-family: inherit;) que delega ao
    :root { --pole-heading-font / --pole-body-font } definido por
    _ensure_font_vars_in_css.

    Idempotente.
    """
    if "font-family" not in css:
        return css
    seen = 0

    def _replace(m: re.Match[str]) -> str:
        nonlocal seen
        seen += 1
        return "font-family: inherit; /* ROLL 9: enforced via --pole-* vars */"

    new_css = _ROLL9_FONT_FAMILY_RE.sub(_replace, css)
    if seen:
        # Log discreto em comentario para auditoria.
        new_css = (
            "/* ROLL 9.1b: "
            f"stripped {seen} inline font-family declarations */\\n"
            + new_css
        )
    return new_css


def _strip_inline_font_family_in_tsx(tsx: str) -> str:
    """ROLL 9.1b: mesma limpeza aplicada em TSX/JSX (style={{ fontFamily: ... }}).
    Idempotente.
    """
    if "fontFamily" not in tsx and "font-family" not in tsx:
        return tsx
    # React style object: fontFamily: 'Inter, sans-serif'
    pat_obj = re.compile(
        r"fontFamily\\s*:\\s*[\"'](?:[^\"']+)[\"']\\s*,?",
        re.IGNORECASE,
    )
    # CSS string em template literal: style={`font-family: Inter, sans-serif`}
    pat_str = re.compile(
        r"font-family\\s*:\\s*[\"']?(?:[^\"';}]+)[\"']?",
        re.IGNORECASE,
    )
    seen = 0

    def _obj(m: re.Match[str]) -> str:
        nonlocal seen
        seen += 1
        return "/* ROLL 9: fontFamily stripped */"

    def _str(m: re.Match[str]) -> str:
        nonlocal seen
        seen += 1
        return "font-family: inherit"

    new_tsx = pat_obj.sub(_obj, tsx)
    new_tsx = pat_str.sub(_str, new_tsx)
    if seen:
        new_tsx = (
            "/* ROLL 9.1b: "
            f"stripped {seen} inline font-family references */\\n"
            + new_tsx
        )
    return new_tsx

'''


def patch_9_1b_strip_inline_fonts() -> bool:
    src = RENDERER.read_text(encoding="utf-8")
    marker = "def _strip_inline_font_family_in_css("
    if marker in src:
        print("[9.1b] already applied — skipping")
        return False
    # Insert before prepare_vite_project_files (line ~2916).
    target = "def prepare_vite_project_files("
    idx = src.find(target)
    if idx < 0:
        raise RuntimeError("prepare_vite_project_files anchor not found")
    new_src = src[:idx] + NEW_HELPERS_91B + src[idx:]
    # Wire into prepare_vite_project_files: after _ensure_font_vars_in_css call.
    anchor = (
        "    prepared[\"src/index.css\"] = _ensure_font_vars_in_css(\n"
        "            prepared[\"src/index.css\"], heading=_hf, body=_bf,\n"
        "            lead_id=facts.get(\"lead_id\") or facts.get(\"id\"),\n"
        "        )\n"
        "    _normalize_generated_imports_and_hooks(prepared)"
    )
    new_block = (
        "    prepared[\"src/index.css\"] = _ensure_font_vars_in_css(\n"
        "            prepared[\"src/index.css\"], heading=_hf, body=_bf,\n"
        "            lead_id=facts.get(\"lead_id\") or facts.get(\"id\"),\n"
        "        )\n"
        "    # ROLL 9.1b: strip any inline font-family the LLM injected (CSS + TSX)\n"
        "    prepared[\"src/index.css\"] = _strip_inline_font_family_in_css(\n"
        "        prepared[\"src/index.css\"]\n"
        "    )\n"
        "    for _tsx_path in list(prepared.keys()):\n"
        "        if _tsx_path.endswith((\".tsx\", \".ts\", \".jsx\", \".js\")):\n"
        "            prepared[_tsx_path] = _strip_inline_font_family_in_tsx(\n"
        "                prepared[_tsx_path]\n"
        "            )\n"
        "    _normalize_generated_imports_and_hooks(prepared)"
    )
    if anchor not in new_src:
        raise RuntimeError("CSS vars injection anchor not found")
    new_src = new_src.replace(anchor, new_block, 1)
    RENDERER.write_text(new_src, encoding="utf-8")
    print("[9.1b] added _strip_inline_font_family_in_css/tsx + wired into prepare")
    return True


# ════════════════════════════════════════════════════════════════════════════
# PATCH 9.2 — Filter sections by nicho + wire ordem_das_secoes into variation
# ════════════════════════════════════════════════════════════════════════════

NEW_HELPERS_92 = '''
# ═══════════════════════════════════════════════════════════════════════════
# ROLL 9.2 — Section filtering by nicho + wire ordem_das_secoes → section_order
# ═══════════════════════════════════════════════════════════════════════════

# Secoes que NAO fazem sentido em determinados nichos.
# Patch Purge origem: arquitetos/comercial/energia solar nao tem "pricing"
# de servicos (orcamento sob consulta); o bloco de planos polui o hero.
_ROLL9_EXCLUDED_SECTIONS_BY_NICHO: dict[str, tuple[str, ...]] = {
    "arquiteto_residencial": ("pricing",),
    "arquiteto_comercial": ("pricing",),
    "construtora_residencial": ("pricing",),
    "construtora_comercial": ("pricing",),
    "energia_solar": ("pricing",),
    "escritorio_contabil": ("pricing",),
    "advocacia_trabalhista": ("pricing",),
    "nutricionista_esportiva": ("pricing", "gallery"),
    "barbearia_premium": ("pricing",),
    "academia_crossfit": ("pricing",),
    "academia_musculacao": ("pricing",),
    "imobiliaria_residencial": ("pricing",),
    "restaurante_familiar": ("pricing",),
    "clinica_estetica": ("pricing",),
    "clinica_odontologica": ("pricing",),
}


def _roll9_excluded_sections_for(nicho: str | None, subnicho: str | None) -> tuple[str, ...]:
    """Retorna tupla de secoes a EXCLUIR para (nicho, subnicho).
    Ordem de precedencia: subnicho > nicho.
    """
    excluded: list[str] = []
    if subnicho:
        excluded.extend(_ROLL9_EXCLUDED_SECTIONS_BY_NICHO.get(subnicho.lower(), ()))
    if nicho:
        excluded.extend(_ROLL9_EXCLUDED_SECTIONS_BY_NICHO.get(nicho.lower(), ()))
    return tuple(dict.fromkeys(excluded))  # dedupe preservando ordem


def _roll9_apply_section_exclusions(
    order: list[str],
    nicho: str | None,
    subnicho: str | None,
) -> list[str]:
    """Filtra secoes NAO relevantes para o (nicho, subnicho)."""
    excluded = _roll9_excluded_sections_for(nicho, subnicho)
    if not excluded:
        return order
    return [s for s in order if s not in set(excluded)]


def _roll9_normalize_ptbr_sections(order: list[str]) -> list[str]:
    """Converte chaves PT-BR (ordem_das_secoes do agente_variacao) para EN
    canonico usado pelo renderer.
    """
    aliases = {
        "sobre": "about",
        "servicos": "services",
        "galeria": "gallery",
        "faq": "faq",
        "depoimentos": "reviews",
        "testimonials": "reviews",
        "avaliacoes": "reviews",
        "localizacao": "location",
        "experiencia": "lifestyle",
        "contato": "contact-cta",
        "cta": "contact-cta",
        "cta-final": "contact-cta",
        "numeros": "stats-bar",
        "processo": "about",
        "areas-atuacao": "services",
        "modalidades": "services",
        "cardapio": "services",
        "equipe": "about",
        "planos": "pricing",
    }
    return [aliases.get(str(s).strip().lower(), str(s).strip().lower()) for s in order]


def _roll9_merge_section_orders(
    variation: dict[str, Any],
    facts: dict[str, Any],
) -> dict[str, Any]:
    """ROLL 9.2: mescla section_order de 3 fontes (ordem de prioridade):
      1. facts.information_architecture.section_order (ja canonico EN, vindo
         do site_build_plan._resolve_section_order)
      2. facts.variacao.ordem_das_secoes (PT-BR, vindo do agente_variacao)
         — convertido para EN e mesclado se nao duplicar
      3. variation.section_order (ja canonico, vindo do pipeline_builders)

    Sempre injeta 'pricing' apenas se o nicho/subnicho permitir.
    """
    if not isinstance(variation, dict):
        return variation
    out = dict(variation)

    candidates: list[str] = []
    # 1) information_architecture.section_order (canonical EN)
    info_arch = (
        facts.get("information_architecture")
        if isinstance(facts.get("information_architecture"), dict)
        else {}
    )
    if isinstance(info_arch.get("section_order"), list):
        candidates.extend(str(s) for s in info_arch["section_order"])
    # 2) variacao.ordem_das_secoes (PT-BR)
    variacao_src = (
        facts.get("variacao")
        if isinstance(facts.get("variacao"), dict)
        else facts.get("variacao_estrutural")
        if isinstance(facts.get("variacao_estrutural"), dict)
        else {}
    )
    if isinstance(variacao_src.get("ordem_das_secoes"), list):
        candidates.extend(_roll9_normalize_ptbr_sections(variacao_src["ordem_das_secoes"]))
    # 3) variation.section_order (canonical EN)
    if isinstance(variation.get("section_order"), list):
        candidates.extend(str(s) for s in variation["section_order"])

    if not candidates:
        return out

    # Preserva ordem, deduplica, e adiciona must-have (navbar/hero/footer).
    seen: set[str] = set()
    merged: list[str] = []
    for s in candidates:
        s = s.strip().lower()
        if not s or s in seen:
            continue
        seen.add(s)
        merged.append(s)

    # Garante navbar primeiro, hero depois, footer por ultimo.
    for must in ("navbar",):
        if must not in merged:
            merged.insert(0, must)
    for must in ("hero",):
        if must not in merged:
            merged.insert(1 if "navbar" in merged else 0, must)
    if "footer" not in merged:
        merged.append("footer")

    # Aplica filtro por nicho/subnicho.
    biz = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    nicho = str(
        biz.get("segment")
        or biz.get("segmento")
        or facts.get("segmento")
        or facts.get("segment")
        or ""
    ).strip().lower() or None
    subnicho = str(
        biz.get("subnicho")
        or biz.get("subniche")
        or facts.get("subnicho")
        or facts.get("subniche")
        or ""
    ).strip().lower() or None
    merged = _roll9_apply_section_exclusions(merged, nicho, subnicho)

    out["section_order"] = merged
    return out

'''


def patch_9_2_section_filter() -> bool:
    src = RENDERER.read_text(encoding="utf-8")
    marker = "def _roll9_excluded_sections_for("
    if marker in src:
        print("[9.2] already applied — skipping")
        return False

    # Insert helpers before _resolve_cinematic_section_order (line ~4318).
    target = "def _resolve_cinematic_section_order("
    idx = src.find(target)
    if idx < 0:
        raise RuntimeError("_resolve_cinematic_section_order anchor not found")
    new_src = src[:idx] + NEW_HELPERS_92 + src[idx:]

    # Wire merge into the call site at line ~6266.
    anchor = (
        "    _variation_payload = dict(\n"
        "        facts.get(\"variation\") if isinstance(facts.get(\"variation\"), dict) else {}\n"
        "    )\n"
        "    _hero_classes_override = str(_variation_payload.get(\"hero_classes\") or \"\").strip()"
    )
    new_block = (
        "    _variation_payload = dict(\n"
        "        facts.get(\"variation\") if isinstance(facts.get(\"variation\"), dict) else {}\n"
        "    )\n"
        "    # ROLL 9.2: mescla information_architecture.section_order +\n"
        "    # variacao.ordem_das_secoes (PT-BR→EN) em variation.section_order.\n"
        "    _variation_payload = _roll9_merge_section_orders(_variation_payload, facts)\n"
        "    _hero_classes_override = str(_variation_payload.get(\"hero_classes\") or \"\").strip()"
    )
    if anchor not in new_src:
        raise RuntimeError("variation payload anchor not found")
    new_src = new_src.replace(anchor, new_block, 1)
    RENDERER.write_text(new_src, encoding="utf-8")
    print("[9.2] added section filter + ordem_das_secoes wire into variation")
    return True


# ════════════════════════════════════════════════════════════════════════════
# PATCH 9.3 — bg-noise + glowing-orb utilities + 3D prompt instructions
# ════════════════════════════════════════════════════════════════════════════

NEW_HELPERS_93 = '''
# ═══════════════════════════════════════════════════════════════════════════
# ROLL 9.3 — Texture & depth utilities (bg-noise, glowing-orb, 3D scroll)
# ═══════════════════════════════════════════════════════════════════════════

ROLL9_TEXTURE_CSS = """/* ROLL 9.3 — texture & depth utilities (CSS-only, no bundle bloat) */

/* Noise sutil de fundo para polo BOLD (academia/oficina/energia) */
@keyframes fralib-noise-shift {
  0%, 100% { transform: translate(0, 0); }
  10% { transform: translate(-2%, -1%); }
  30% { transform: translate(1%, -2%); }
  50% { transform: translate(-1%, 1%); }
  70% { transform: translate(2%, 1%); }
  90% { transform: translate(-2%, 2%); }
}
.bg-noise {
  position: relative;
  isolation: isolate;
}
.bg-noise::before {
  content: "";
  position: absolute;
  inset: -10%;
  z-index: -1;
  pointer-events: none;
  opacity: 0.06;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1   0 0 0 0 1   0 0 0 0 1   0 0 0 0.55 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  background-size: 160px 160px;
  animation: fralib-noise-shift 7s steps(6) infinite;
  mix-blend-mode: overlay;
}

/* Orbs suaves de gradiente para polo TECH (energia_solar, imobiliaria) */
@keyframes fralib-orb-drift-a {
  0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
  50% { transform: translate3d(8%, -6%, 0) scale(1.12); }
}
@keyframes fralib-orb-drift-b {
  0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
  50% { transform: translate3d(-10%, 4%, 0) scale(0.92); }
}
.glowing-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(64px);
  pointer-events: none;
  will-change: transform;
  z-index: 0;
}
.glowing-orb--a {
  width: 36vmax;
  height: 36vmax;
  background: radial-gradient(circle, var(--orb-a, rgba(56, 189, 248, 0.45)), transparent 65%);
  animation: fralib-orb-drift-a 14s ease-in-out infinite;
}
.glowing-orb--b {
  width: 28vmax;
  height: 28vmax;
  background: radial-gradient(circle, var(--orb-b, rgba(168, 85, 247, 0.35)), transparent 70%);
  animation: fralib-orb-drift-b 18s ease-in-out infinite;
}

/* 3D parallax helper (CSS-only, scroll-driven em browsers modernos) */
.parallax-3d {
  transform-style: preserve-3d;
  perspective: 1200px;
  will-change: transform;
}

/* Section "depth" wrapper para aplicacao em scroll */
.depth-card {
  transform: translate3d(0, 0, 0);
  transition: transform 600ms cubic-bezier(0.22, 1, 0.36, 1);
}
.depth-card:hover {
  transform: translate3d(0, -4px, 8px);
}

@media (prefers-reduced-motion: reduce) {
  .bg-noise::before, .glowing-orb { animation: none !important; }
  .depth-card { transition: none !important; }
}
"""


def _ensure_roll9_texture_utilities(css: str) -> str:
    """Idempotente: injeta o bloco de utilidades 9.3 apenas uma vez."""
    if "ROLL 9.3 — texture & depth utilities" in css:
        return css
    return css.rstrip() + "\\n\\n" + ROLL9_TEXTURE_CSS

'''


ROLL9_PROMPT_INSTRUCTIONS = """
=== ROLL 9.3 — TEXTURE & DEPTH (polo-aware) ===
POLO {_polo}:
- BOLD_ENERGY: adicione a classe `bg-noise` em pelo menos um bloco (hero ou
  secao de prova social). Ela renderiza uma textura sutil de ruido analogico
  via SVG inline — sem dependencias externas.
- MODERN_TECH: adicione 2 elementos `glowing-orb` (a + b) posicionados
  absolutos dentro de um wrapper `relative overflow-hidden` no hero. Use
  --orb-a e --orb-b para customizar a cor (ex: cyan + violet).
- PROFESSIONAL_TRUST / WARM_LOCAL: adicione `parallax-3d` em cards do about
  e `depth-card` em cards de servicos para micro-elevacao no hover.
- Qualquer polo: ao usar imagens, envolva em `parallax-3d` para permitir
  profundidade de scroll futura. NAO adicione GSAP manualmente — o sistema
  ja tem motion chunks separados no vite.config.

REGRA DURA: nunca use `font-family` inline em JSX style={{}}. Use
exclusivamente as classes `font-heading` / `font-body` ou vars CSS
--pole-heading-font / --pole-body-font. O renderer ja strippa inline
font-family automaticamente.
=== END ROLL 9.3 ===
"""


def patch_9_3_texture_utilities() -> bool:
    src = RENDERER.read_text(encoding="utf-8")
    marker = "def _ensure_roll9_texture_utilities("
    if marker in src:
        print("[9.3] already applied — skipping")
        return False

    # 1) Add helper before _default_index_css (~line 10581).
    target = "def _default_index_css() -> str:"
    idx = src.find(target)
    if idx < 0:
        raise RuntimeError("_default_index_css anchor not found")
    new_src = src[:idx] + NEW_HELPERS_93 + src[idx:]

    # 2) Wire injection into _default_index_css body (right before the
    # closing triple-quote).
    anchor_default = (
        "@media (prefers-reduced-motion: reduce) {\n"
        "  *, *::before, *::after {\n"
        "    animation-duration: 0.01ms !important;\n"
        "    animation-iteration-count: 1 !important;\n"
        "    scroll-behavior: auto !important;\n"
        "    transition-duration: 0.01ms !important;\n"
        "  }\n"
        "}\n"
        "\"\"\"\n"
        "\n"
        "\n"
        "def _ensure_index_css_contract"
    )
    new_default = (
        "@media (prefers-reduced-motion: reduce) {\n"
        "  *, *::before, *::after {\n"
        "    animation-duration: 0.01ms !important;\n"
        "    animation-iteration-count: 1 !important;\n"
        "    scroll-behavior: auto !important;\n"
        "    transition-duration: 0.01ms !important;\n"
        "  }\n"
        "}\n"
        "\"\"\"\n"
        "    css = _ensure_roll9_texture_utilities(css)\n"
        "    return css\n"
        "\n"
        "\n"
        "def _ensure_index_css_contract"
    )
    if anchor_default not in new_src:
        raise RuntimeError("_default_index_css body anchor not found")
    new_src = new_src.replace(anchor_default, new_default, 1)

    # 3) Inject prompt instructions right after _design_system_spec_ref block.
    prompt_anchor = (
        "=== END DESIGN SYSTEM SPEC ===\n"
        "\"\"\"\n"
    )
    prompt_block = (
        "=== END DESIGN SYSTEM SPEC ===\n"
        + ROLL9_PROMPT_INSTRUCTIONS.replace("{_polo}", "{_polo}")
        + "\"\"\"\n"
    )
    if prompt_anchor not in new_src:
        raise RuntimeError("design_system_spec_ref prompt anchor not found")
    new_src = new_src.replace(prompt_anchor, prompt_block, 1)

    # 4) Replace {design_contract_ref}{...} to include the new block.
    insertion_point = "{skill_pack_ref}{design_contract_ref}{design_reference_ref}{design_system_ref}{_design_system_spec_ref}{variacao_ref}"
    insertion_with_roll9 = "{skill_pack_ref}{design_contract_ref}{design_reference_ref}{design_system_ref}{_design_system_spec_ref}{_roll9_3_ref}{variacao_ref}"
    if insertion_point not in new_src:
        raise RuntimeError("prompt composition anchor not found")
    new_src = new_src.replace(insertion_point, insertion_with_roll9, 1)

    # 5) Build _roll9_3_ref string near the existing variacao_ref block.
    var_anchor = (
        "    # Injetar variação estrutural do Agente Variação\n"
        "    variacao_ref = \"\""
    )
    var_block = (
        "    # ROLL 9.3: bloco de instruções de textura/profundidade por polo\n"
        "    try:\n"
        "        _roll9_polo_name = str(_polo or \"CLASSIC\")\n"
        "    except Exception:\n"
        "        _roll9_polo_name = \"CLASSIC\"\n"
        "    _roll9_3_ref = f\"\"\"\n"
        "=== ROLL 9.3 — TEXTURE & DEPTH (polo-aware) ===\n"
        "POLO {_roll9_polo_name}:\n"
        "- BOLD_ENERGY: adicione a classe `bg-noise` em pelo menos um bloco (hero ou\n"
        "  secao de prova social). Ela renderiza uma textura sutil de ruido analogico\n"
        "  via SVG inline — sem dependencias externas.\n"
        "- MODERN_TECH: adicione 2 elementos `glowing-orb` (a + b) posicionados\n"
        "  absolutos dentro de um wrapper `relative overflow-hidden` no hero. Use\n"
        "  --orb-a e --orb-b para customizar a cor (ex: cyan + violet).\n"
        "- PROFESSIONAL_TRUST / WARM_LOCAL: adicione `parallax-3d` em cards do about\n"
        "  e `depth-card` em cards de servicos para micro-elevacao no hover.\n"
        "- Qualquer polo: ao usar imagens, envolva em `parallax-3d` para permitir\n"
        "  profundidade de scroll futura. NAO adicione GSAP manualmente — o sistema\n"
        "  ja tem motion chunks separados no vite.config.\n\n"
        "REGRA DURA: nunca use `font-family` inline em JSX style={{}}. Use\n"
        "exclusivamente as classes `font-heading` / `font-body` ou vars CSS\n"
        "--pole-heading-font / --pole-body-font. O renderer ja strippa inline\n"
        "font-family automaticamente.\n"
        "=== END ROLL 9.3 ===\n"
        "\"\"\"\n"
        "\n"
        "    # Injetar variação estrutural do Agente Variação\n"
        "    variacao_ref = \"\""
    )
    if var_anchor not in new_src:
        raise RuntimeError("variacao_ref anchor not found")
    new_src = new_src.replace(var_anchor, var_block, 1)

    RENDERER.write_text(new_src, encoding="utf-8")
    print("[9.3] added bg-noise + glowing-orb utilities + 3D prompt instructions")
    return True


# ════════════════════════════════════════════════════════════════════════════
# PATCH 9.4 — Update vite_templates._GOOGLE_FONT_FAMILIES (missing fonts)
# ════════════════════════════════════════════════════════════════════════════

NEW_FONT_ENTRIES = '''    "Cormorant Garamond": "Cormorant+Garamond:wght@500;600;700",
    "Space Grotesk": "Space+Grotesk:wght@500;600;700",
    "Archivo": "Archivo:wght@500;600;700",
    "IBM Plex Sans": "IBM+Plex+Sans:wght@400;500;600",
    "IBM Plex Serif": "IBM+Plex+Serif:wght@400;500;700",
    "Source Sans 3": "Source+Sans+3:wght@400;500;600",
    "Pacifico": "Pacifico",
    "Cairo": "Cairo:wght@500;700",
    "Poppins": "Poppins:wght@500;600;700",
    "Lato": "Lato:wght@400;700",
    "Montserrat": "Montserrat:wght@500;700",
    "Open Sans": "Open+Sans:wght@400;600;700",
    "Raleway": "Raleway:wght@500;600;700",
    "Work Sans": "Work+Sans:wght@500;600;700",
    "Karla": "Karla:wght@500;600;700",
    "Rubik": "Rubik:wght@500;600;700",
'''


def patch_9_4_expand_font_registry() -> bool:
    src = TEMPLATES.read_text(encoding="utf-8")
    marker = "/* ROLL 9.4: missing fonts added */"
    if marker in src:
        print("[9.4] already applied — skipping")
        return False
    # Insert before closing brace of _GOOGLE_FONT_FAMILIES dict.
    anchor = '    "Nunito": "Nunito:wght@400;600;700",\n}\n'
    if anchor not in src:
        raise RuntimeError("Nunito anchor not found in vite_templates.py")
    new_src = src.replace(
        anchor,
        '    "Nunito": "Nunito:wght@400;600;700",\n'
        + NEW_FONT_ENTRIES
        + '}\n\n' + marker + '\n',
        1,
    )
    TEMPLATES.write_text(new_src, encoding="utf-8")
    print("[9.4] expanded _GOOGLE_FONT_FAMILIES with 16 missing families")
    return True


# ════════════════════════════════════════════════════════════════════════════
# RUNNER
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== ROLL 9 — applying patches ===\n")
    patch_9_1a_strip_hardcoded_fonts()
    patch_9_1b_strip_inline_fonts()
    patch_9_2_section_filter()
    patch_9_3_texture_utilities()
    patch_9_4_expand_font_registry()
    print("\n=== Done ===")