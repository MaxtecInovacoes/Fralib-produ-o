"""
Color Enforcer - Garante paleta harmoniosa e contraste WCAG
FONTE UNICA DE VERDADE para cores do sistema FraLib
Etapa dedicada: extrai -> harmoniza -> valida -> injeta
"""
import re
import colorsys

# ===== UTILITARIOS =====

def hex_to_rgb(h: str):
    h = h.lstrip("#")
    if len(h) != 6: return (55, 65, 81)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

def hex_to_hsl(h: str):
    r, g, b = [x/255 for x in hex_to_rgb(h)]
    hh, l, s = colorsys.rgb_to_hls(r, g, b)
    return hh, s, l

def hsl_to_hex(h, s, l) -> str:
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))

def luminance(hex_c: str) -> float:
    r, g, b = [x/255 for x in hex_to_rgb(hex_c)]
    r, g, b = [x/12.92 if x <= 0.03928 else ((x+0.055)/1.055)**2.4 for x in [r, g, b]]
    return 0.2126*r + 0.7152*g + 0.0722*b

def contrast_ratio(c1: str, c2: str) -> float:
    l1, l2 = luminance(c1), luminance(c2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

def saturacao(hex_c: str) -> float:
    _, s, _ = hex_to_hsl(hex_c)
    return s

def ajustar_para_contraste(hex_c: str, fundo: str = "#ffffff", min_ratio: float = 4.5) -> str:
    """Escurece ou clareia a cor ate atingir contraste minimo com o fundo"""
    h, s, l = hex_to_hsl(hex_c)
    fundo_lum = luminance(fundo)
    # Tentar escurecer primeiro
    for step in range(20):
        l_new = max(0.05, l - step * 0.04)
        candidate = hsl_to_hex(h, s, l_new)
        if contrast_ratio(candidate, fundo) >= min_ratio:
            return candidate
    # Se nao conseguir escurecendo, clarear
    for step in range(20):
        l_new = min(0.95, l + step * 0.04)
        candidate = hsl_to_hex(h, s, l_new)
        if contrast_ratio(candidate, fundo) >= min_ratio:
            return candidate
    return "#1f2937"  # fallback seguro

def gerar_acento_harmonioso(primary_hex: str) -> str:
    """Gera cor de acento harmoniosa (complementar split) a partir da primaria"""
    h, s, l = hex_to_hsl(primary_hex)
    # Split complementar: 150 graus de distancia
    h_acento = (h + 150/360) % 1.0
    # Manter saturacao vibrante e luminosidade media
    s_acento = max(0.5, min(0.85, s * 1.1))
    l_acento = max(0.35, min(0.55, l))
    return hsl_to_hex(h_acento, s_acento, l_acento)

def gerar_escala_cor(hex_color: str) -> dict:
    h, s, l = hex_to_hsl(hex_color)
    steps = {50:0.97, 100:0.93, 200:0.86, 300:0.76, 400:0.63,
             500:0.50, 600:0.40, 700:0.32, 800:0.25, 900:0.18, 950:0.12}
    return {k: hsl_to_hex(h, s, v) for k, v in steps.items()}

# ===== HARMONIZACAO =====

def harmonizar_paleta(colors: dict) -> dict:
    """
    Etapa dedicada de harmonizacao:
    1. Valida contraste da primaria com branco
    2. Gera acento harmonioso se o acento atual nao combinar
    3. Garante que primary e accent nao sejam cores similares
    4. Retorna paleta harmonizada com texto correto para cada cor
    """
    primary = colors.get("primary", "#374151")
    accent  = colors.get("accent",  "#e85d04")

    print(f"[ColorHarmonizer] Entrada: primary={primary} accent={accent}")

    # 1. Ajustar primaria para contraste minimo 4.5:1 com branco
    cr_primary = contrast_ratio(primary, "#ffffff")
    if cr_primary < 4.5:
        primary = ajustar_para_contraste(primary, "#ffffff", 4.5)
        print(f"[ColorHarmonizer] Primary ajustada para contraste: {primary} (ratio={round(contrast_ratio(primary,'#ffffff'),2)})")

    # 2. Verificar se accent e primary sao muito similares (hue < 30 graus de diferenca)
    h_p, s_p, l_p = hex_to_hsl(primary)
    h_a, s_a, l_a = hex_to_hsl(accent)
    hue_diff = abs(h_p - h_a) * 360
    if hue_diff > 180: hue_diff = 360 - hue_diff

    if hue_diff < 30 or saturacao(accent) < 0.2:
        accent = gerar_acento_harmonioso(primary)
        print(f"[ColorHarmonizer] Accent gerado harmonioso: {accent} (hue_diff era {round(hue_diff)}deg)")
    else:
        # Ajustar contraste do accent tambem
        cr_accent = contrast_ratio(accent, "#ffffff")
        if cr_accent < 3.0:
            accent = ajustar_para_contraste(accent, "#ffffff", 3.0)
            print(f"[ColorHarmonizer] Accent ajustado para contraste: {accent}")

    # 3. Definir texto correto sobre cada cor
    text_on_primary = "#ffffff" if contrast_ratio(primary, "#ffffff") >= 4.5 else "#111827"
    text_on_accent  = "#ffffff" if contrast_ratio(accent,  "#ffffff") >= 4.5 else "#111827"

    # 4. Gerar surface escuro para secoes dark
    h_dark, _, _ = hex_to_hsl(primary)
    dark_surface = hsl_to_hex(h_dark, 0.3, 0.08)

    harmonized = {
        "primary":          primary,
        "secondary":        colors.get("secondary", "#f9fafb"),
        "accent":           accent,
        "background":       "#ffffff",
        "text":             "#1f2937",
        "text_on_primary":  text_on_primary,
        "text_on_accent":   text_on_accent,
        "dark_surface":     dark_surface,
        "bg_classes": {
            "hero":        "section-bg-dark",
            "sobre":       "section-bg-subtle",
            "servicos":    "section-bg-mesh",
            "depoimentos": "section-bg-dark",
            "localizacao": "section-bg-subtle",
            "contato":     "section-bg-brand",
            "footer":      "section-bg-dark",
        }
    }

    print(f"[ColorHarmonizer] Paleta harmonizada: primary={primary} accent={accent}")
    print(f"[ColorHarmonizer] WCAG: text_on_primary={text_on_primary} ({round(contrast_ratio(primary,text_on_primary),2)}:1) text_on_accent={text_on_accent} ({round(contrast_ratio(accent,text_on_accent),2)}:1)")
    return harmonized

# ===== CSS VARS =====

def gerar_css_vars_completo(colors: dict) -> str:
    primary    = colors.get("primary",    "#374151")
    secondary  = colors.get("secondary",  "#f9fafb")
    accent     = colors.get("accent",     "#e85d04")
    background = colors.get("background", "#ffffff")
    text       = colors.get("text",       "#1f2937")
    dark_surf  = colors.get("dark_surface", "#0d1117")

    ep = gerar_escala_cor(primary)
    ea = gerar_escala_cor(accent)

    lines = [":root {",
             f"  --color-primary: {primary};",
             f"  --color-secondary: {secondary};",
             f"  --color-accent: {accent};",
             f"  --color-background: {background};",
             f"  --color-text: {text};",
             f"  --color-surface: #f9fafb;",
             f"  --color-border: #e5e7eb;",
             f"  --color-muted: #6b7280;",
             f"  --color-dark-surface: {dark_surf};"]
    for k, v in ep.items():
        lines.append(f"  --color-p{k}: {v};")
    for k, v in ea.items():
        lines.append(f"  --color-a{k}: {v};")
    lines.append("}")
    return "\n".join(lines)

# ===== ENFORCE (ponto de entrada) =====

def enforce_colors(html: str, colors: dict) -> str:
    """
    Ponto de entrada unico para cores.
    1. Harmoniza a paleta
    2. Injeta CSS vars completo no head
    """
    # Harmonizar antes de injetar
    harmonized = harmonizar_paleta(colors)

    # Atualizar colors com valores harmonizados para uso externo
    colors.update(harmonized)

    css_vars  = gerar_css_vars_completo(harmonized)
    css_block = f"<style id=\"fralib-colors\">\n{css_vars}\n</style>"

    if "fralib-colors" in html:
        # Substituir bloco existente
        html = re.sub(r'<style id="fralib-colors">.*?</style>', css_block, html, flags=re.DOTALL)
    else:
        html = re.sub(r"(<head[^>]*>)", r"\1\n" + css_block, html, count=1, flags=re.IGNORECASE)

    
    print(f"[ColorEnforcer] Paleta harmonizada + escala completa injetada")
    return html
