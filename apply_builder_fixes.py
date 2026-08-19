"""Apply F2+F3+F4 edits to builder/agent.py (current UPGRADE2 version)."""
import re

p = r'C:\fralib\builder_agent_current.py'
with open(p, encoding='utf-8') as f:
    src = f.read()

# ── F2: Column squeeze + F3: Contrast shield + F4: CTA + purge + depoimentos ──
# Insert after line 690 ("- FAQ: acordeão ..."), before "MOTION:"
old = (
    '        "- FAQ: acordeão com transição suave (details/summary animado), não lista plana.\\n\\n'
    '        "MOTION:\\n"'
)
new = (
    '        "- FAQ: acordeão com transição suave (details/summary animado), não lista plana.\\n'
    '        "\\n'
    '        "PROIBIÇÃO DE COLUNA ESMAGADA (F2):\\n"
    '        "- NUNCA use classes `min-w-[Npx]` (qualquer N) dentro de grids ou cards.\\n"
    '        "- Títulos de seção (h1, h2): SEMPRE `max-w-2xl w-full break-normal`.\\n"
    '        "  Proibido: `whitespace-nowrap`, `truncate` ou `overflow-hidden` em headings.\\n"
    '        "- Cards: `w-full` sem min-width fixo. Conteúdo quebra linha livremente.\\n"
    '        "\\n"
    '        "SHIELD DE CONTRASTE (F3):\\n"
    '        "- Se uma seção usa imagem de fundo com `brightness < 0.5` OU overlay escuro com opacidade > 50%,\\n"
    '        "  TODO texto visível (h1, h2, h3, p) DEVE ter `text-white` ou `color: #ffffff`.\\n"
    '        "- NUNCA use `color:var(--fg)` ou `text-[var(--foreground)]` sobre fundo escurecido.\\n"
    '        "- Overlay mínimo: gradient de 60% opacidade do --bg (light) ou 40% do --fg (dark) para garantir contraste > 4.5:1.\\n"
    '        "\\n"
    '        "CTA FINAL (F4):\\n"
    '        "- Container do CTA final: `w-full flex flex-col sm:flex-row items-center justify-center gap-4`.\\n"
    '        "- Nunca use `inline` ou `inline-flex` sem wrap em telas < 480px.\\n"
    '        "\\n"
    '        "PURGA DE SEÇÕES VAZIAS (F4):\\n"
    '        "- Seção com apenas título e menos de 30 caracteres de conteúdo visível: NÃO renderizar.\\n"
    '        "- Em vez de seção vazia, use um bloco de \'Compromissos e Diferenciais\' com 3 bullets.\\n"
    '        "\\n"
    '        "DEPOIMENTOS (OBRIGATÓRIO):\\n"
    '        "- Use APENAS os reviews reais da lista `reviews_list` (autor + nota + texto).\\n"
    '        "- NÃO invente depoimentos, NÃO use placeholder como \'Cliente satisfeito\'.\\n"
    '        "- Máximo 3 depoimentos, ordenados por nota (maior primeiro).\\n"
    '        "- Se `reviews_list` estiver vazia: renderizar bloco \'Compromissos e Diferenciais\' "
    'com 3 bullets, NUNCA depoimentos inventados.\\n'
    '        "\\n'
    '        "MOTION:\\n"
)
if old in src:
    src = src.replace(old, new)
    print("[OK] F2+F3+F4 builder_directive injected")
else:
    print("[FAIL] Could not find target string for F2+F3+F4")

# ── F3: strip -- keys from palette flatten ──
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
    print("[OK] F3 palette flatten -- strip applied")
else:
    print("[FAIL] Could not find target for F3 palette flatten")

# ── F3: Remove --bg from _first fallback ──
old_bg = '    bg        = _first("background", "bg", "--bg") or "#ffffff"\\n'
new_bg = '    bg        = _first("background", "bg") or "#ffffff"\\n'
if old_bg in src:
    src = src.replace(old_bg, new_bg)
    print("[OK] F3 --bg circular removed")
else:
    print("[FAIL] Could not find bg line")

# ── F4: skip-and-continue in _render_section_blocks ──
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
    print("[OK] F4 skip-and-continue applied")
else:
    print("[FAIL] Could not find F4 target")

with open(p, 'w', encoding='utf-8') as f:
    f.write(src)
print(f"Total size: {len(src)} bytes")
