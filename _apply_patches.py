"""Apply FRA-LIB footer-pin + palette-rotation patches to local clean checkout."""
import re, os, sys

BUILDER = r"C:\fralib\backend\agents\builder\agent.py"
DC = r"C:\fralib\design_context.py"


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def write(p, s):
    with open(p, 'w', encoding='utf-8') as f:
        f.write(s)
    print(f' wrote {len(s)} bytes -> {p}')


# ─── BUILDER ─────────────────────────────────────────────────────────────────
b = read(BUILDER)

# 1) Add import + pin function near top (after `import re`)
if "_pin_footer_last" not in b:
    b = b.replace(
        "import re",
        "import re\n"
        "\n"
        "def _pin_footer_last(html: str) -> str:\n"
        '    lower = html.lower()\n'
        '    if "</body>" not in lower:\n'
        "        return html\n"
        '    footer_match = re.search(\n'
        '        r"(?is)(?:<footer\\b[^>]*>|<section\\b[^>]*id=[\'\\\"]footer[\'\\\"][^>]*>)(.*?)(?:</footer>|</section>)",\n'
        "        html,\n"
        "    )\n"
        "    if not footer_match:\n"
        "        return html\n"
        "    footer_block = html[footer_match.start():footer_match.end()]\n"
        "    html_no_footer = html[:footer_match.start()] + html[footer_match.end():]\n"
        '    html_no_footer = re.sub(\n'
        '        r"(?is)(<section\\b[^>]*>.*?</section>)", "", html_no_footer,\n'
        "    )\n"
        '    html_pinned = re.sub(\n'
        '        r"(?is)(</body>)",\n'
        '        footer_block + "\\n" + r"\\1", html_no_footer, count=1,\n'
        "    )\n"
        "    return html_pinned\n",
        1,
    )
    print('builder: added _pin_footer_last')

# 2) Inject palette import into _prd_to_spec
if "_gdc" not in b:
    # add design_tokens init at start of function
    b = b.replace(
        "def _prd_to_spec(prd):",
        "def _prd_to_spec(prd):\n    design_tokens: dict = {}",
        1,
    )
    print('builder: added design_tokens init')
    insert_after = "def _prd_to_spec(prd):\n    design_tokens: dict = {}"
    palette_block = (
        "\n"
        "    try:\n"
        '        from agents.design_context import get_design_context as _gdc\n'
        "        _ctx = _gdc(_seg, _nome, getattr(prd, 'tier', 'STANDARD') or 'STANDARD', False)\n"
        "        _ctx_tokens = _ctx.get('tokens', {}) if isinstance(_ctx, dict) else {}\n"
        "        for _tk, _tv in _ctx_tokens.items():\n"
        "            _flat = _tk[2:] if _tk.startswith('--') else _tk\n"
        "            design_tokens[_flat] = _tv\n"
        "    except Exception:\n"
        "        pass\n"
    )
    b = b.replace(insert_after, insert_after + palette_block, 1)
    print('builder: injected palette import in _prd_to_spec')

# 3) Ensure design_tokens injected in final HTML (look for html = _inject_deterministic_assets)
if "design_tokens" not in b[b.find("_inject_deterministic_assets"):b.find("_inject_deterministic_assets") + 400]:
    marker = "html = _inject_deterministic_assets(html"
    replacement = (
        marker
        + "\n    if design_tokens:\n"
        "        for _k, _v in design_tokens.items():\n"
        '            html = html.replace(f"var(--{_k},", f"var(--{_k},{_v}", 1)\n'
        "            html = html.replace(f'var(--{_k},', f'var(--{_k},{_v}', 1)"
    )
    b = b.replace(marker, replacement, 1)
    print('builder: injected design_tokens into HTML')

# 4) Add footer-pin call
if "_pin_footer_last" in b and "html = _pin_footer_last(html)" not in b:
    # Find a natural place — after HTML generation, before return
    marker = "    return html\n"
    # Last occurrence before any other function
    last_idx = b.rfind(marker, 0, b.rfind("def "))
    if last_idx != -1:
        b = b[:last_idx] + "    html = _pin_footer_last(html)\n" + b[last_idx:]
        print('builder: added _pin_footer_last call')

# 5) Add footer-last prompt instruction (once, after TAILWIND_FIRST_RULES)
if "footer" not in b[b.find("TAILWIND_FIRST_RULES"):b.find("TAILWIND_FIRST_RULES") + 500]:
    marker = '            "\\n\\nDIRETRIZES OBRIGATÓRIAS DE HTML/CSS:\\n"'
    replacement = (
        '            "\\n\\nDIRETRIZES OBRIGATÓRIAS DE HTML/CSS:\\n"'
        "\n"
        '            "- O <footer> ou <section id=\'footer\'> DEVE ser a ÚLTIMA seção visível.\\n"\n'
        '            "- Nenhuma seção contato/localização/sobre pode aparecer após o footer.\\n"'
    )
    b = b.replace(marker, replacement, 1)
    print('builder: added footer-last prompt instruction')

write(BUILDER, b)

# ─── DESIGN_CONTEXT ───────────────────────────────────────────────────────────
d = read(DC)

