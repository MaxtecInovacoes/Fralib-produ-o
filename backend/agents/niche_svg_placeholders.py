"""SVG placeholders niche-aware.

Em vez de usar Unsplash genéricos ou fallbacks vazios,
gera SVGs inline que representam visualmente cada nicho.

Usado quando:
1. Lead não tem fotos
2. Fotos falharam ao carregar
3. Quer manter consistência visual
"""

from typing import Callable


# Paletas por nicho (background, accent, text)
NICHO_PALETTES: dict[str, tuple[str, str, str]] = {
    "academia": ("#1a1a1a", "#ff4444", "#ffffff"),
    "crossfit": ("#0f0f0f", "#ffcc00", "#ffffff"),
    "fitness": ("#1a1a1a", "#ff6b35", "#ffffff"),
    "nutricionista": ("#f5f5f0", "#7ab87a", "#2d4a2d"),
    "nutricao": ("#f5f5f0", "#7ab87a", "#2d4a2d"),
    "dentista": ("#f8f9fa", "#4a90d9", "#1a365d"),
    "odontologia": ("#f8f9fa", "#4a90d9", "#1a365d"),
    "restaurante": ("#2d1810", "#d4a574", "#fff8f0"),
    "pizzaria": ("#1a0f05", "#e85d04", "#ffd166"),
    "hamburgueria": ("#1a0a00", "#ff6b35", "#ffd166"),
    "cafe": ("#f5f0e8", "#8b7355", "#3d2914"),
    "padaria": ("#f5e6d3", "#c9a66b", "#5d4e37"),
    "barbearia": ("#1a1a1a", "#d4af37", "#ffffff"),
    "estetica": ("#1a0a15", "#c77dff", "#fff0f5"),
    "clinica": ("#f0f4f8", "#38b2ac", "#1a365d"),
    "advocacia": ("#1a2332", "#c9a227", "#f5f5f5"),
    "escritorio": ("#f5f5f5", "#4a5568", "#1a202c"),
    "pet": ("#e8f5e9", "#81c784", "#1b5e20"),
    "petshop": ("#e8f5e9", "#81c784", "#1b5e20"),
    "default": ("#f0f0f0", "#6b7280", "#374151"),
}


def get_niche_palette(segmento: str) -> tuple[str, str, str]:
    """Retorna (bg, accent, fg) para o segmento."""
    segmento_lower = segmento.lower()
    for niche, palette in NICHO_PALETTES.items():
        if niche in segmento_lower:
            return palette
    return NICHO_PALETTES["default"]


def generate_hero_svg(segmento: str, business_name: str = "", size: str = "1400x800") -> str:
    """Gera SVG de hero placeholder para o nicho."""
    bg, accent, fg = get_niche_palette(segmento)
    w, h = map(int, size.split("x"))

    # Ícones simples por nicho (inline SVG path)
    icon_paths = {
        "academia": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-2-3.5l6-4.5-6-4.5v9z",
        "crossfit": "M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5",
        "nutricionista": "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z",
        "dentista": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z",
        "restaurante": "M11 9H9V2H7v7H5V2H3v7c0 2.12 1.66 3.84 3.75 3.97V22h2.5v-9.03C11.34 12.84 13 11.12 13 9V2h-2v7zm5-3v8h2.5v8H21V2c-2.76 0-5 2.24-5 4z",
        "pizzaria": "M12 2C8.43 2 5.23 3.54 3.01 6L12 22l8.99-16C18.78 3.55 15.57 2 12 2zM7 7c0-1.1.9-2 2-2s2 .9 2 2-.9 2-2 2-2-.9-2-2zm5 8l-2-2 4-4 2 2-4 4z",
        "barbearia": "M8 2v4H6v2h2v12c0 1.1.9 2 2 2h4c1.1 0 2-.9 2-2V8h2V6h-2V2h-8zm4 18c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1z",
        "estetica": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z",
        "clinica": "M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-1 11h-4v4h-4v-4H6v-4h4V6h4v4h4v4z",
        "advocacia": "M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z",
        "pet": "M4.5 9.5m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0 -5 0M9 5.5m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0 -5 0M15 5.5m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0 -5 0M19.5 9.5m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0 -5 0M17.34 14.86c-.87-1.02-1.6-1.89-2.48-2.91-.46-.54-1.17-.79-1.86-.79-.69 0-1.4.25-1.86.79-.88 1.02-1.61 1.89-2.48 2.91-1.31 1.31-2.92 2.76-2.62 4.79.29 1.02 1.02 2.03 2.33 2.32.73.15 3.06-.44 5.63-.44h.18c2.57 0 4.9.59 5.63.44 1.31-.29 2.04-1.31 2.33-2.32.31-2.04-1.3-3.49-2.62-4.8z",
        "default": "M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z",
    }

    # Encontrar ícone apropriado
    icon = icon_paths["default"]
    for niche, path in icon_paths.items():
        if niche in segmento.lower():
            icon = path
            break

    name_text = business_name[:20] if business_name else "Seu Negócio"
    sector_text = segmento.title()[:30] if segmento else "Profissional"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{bg};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{_darken(bg, 15)};stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="{w}" height="{h}" fill="url(#bg)"/>
  <g transform="translate({w//2 - 50}, {h//2 - 100})">
    <circle cx="50" cy="50" r="45" fill="{accent}" opacity="0.15"/>
    <circle cx="50" cy="50" r="35" fill="{accent}" opacity="0.25"/>
    <path d="{icon}" fill="{accent}" transform="scale(3) translate(8, 8)"/>
  </g>
  <text x="{w//2}" y="{h//2 + 20}" text-anchor="middle" font-family="system-ui, sans-serif" font-size="28" font-weight="600" fill="{fg}">{name_text}</text>
  <text x="{w//2}" y="{h//2 + 55}" text-anchor="middle" font-family="system-ui, sans-serif" font-size="16" fill="{fg}" opacity="0.7">{sector_text}</text>
  <rect x="{w//2 - 80}" y="{h//2 + 75}" width="160" height="2" fill="{accent}" opacity="0.5"/>
