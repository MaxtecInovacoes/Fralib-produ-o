"""
Paleta por nicho com variacoes — garante que sites do mesmo nicho
nao saiam com cores identicas.
"""

PALETAS_NICHO = {
    "nutricionista": [
        {"primary": "#2d6a4f", "accent": "#74c69d", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#1b4332", "accent": "#52b788", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#40916c", "accent": "#b7e4c7", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#081c15", "accent": "#95d5b2", "background": "#0a0a0a", "text": "#f1f5f9"},
    ],
    "academia": [
        {"primary": "#1a1a2e", "accent": "#e94560", "background": "#0f0f1a", "text": "#f1f5f9"},
        {"primary": "#16213e", "accent": "#f5a623", "background": "#0d0d1a", "text": "#f1f5f9"},
        {"primary": "#0f3460", "accent": "#e94560", "background": "#0a0a1a", "text": "#f1f5f9"},
        {"primary": "#1a1a1a", "accent": "#00d4ff", "background": "#111111", "text": "#f1f5f9"},
    ],
    "crossfit": [
        {"primary": "#1a1a1a", "accent": "#ff4500", "background": "#0d0d0d", "text": "#f1f5f9"},
        {"primary": "#111111", "accent": "#ffd700", "background": "#0a0a0a", "text": "#f1f5f9"},
        {"primary": "#1c1c1c", "accent": "#00ff88", "background": "#111111", "text": "#f1f5f9"},
        {"primary": "#0d0d0d", "accent": "#ff6b35", "background": "#080808", "text": "#f1f5f9"},
    ],
    "barbearia": [
        {"primary": "#1a1a1a", "accent": "#c9a84c", "background": "#111111", "text": "#f1f5f9"},
        {"primary": "#2c1810", "accent": "#d4a853", "background": "#1a0f0a", "text": "#f1f5f9"},
        {"primary": "#0d0d0d", "accent": "#8b7355", "background": "#080808", "text": "#f1f5f9"},
        {"primary": "#1c1c1c", "accent": "#e8c97e", "background": "#111111", "text": "#f1f5f9"},
    ],
    "salao": [
        {"primary": "#4a0e2e", "accent": "#e91e8c", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#2d1b33", "accent": "#c77dff", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#1a0a1a", "accent": "#ff69b4", "background": "#fff5f9", "text": "#1a1a1a"},
        {"primary": "#3d0c2e", "accent": "#f72585", "background": "#ffffff", "text": "#1a1a1a"},
    ],
    "clinica": [
        {"primary": "#0077b6", "accent": "#00b4d8", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#023e8a", "accent": "#48cae4", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#03045e", "accent": "#90e0ef", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#0096c7", "accent": "#ade8f4", "background": "#ffffff", "text": "#1a1a1a"},
    ],
    "dentista": [
        {"primary": "#0077b6", "accent": "#00b4d8", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#1d3557", "accent": "#457b9d", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#023e8a", "accent": "#48cae4", "background": "#f0f8ff", "text": "#1a1a1a"},
        {"primary": "#0096c7", "accent": "#caf0f8", "background": "#ffffff", "text": "#1a1a1a"},
    ],
    "restaurante": [
        {"primary": "#7b2d00", "accent": "#e85d04", "background": "#1a0a00", "text": "#f1f5f9"},
        {"primary": "#6a0572", "accent": "#e040fb", "background": "#1a001a", "text": "#f1f5f9"},
        {"primary": "#1a0a00", "accent": "#ff6b35", "background": "#0d0500", "text": "#f1f5f9"},
        {"primary": "#2d0a00", "accent": "#ff9500", "background": "#1a0500", "text": "#f1f5f9"},
    ],
    "lanchonete": [
        {"primary": "#c1121f", "accent": "#ffd60a", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#e63946", "accent": "#f4a261", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#d62828", "accent": "#fcbf49", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#9d0208", "accent": "#f48c06", "background": "#ffffff", "text": "#1a1a1a"},
    ],
    "padaria": [
        {"primary": "#7b4f2e", "accent": "#e8a87c", "background": "#fdf6ec", "text": "#1a1a1a"},
        {"primary": "#5c3317", "accent": "#d4956a", "background": "#fff8f0", "text": "#1a1a1a"},
        {"primary": "#8b5e3c", "accent": "#f0c080", "background": "#fef9f0", "text": "#1a1a1a"},
        {"primary": "#4a2c17", "accent": "#c8874a", "background": "#fdf5e6", "text": "#1a1a1a"},
    ],
    "estetica": [
        {"primary": "#4a0e2e", "accent": "#e91e8c", "background": "#fff5f9", "text": "#1a1a1a"},
        {"primary": "#2d1b33", "accent": "#c77dff", "background": "#faf5ff", "text": "#1a1a1a"},
        {"primary": "#1a0a1a", "accent": "#ff69b4", "background": "#fff0f5", "text": "#1a1a1a"},
        {"primary": "#3d0c2e", "accent": "#f72585", "background": "#fff5f9", "text": "#1a1a1a"},
    ],
    "advocacia": [
        {"primary": "#1a1a2e", "accent": "#c9a84c", "background": "#0f0f1a", "text": "#f1f5f9"},
        {"primary": "#0d1b2a", "accent": "#d4a853", "background": "#080f18", "text": "#f1f5f9"},
        {"primary": "#1c2541", "accent": "#e8c97e", "background": "#111827", "text": "#f1f5f9"},
        {"primary": "#0a0a1a", "accent": "#b8960c", "background": "#050510", "text": "#f1f5f9"},
    ],
    "psicologia": [
        {"primary": "#4a4e69", "accent": "#9a8c98", "background": "#f2e9e4", "text": "#22223b"},
        {"primary": "#22223b", "accent": "#c9ada7", "background": "#f2e9e4", "text": "#22223b"},
        {"primary": "#3d405b", "accent": "#81b29a", "background": "#f4f1de", "text": "#1a1a1a"},
        {"primary": "#264653", "accent": "#2a9d8f", "background": "#f8f9fa", "text": "#1a1a1a"},
    ],
    "cafe": [
        {"primary": "#3e1f00", "accent": "#c8874a", "background": "#1a0d00", "text": "#f1f5f9"},
        {"primary": "#2c1503", "accent": "#d4956a", "background": "#150a00", "text": "#f1f5f9"},
        {"primary": "#4a2c17", "accent": "#e8a87c", "background": "#1a0f05", "text": "#f1f5f9"},
        {"primary": "#1a0a00", "accent": "#f0c080", "background": "#0d0500", "text": "#f1f5f9"},
    ],
    "pet": [
        {"primary": "#2d6a4f", "accent": "#74c69d", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#1b4332", "accent": "#52b788", "background": "#f0fff4", "text": "#1a1a1a"},
        {"primary": "#0077b6", "accent": "#48cae4", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#023e8a", "accent": "#90e0ef", "background": "#f0f8ff", "text": "#1a1a1a"},
    ],
    "imobiliaria": [
        {"primary": "#1a1a2e", "accent": "#c9a84c", "background": "#0f0f1a", "text": "#f1f5f9"},
        {"primary": "#0d1b2a", "accent": "#d4a853", "background": "#080f18", "text": "#f1f5f9"},
        {"primary": "#1c2541", "accent": "#e8c97e", "background": "#111827", "text": "#f1f5f9"},
        {"primary": "#0a1628", "accent": "#f0c040", "background": "#050d1a", "text": "#f1f5f9"},
    ],
    "default": [
        {"primary": "#1a1a2e", "accent": "#6366f1", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#0f172a", "accent": "#8b5cf6", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#1e293b", "accent": "#06b6d4", "background": "#ffffff", "text": "#1a1a1a"},
        {"primary": "#111827", "accent": "#10b981", "background": "#ffffff", "text": "#1a1a1a"},
    ],
}


def get_paleta_nicho(segmento: str, variacao_usada: list = None) -> dict:
    seg = segmento.lower().strip()
    paletas = None
    for key in PALETAS_NICHO:
        if key in seg:
            paletas = PALETAS_NICHO[key]
            break
    if not paletas:
        paletas = PALETAS_NICHO["default"]
    variacao_usada = variacao_usada or []
    for idx in range(len(paletas)):
        if idx not in variacao_usada:
            paleta = dict(paletas[idx])
            paleta["variacao_idx"] = idx
            return paleta
    paleta = dict(paletas[0])
    paleta["variacao_idx"] = 0
    return paleta