# 1) Move inner _SEGMENT_HUE_STRICT to module-level BEFORE function
if "def get_design_context(" in d and "_SEGMENT_HUE_STRICT" not in d[: d.find("def get_design_context(")]:
    lines = d.splitlines(keepends=True)
    new_lines = []
    skip = False
    for i, line in enumerate(lines):
        if i > 500 and line.strip() == "_SEGMENT_HUE_STRICT = {":
            skip = True
            continue
        if skip:
            if line.strip() == "}":
                skip = False
            continue
        new_lines.append(line)
    d = "".join(new_lines)
    mod_def = (
        '_SEGMENT_HUE_STRICT = {\n'
        '    "pizzaria", "pizza", "restaurante", "hamburgueria", "lanchonete",\n'
        '    "churrascaria", "padaria", "sorveteria", "doceria", "confeitaria",\n'
        '    "acai", "sushi", "pastelaria", "food_truck", "bar", "cafe",\n'
        '    "academia", "personal", "crossfit",\n'
        "}\n"
        "\n"
    )
    d = d.replace("def get_design_context(", mod_def + "def get_design_context(", 1)
    print('design_context: moved _SEGMENT_HUE_STRICT to module level')

# 2) Palette rotation — only add if missing
if "_PALETTE_ROTATION" not in d:
    pal_block = (
        "    # ─── PALETTE ROTATION POR LEAD (FRA-LIB 2026-08-17) ────────────────────────\n"
        "    # Para nichos com preferência de cor forte, rotaciona entre 6 paletas vibrantes.\n"
        "    _PALETTE_ROTATION = [\n"
        "        {\"bg\": \"oklch(14% 0.012 260)\", \"surface\": \"oklch(20% 0.015 265)\", \"accent\": \"oklch(85% 0.18 95)\", \"accent_hue\": 95, \"label\": \"amarelo_neon\"},\n"
        "        {\"bg\": \"oklch(13% 0.02 250)\", \"surface\": \"oklch(18% 0.025 252)\", \"accent\": \"oklch(62% 0.22 250)\", \"accent_hue\": 250, \"label\": \"azul_eletrico\"},\n"
        "        {\"bg\": \"oklch(13% 0.015 160)\", \"surface\": \"oklch(19% 0.02 162)\", \"accent\": \"oklch(72% 0.18 145)\", \"accent_hue\": 145, \"label\": \"verde_esmeralda\"},\n"
        "        {\"bg\": \"oklch(14% 0.02 25)\", \"surface\": \"oklch(20% 0.025 27)\", \"accent\": \"oklch(68% 0.22 28)\", \"accent_hue\": 28, \"label\": \"laranja_vulcanico\"},\n"
        "        {\"bg\": \"oklch(13% 0.015 280)\", \"surface\": \"oklch(18% 0.02 283)\", \"accent\": \"oklch(65% 0.24 285)\", \"accent_hue\": 285, \"label\": \"roxo_cyberpunk\"},\n"
        "        {\"bg\": \"oklch(12% 0.005 220)\", \"surface\": \"oklch(17% 0.008 222)\", \"accent\": \"oklch(82% 0.14 195)\", \"accent_hue\": 195, \"label\": \"branco_ciano\"},\n"
        "    ]\n"
        "    if nome_negocio and seg in _SEGMENT_HUE_STRICT:\n"
        "        import hashlib as _hlib_pal, random as _rnd_pal\n"
        "        _palette_seed = int(_hlib_pal.md5(nome_negocio.encode()).hexdigest(), 16)\n"
        "        _palette_rng = _rnd_pal.Random(_palette_seed)\n"
        "        _picked = _palette_rng.choice(_PALETTE_ROTATION)\n"
        "        tokens['--bg'] = _picked['bg']\n"
        "        tokens['--surface'] = _picked['surface']\n"
        "        tokens['--accent'] = _picked['accent']\n"
        "        _palette_hue = _picked['accent_hue']\n"
        "        _palette_applied = True\n"
        "    else:\n"
        "        _palette_hue = _fallback_hue\n"
        "        _palette_applied = False\n"
        "\n"
    )
    d = d.replace(
        "    # Tokens: prioridade DESIGN.md real extraido > DIRECOES_VISUAIS hardcoded\n",
        pal_block + "    # Tokens: prioridade DESIGN.md real extraido > DIRECOES_VISUAIS hardcoded\n",
        1,
    )
    print('design_context: added palette rotation')

# 3) Replace _fallback_hue with _palette_hue (but NOT the definition line)
d = re.sub(r"\b_fallback_hue\b", "_palette_hue", d)
# Restore the one legitimate definition
d = d.replace("_palette_hue = _SEGMENT_HUE.get(seg, 270)", "_fallback_hue = _SEGMENT_HUE.get(seg, 270)", 1)
print('design_context: replaced _fallback_hue -> _palette_hue (kept definition)')

write(DC, d)

# ─── VALIDATE ─────────────────────────────────────────────────────────────────
import py_compile, traceback
for p in (BUILDER, DC):
    try:
        py_compile.compile(p, doraise=True)
        print(f'OK compile: {p}')
    except Exception as e:
        print(f'COMPILE ERROR {p}: {e}')
        sys.exit(1)

print('ALL PATCHES APPLIED + VALIDATED')