</svg>'''

    return svg


def generate_section_svg(segmento: str, section_type: str = "generic", size: str = "600x400") -> str:
    """Gera SVG de seção (sobre, serviços, etc)."""
    bg, accent, fg = get_niche_palette(segmento)
    w, h = map(int, size.split("x"))

    # Padrões geométricos por tipo de seção
    patterns = {
        "hero": f"fill:{accent};opacity:0.1",
        "sobre": f"fill:{accent};opacity:0.05",
        "servicos": f"fill:{accent};opacity:0.08",
        "depoimentos": f"fill:{accent};opacity:0.06",
        "contato": f"fill:{accent};opacity:0.1",
        "generic": f"fill:{accent};opacity:0.05",
    }
    pattern_style = patterns.get(section_type, patterns["generic"])

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <rect width="{w}" height="{h}" fill="{bg}"/>
  <rect x="0" y="0" width="{w}" height="{h}" style="{pattern_style}"/>
  <circle cx="50" cy="50" r="30" fill="{accent}" opacity="0.2"/>
  <circle cx="{w-50}" cy="{h-50}" r="40" fill="{accent}" opacity="0.15"/>
  <rect x="{w//2-30}" y="{h//2-5}" width="60" height="3" fill="{accent}" opacity="0.4"/>
  <rect x="{w//2-50}" y="{h//2+10}" width="100" height="2" fill="{fg}" opacity="0.2"/>
</svg>'''

    return svg


def svg_to_data_uri(svg: str) -> str:
    """Converte SVG para data URI."""
    import base64
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


def _darken(hex_color: str, percent: int = 10) -> str:
    """Escurece uma cor hex."""
    if not hex_color.startswith("#") or len(hex_color) != 7:
        return hex_color
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    r = max(0, r - int(255 * percent / 100))
    g = max(0, g - int(255 * percent / 100))
    b = max(0, b - int(255 * percent / 100))
    return f"#{r:02x}{g:02x}{b:02x}"


# URLs de referência para SVGs hospedados (alternativa a inline)
NICHO_SVG_URLS: dict[str, str] = {
    "academia": "https://fraub-assets.s3.amazonaws.com/placeholders/academia-hero.svg",
    "restaurante": "https://fraub-assets.s3.amazonaws.com/placeholders/restaurante-hero.svg",
    "default": "https://fraub-assets.s3.amazonaws.com/placeholders/default-hero.svg",
}


def get_placeholder_url(segmento: str) -> str:
    """Retorna URL do placeholder SVG para o nicho (ou default)."""
    segmento_lower = segmento.lower()
    for niche, url in NICHO_SVG_URLS.items():
        if niche in segmento_lower:
            return url
    return NICHO_SVG_URLS["default"]
