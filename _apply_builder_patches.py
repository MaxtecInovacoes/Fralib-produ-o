"""Apply FRA-LIB footer-pin + palette patches to builder/agent.py.

P1: _pin_footer_last function (after `import re`)
P2: Palette import injection (after design_tokens dict closing brace)
P3: design_tokens HTML injection (after _inject_deterministic_assets call)
P4: footer-last prompt instruction
"""
import re

BUILDER = r"C:\fralib\backend\agents\builder\agent.py"

with open(BUILDER, encoding="utf-8") as f:
    src = f.read()

assert "_pin_footer_last" in src, "P1 missing — run restore first"
assert "_gdc" not in src, "already patched"

# ── PATCH 2: palette import injection AFTER design_tokens closing brace ────────
# Find `    }` right after line 609 (closing of design_tokens dict)
# Then next line is `    color_palette = ...` — inject between them
m = re.search(
    r'("palette_bias": archetype_system.get\("palette_bias", \{\}\)\s*,\s*\n\s*\}\s*\n\s*)(color_palette =)',
    src,
)
assert m, "could not find design_tokens closing brace"
palette_injection = (
    m.group(1)
    + "    # Inject palette rotation tokens from design_context\n"
    "    try:\n"
    '        from agents.design_context import get_design_context as _gdc\n'
    "        _ctx = _gdc(_seg, _nome, getattr(prd, 'tier', 'STANDARD') or 'STANDARD', False)\n"
    "        _ctx_tokens = _ctx.get('tokens', {}) if isinstance(_ctx, dict) else {}\n"
    "        for _tk, _tv in _ctx_tokens.items():\n"
    "            _flat = _tk[2:] if _tk.startswith('--') else _tk\n"
    "            design_tokens[_flat] = _tv\n"
    "    except Exception:\n"
    "        pass\n\n    "
)
src = src[:m.start()] + palette_injection + src[m.end():]
assert "_gdc" in src
print("PATCH 2 OK: palette injection after design_tokens dict")

# ── PATCH 3: inject design_tokens into final HTML ─────────────────────────────
old3 = 'final_html = _inject_deterministic_assets(final_html, spec.get("design_tokens", {}))'
new3 = (
    'final_html = _inject_deterministic_assets(final_html, spec.get("design_tokens", {}))\n'
    "    # Inject palette tokens into HTML (if design_context set them)\n"
    "    if design_tokens:\n"
    "        for _k, _v in design_tokens.items():\n"
    '            final_html = final_html.replace(f"var(--{_k},", f"var(--{_k},{_v}", 1)\n'
    '            final_html = final_html.replace(f\'var(--{_k},\', f\'var(--{_k},{_v}\', 1)'
)
assert old3 in src, "could not find _inject_deterministic_assets call"
src = src.replace(old3, new3, 1)
print("PATCH 3 OK: design_tokens into HTML")

# ── PATCH 4: footer-last prompt instruction ───────────────────────────────────
old4 = (
    '"\\n\\nDIRETRIZES OBRIGAT\\u00d3RIAS DE HTML/CSS:\\n"'
    "\n"
    '            f"{TAILWIND_FIRST_RULES.strip()}"\n\n'
    '            "REGRAS DE ESTRUTURA:\\n"'
)
new4 = (
    '"\\n\\nDIRETRIZES OBRIGAT\\u00d3RIAS DE HTML/CSS:\\n"'
    "\n"
    '            "- O <footer> ou <section id=footer> DEVE ser a ULTIMA secao visivel.\\n"\n'
    '            "- Nenhuma secao contato/localizacao/sobre pode aparecer apos o footer.\\n"\n'
    "\n"
    '            f"{TAILWIND_FIRST_RULES.strip()}"\n\n'
    '            "REGRAS DE ESTRUTURA:\\n"'
)
if old4 in src:
    src = src.replace(old4, new4, 1)
    print("PATCH 4 OK: footer-last prompt")
else:
    print("PATCH 4 SKIP: marker not found")

with open(BUILDER, "w", encoding="utf-8") as f:
    f.write(src)

# Validate
import py_compile
try:
    py_compile.compile(BUILDER, doraise=True)
    print("COMPILE OK")
except Exception as e:
    print(f"COMPILE ERROR: {e}")
    import sys
    sys.exit(1)

print("ALL PATCHES APPLIED")
