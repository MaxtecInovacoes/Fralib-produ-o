"""Apply F2+F3+F4 to builder_agent_current.py by line index."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

p = r'C:\fralib\builder_agent_current.py'
with open(p, encoding='utf-8') as f:
    lines = f.readlines()

# ── F2+F3+F4 builder_directive: replace lines 690-691 ──
new_block = [
    '        "- FAQ: acorde\u00e3o com transi\u00e7\u00e3o suave (details/summary animado), n\u00e3o lista plana.\\n"\n',
    '        "\\n"\n',
    '        "PROIBI\u00c7\u00c3O DE COLUNA ESMAGADA (F2):\\n"\n',
    '        "- NUNCA use classes `min-w-[Npx]` (qualquer N) dentro de grids ou cards.\\n"\n',
    '        "- T\u00edtulos de se\u00e7\u00e3o (h1, h2): SEMPRE `max-w-2xl w-full break-normal`.\\n"\n',
    '        "  Proibido: `whitespace-nowrap`, `truncate` ou `overflow-hidden` em headings.\\n"\n',
    '        "- Cards: `w-full` sem min-width fixo. Conte\u00fado quebra linha livremente.\\n"\n',
    '        "\\n"\n',
    '        "SHIELD DE CONTRASTE (F3):\\n"\n',
    '        "- Se uma se\u00e7\u00e3o usa imagem de fundo com `brightness < 0.5` OU overlay escuro com opacidade > 50%, TODO texto vis\u00edvel (h1, h2, h3, p) DEVE ter `text-white` ou `color: #ffffff`.\\n"\n',
    '        "- NUNCA use `color:var(--fg)` ou `text-[var(--foreground)]` sobre fundo escurecido.\\n"\n',
    '        "- Overlay m\u00ednimo: gradient de 60% opacidade do --bg (light) ou 40% do --fg (dark) para garantir contraste > 4.5:1.\\n"\n',
    '        "\\n"\n',
    '        "CTA FINAL (F4):\\n"\n',
    '        "- Container do CTA final: `w-full flex flex-col sm:flex-row items-center justify-center gap-4`.\\n"\n',
    '        "- Nunca use `inline` ou `inline-flex` sem wrap em telas < 480px.\\n"\n',
    '        "\\n"\n',
    '        "PURGA DE SE\u00c7\u00d5ES VAZIAS (F4):\\n"\n',
    '        "- Se\u00e7\u00e3o com apenas t\u00edtulo e menos de 30 caracteres de conte\u00fado vis\u00edvel: N\u00c3O renderizar.\\n"\n',
    '        "- Em vez de se\u00e7\u00e3o vazia, use um bloco de \u2018Compromissos e Diferenciais\u2019 com 3 bullets.\\n"\n',
    '        "\\n"\n',
    '        "DEPOIMENTOS (OBRIGAT\u00d3RIO):\\n"\n',
    '        "- Use APENAS os reviews reais da lista `reviews_list` (autor + nota + texto).\\n"\n',
    '        "- N\u00c3O invente depoimentos, N\u00c3O use placeholder como \'Cliente satisfeito\'.\\n"\n',
    '        "- M\u00e1ximo 3 depoimentos, ordenados por nota (maior primeiro).\\n"\n',
    '        "- Se `reviews_list` estiver vazia: renderizar bloco \'Compromissos e Diferenciais\' com 3 bullets, NUNCA depoimentos inventados.\\n"\n',
    '        "\\n"\n',
    '        "MOTION:\\n"\n',
]
# Replace lines 691 (index 690) - just the MOTION line - with the new block + MOTION at end
# Lines 690 + 691 in 1-indexed = indices 689 + 690 in 0-indexed
# Keep line 690 (FAQ), replace line 691 (MOTION) with new_block
lines = lines[:690] + new_block + lines[691:]
print(f"[OK] F2+F3+F4 directive injected ({len(new_block)} lines)")

# Adjust remaining line indices: subtract inserted count
inserted = len(new_block) - 1  # net change = new_lines - old_lines = 28 - 1 = 27

# ── F3 palette flatten: line 853 (1-indexed) = index 852, replace 7 lines (853-859)
# After previous insert: index is now 852 + 27 = 879
# But better: search by content since indices shift
for i, l in enumerate(lines):
    if 'Flatten palette from design_tokens' in l:
        # Replace this comment + next 6 lines with the new block
        new_flat = [
            '    # Flatten palette from design_tokens. CSS-var-named keys (e.g. "--bg") are target\\n',
            '    # variable names, not color values. Strip the "--" prefix so _first("bg") finds the oklch value.\\n',
            '    flat = dict(design_tokens or {})\\n',
            '    for nested_key in ("palette", "color_palette"):\\n',
            '        nested = flat.get(nested_key)\\n',
            '        if isinstance(nested, dict):\\n',
            '            for k, v in nested.items():\\n',
            '                if k.startswith("--"):\\n',
            '                    flat.setdefault(k[2:], v)\\n',
            '                else:\\n',
            '                    flat.setdefault(k, v)\\n',
        ]
        lines = lines[:i] + new_flat + lines[i+7:]
        print(f"[OK] F3 palette flatten (line {i+1})")
        break

# ── F3 --bg: find and replace
for i, l in enumerate(lines):
    if '--bg' in l and '_first' in l and 'background' in l:
        lines[i] = '    bg        = _first("background", "bg") or "#ffffff"\n'
        print(f"[OK] F3 --bg removed (line {i+1})")
        break

# ── F4 skip-and-continue: find fail-fast and replace 3 lines (1226, 1227, 1228 -> new 5 lines)
# Wait, after inserts the line numbers shifted. Search by content.
for i, l in enumerate(lines):
    if 'Falha ao gerar secao' in l and 'return' in l:
        # Replace line at i (the return), and prepend skip-and-continue before it
        # Line at i-1 is `if not html:`
        # Lines i, i+1 will be replaced
        lines[i-1] = '        if not html or len(re.sub(r"<[^>]+>", "", html).strip()) < 30:\n'
        lines[i] = '            _builder_logger.warning("[builder] pulando secao vazia/invalida: {}", s.get("name"))\n'
        # Insert `continue` line at position i+1
        lines.insert(i+1, '            continue\n')
        print(f"[OK] F4 skip-and-continue (line {i})")
        break

with open(p, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print(f"Total: {len(lines)} lines")

import py_compile
try:
    py_compile.compile(p, doraise=True)
    print("[OK] py_compile PASSED")
except py_compile.PyCompileError as e:
    print(f"[FAIL] py_compile: {e}")