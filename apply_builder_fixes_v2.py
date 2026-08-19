"""Apply F2+F3+F4 edits to builder/agent.py using bytes to avoid encoding issues."""
import re

p = r'C:\fralib\builder_agent_current.py'
with open(p, encoding='utf-8') as f:
    src = f.read()

# We operate on the text directly but avoid problematic chars in the script.
# Use \uXXXX escapes for all non-ASCII.

# F2+F3+F4 builder_directive: inject after FAQ line, before MOTION
trigger = (
    '\u201c- FAQ: acorde\u00e3o com transi\u00e7\u00e3o suave (details/summary animado), n\u00e3o lista plana.\\n\\n'
    '\u201cMOTION:\\n'
)
injection = (
    '\u201c- FAQ: acorde\u00e3o com transi\u00e7\u00e3o suave (details/summary animado), n\u00e3o lista plana.\\n'
    '\u201c\\n'
    '\u201cPROIBI\u00c7\u00c3O DE COLUNA ESMAGADA (F2):\\n'
    '\u201c- NUNCA use classes `min-w-[Npx]` (qualquer N) dentro de grids ou cards.\\n'
    '\u201c- T\u00edtulos de se\u00e7\u00e3o (h1, h2): SEMPRE `max-w-2xl w-full break-normal`.\\n'
    '\u201c  Proibido: `whitespace-nowrap`, `truncate` ou `overflow-hidden` em headings.\\n'
    '\u201c- Cards: `w-full` sem min-width fixo. Conte\u00fado quebra linha livremente.\\n'
    '\u201c\\n'
    '\u201cSHIELD DE CONTRASTE (F3):\\n'
    '\u201c- Se uma se\u00e7\u00e3o usa imagem de fundo com `brightness < 0.5` OU overlay escuro com opacidade > 50\%,\\n'
    '\u201c  TODO texto vis\u00edvel (h1, h2, h3, p) DEVE ter `text-white` ou `color: #ffffff`.\\n'
    '\u201c- NUNCA use `color:var(--fg)` ou `text-[var(--foreground)]` sobre fundo escurecido.\\n'
    '\u201c- Overlay m\u00ednimo: gradient de 60% opacidade do --bg (light) ou 40% do --fg (dark) para garantir contraste > 4.5:1.\\n'
    '\u201c\\n'
    '\u201cCTA FINAL (F4):\\n'
    '\u201c- Container do CTA final: `w-full flex flex-col sm:flex-row items-center justify-center gap-4`.\\n'
    '\u201c- Nunca use `inline` ou `inline-flex` sem wrap em telas < 480px.\\n'
    '\u201c\\n'
    '\u201cPURGA DE SE\u00c7\u00d5ES VAZIAS (F4):\\n'
    '\u201c- Se\u00e7\u00e3o com apenas t\u00edtulo e menos de 30 caracteres de conte\u00fado vis\u00edvel: N\u00c3O renderizar.\\n'
    '\u201c- Em vez de se\u00e7\u00e3o vazia, use um bloco de \u2018Compromissos e Diferenciais\u2019 com 3 bullets.\\n'
    '\u201c\\n'
    '\u201cDEPOIMENTOS (OBRIGAT\u00d3RIO):\\n'
    '\u201c- Use APENAS os reviews reais da lista `reviews_list` (autor + nota + texto).\\n'
    '\u201c- N\u00c3O invente depoimentos, N\u00c3O use placeholder como \'Cliente satisfeito\'.\\n'
    '\u201c- M\u00e1ximo 3 depoimentos, ordenados por nota (maior primeiro).\\n'
    '\u201c- Se `reviews_list` estiver vazia: renderizar bloco \'Compromissos e Diferenciais\'
    'com 3 bullets, NUNCA depoimentos inventados.\\n'
    '\u201c\\n'
    '\u201cMOTION:\\n'
)
if trigger in src:
    src = src.replace(trigger, injection, 1)
    print("[OK] F2+F3+F4 builder_directive injected")
else:
    print("[FAIL] FAQ trigger not found")

# F3: strip -- keys from palette flatten
old_flat = (
    '    # Flatten palette from design_tokens (supports nested palette/color_palette or flat keys)\\n'
    '    flat = dict(design_tokens or {})\\n'
    '    for nested_key in ("palette", "color_palette"):\\n'
    '        nested = flat.get(nested_key)\\n'
    '        if isinstance(nested, dict):\\n'
    '            for k, v in nested.items():\\n'
    '                flat.setdefault(k, v)\\n'
)
new_flat = (
    '    # Flatten palette from design_tokens. CSS-var-named keys (e.g. "--bg") are target\\n'
    '    # variable names, not color values. Strip the "--" prefix so _first("bg") finds the oklch value.\\n'
    '    flat = dict(design_tokens or {})\\n'
    '    for nested_key in ("palette", "color_palette"):\\n'
    '        nested = flat.get(nested_key)\\n'
    '        if isinstance(nested, dict):\\n'
    '            for k, v in nested.items():\\n'
    '                if k.startswith("--"):\\n'
    '                    flat.setdefault(k[2:], v)\\n'
    '                else:\\n'
    '                    flat.setdefault(k, v)\\n'
)
if old_flat in src:
    src = src.replace(old_flat, new_flat)
    print("[OK] F3 palette flatten -- strip")
else:
    print("[FAIL] palette flatten not found")

# F3: Remove --bg from _first fallback
old_bg = '    bg        = _first("background", "bg", "--bg") or "#ffffff"\\n'
new_bg = '    bg        = _first("background", "bg") or "#ffffff"\\n'
if old_bg in src:
    src = src.replace(old_bg, new_bg)
    print("[OK] F3 --bg circular removed")
else:
    print("[FAIL] bg line not found")

# F4: skip-and-continue
old_f4 = (
    '        html, model = _render_block(block_spec, spec.get("design_tokens", {}))\\n'
    '        if not html:\\n'
    '            return [], last_model, f"Falha ao gerar secao [{s.get(\'name\', \'?\')}]"\\n'
    '        partials.append(html)\\n'
    '        last_model = model or last_model\\n'
)
new_f4 = (
    '        html, model = _render_block(block_spec, spec.get("design_tokens", {}))\\n'
    '        if not html or len(re.sub(r"<[^>]+>", "", html).strip()) < 30:\\n'
    '            _builder_logger.warning("[builder] pulando secao vazia/invalida: {}", s.get("name"))\\n'
    '            continue\\n'
    '        partials.append(html)\\n'
    '        last_model = model or last_model\\n'
)
if old_f4 in src:
    src = src.replace(old_f4, new_f4)
    print("[OK] F4 skip-and-continue")
else:
    print("[FAIL] F4 target not found")

with open(p, 'w', encoding='utf-8') as f:
    f.write(src)
print(f"Written. Size: {len(src)} bytes")

# Validate
import py_compile
try:
    py_compile.compile(p, doraise=True)
    print("[OK] py_compile passed")
except py_compile.PyCompileError as e:
    print(f"[FAIL] py_compile: {e}")
