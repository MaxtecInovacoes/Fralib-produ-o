"""hero_styles.py — Estilos de hero por direção visual.

Extraído de design_context.py para encapsulamento reutilizável.
Fornece HERO_STYLES (10 direções), get_hero_style() e get_hero_css().
"""

from typing import Dict


# ─── HERO STYLES por Direção Visual ────────────────────────────────────────────
HERO_STYLES: Dict[str, Dict] = {
    "editorial": {
        "layout":   "hero-split",
        "gradient": (
            "background:linear-gradient(135deg,"
            "oklch(12% 0.015 260) 0%,"
            "oklch(18% 0.020 280) 50%,"
            "oklch(14% 0.012 240) 100%);"
            "animation:hero-shift 12s ease-in-out infinite alternate;"
        ),
        "keyframes": (
            "@keyframes hero-shift{"
            "0%{background-position:0% 50%}"
            "100%{background-position:100% 50%}"
            "}"
        ),
        "overlay":  "rgba(0,0,0,0.55)",
        "text_pos": "left",
        "img_style": "object-fit:cover;filter:contrast(1.05) saturate(0.9);",
    },
    "minimal": {
        "layout":   "hero-center",
        "gradient": (
            "background:linear-gradient(160deg,"
            "oklch(97% 0.005 260) 0%,"
            "oklch(93% 0.010 240) 60%,"
            "oklch(95% 0.008 220) 100%);"
        ),
        "keyframes": "",
        "overlay":  "rgba(255,255,255,0.0)",
        "text_pos": "center",
        "img_style": "object-fit:cover;filter:saturate(0.85) brightness(0.95);",
    },
    "cafe": {
        "layout":   "hero-fullscreen",
        "gradient": (
            "background:linear-gradient(150deg,"
            "oklch(30% 0.040 50) 0%,"
            "oklch(22% 0.030 40) 50%,"
            "oklch(18% 0.020 35) 100%);"
            "background-size:200% 200%;"
            "animation:hero-warm 10s ease-in-out infinite alternate;"
        ),
        "keyframes": (
            "@keyframes hero-warm{"
            "0%{background-position:0% 0%}"
            "100%{background-position:100% 100%}"
            "}"
        ),
        "overlay":  "rgba(20,10,5,0.50)",
        "text_pos": "center",
        "img_style": "object-fit:cover;filter:saturate(1.1) brightness(0.85);",
    },
    "clean": {
        "layout":   "hero-split",
        "gradient": (
            "background:linear-gradient(120deg,"
            "oklch(14% 0.020 220) 0%,"
            "oklch(20% 0.025 230) 100%);"
        ),
        "keyframes": "",
        "overlay":  "rgba(0,0,0,0.45)",
        "text_pos": "left",
        "img_style": "object-fit:cover;filter:contrast(1.1) saturate(0.8);",
    },
    "brutalism": {
        "layout":   "hero-fullscreen",
        "gradient": (
            "background:oklch(98% 0.000 0);"
            "position:relative;"
        ),
        "keyframes": (
            "@keyframes hero-noise{"
            "0%,100%{opacity:0.03}"
            "50%{opacity:0.06}"
            "}"
        ),
        "overlay":  "rgba(0,0,0,0.0)",
        "text_pos": "left",
        "img_style": "object-fit:cover;filter:grayscale(0.3) contrast(1.15);",
        "noise": True,  # adiciona camada de ruido CSS
    },
    "bold": {
        "layout":   "hero-fullscreen",
        "gradient": (
            "background:linear-gradient(160deg,"
            "oklch(5% 0.01 220) 0%,"
            "oklch(12% 0.02 240) 50%,"
            "oklch(8% 0.015 200) 100%);"
            "background-size:200% 200%;"
            "animation:hero-bold 8s ease-in-out infinite alternate;"
        ),
        "keyframes": (
            "@keyframes hero-bold{"
            "0%{background-position:0% 50%}"
            "100%{background-position:100% 50%}"
            "}"
        ),
        "overlay":  "rgba(0,0,0,0.50)",
        "text_pos": "center",
        "img_style": "object-fit:cover;filter:contrast(1.2) brightness(0.75) saturate(1.1);",
    },
    "nike": {
        "layout":   "hero-fullscreen",
        "gradient": (
            "background:oklch(4% 0.0 0);"
        ),
        "keyframes": "",
        "overlay":  "rgba(0,0,0,0.60)",
        "text_pos": "center",
        "img_style": "object-fit:cover;filter:contrast(1.3) brightness(0.7) saturate(0.9);",
    },
    "energetic": {
        "layout":   "hero-fullscreen",
        "gradient": (
            "background:linear-gradient(135deg,"
            "oklch(8% 0.02 250) 0%,"
            "oklch(15% 0.04 200) 100%);"
        ),
        "keyframes": "",
        "overlay":  "rgba(0,0,0,0.45)",
        "text_pos": "center",
        "img_style": "object-fit:cover;filter:contrast(1.15) brightness(0.8) saturate(1.2);",
    },
    "friendly": {
        "layout":   "hero-center",
        "gradient": (
            "background:linear-gradient(160deg,"
            "oklch(97% 0.01 350) 0%,"
            "oklch(95% 0.015 340) 50%,"
            "oklch(98% 0.005 0) 100%);"
        ),
        "keyframes": "",
        "overlay":  "rgba(0,0,0,0.0)",
        "text_pos": "center",
        "img_style": "object-fit:cover;filter:saturate(0.9) brightness(1.0);border-radius:16px;",
    },
    "warm_editorial": {
        "layout":   "hero-split",
        "gradient": (
            "background:linear-gradient(135deg,"
            "oklch(25% 0.03 50) 0%,"
            "oklch(18% 0.02 40) 100%);"
        ),
        "keyframes": "",
        "overlay":  "rgba(20,10,5,0.45)",
        "text_pos": "left",
        "img_style": "object-fit:cover;filter:saturate(1.05) brightness(0.9);",
    },
}


def get_hero_style(dir_key: str) -> Dict:
    """Retorna o estilo de hero para a direção visual do nicho.

    Args:
        dir_key: Chave da direção visual (ex: 'editorial', 'cafe', 'bold').

    Returns:
        Dict com campos: layout, gradient, keyframes, overlay, text_pos, img_style.
        Inclui 'noise' para brutalism (ativa camada de ruido CSS).
    """
    if dir_key in HERO_STYLES:
        return HERO_STYLES[dir_key]

    # Fallback inteligente baseado na direção visual
    # Lazy import para evitar dependência circular
    import re as _re
    from .design_context import DIRECOES_VISUAIS

    d = DIRECOES_VISUAIS.get(dir_key, {})
    tokens = d.get("tokens", {})
    bg = tokens.get("--bg", "oklch(100% 0.0 0)")

    # Se bg é escuro (lightness < 30%), usar hero dark
    m = _re.search(r"oklch\((\d+)%", bg)
    lightness = int(m.group(1)) if m else 100

    if lightness < 30:
        return {
            "layout":    "hero-fullscreen",
            "gradient":  "background:" + bg + ";",
            "keyframes": "",
            "overlay":   "rgba(0,0,0,0.40)",
            "text_pos":  "center",
            "img_style": "object-fit:cover;filter:contrast(1.1) brightness(0.85);",
        }
    else:
        return {
            "layout":    "hero-center",
            "gradient":  "background:" + bg + ";",
            "keyframes": "",
            "overlay":   "rgba(0,0,0,0.0)",
            "text_pos":  "center",
            "img_style": "object-fit:cover;filter:saturate(0.9) brightness(0.95);",
        }


def get_hero_css(dir_key: str) -> str:
    """Retorna o CSS completo do hero (keyframes + gradient) para injetar no wrapper.

    Args:
        dir_key: Chave da direção visual.

    Returns:
        String com CSS pronto para injeção (inclui @keyframes e regra #hero).
    """
    style = get_hero_style(dir_key)
    css = ""
    if style.get("keyframes"):
        css += style["keyframes"] + "\n"
    css += f"#hero{{min-height:100vh;{style['gradient']}}}" + "\n"
    if style.get("noise"):
        css += (
            "#hero::after{content:'';position:absolute;inset:0;pointer-events:none;"
            "background:repeating-linear-gradient(0deg,transparent,transparent 2px,"
            "rgba(0,0,0,0.03) 2px,rgba(0,0,0,0.03) 4px);"
            "opacity:0.04;animation:hero-noise 3s ease-in-out infinite;}" + "\n"
        )
    return css
