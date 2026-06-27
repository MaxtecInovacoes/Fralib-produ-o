"""SDR Message Formatter - Aplica cores da paleta nas mensagens do WhatsApp.

Este módulo formata mensagens do SDR usando cores consistentes com o site gerado,
criando identidade visual visualmente harmoniosa entre o site e as mensagens.
"""

from typing import Dict, Optional


def format_message_with_colors(message: str, paleta_cores: Dict[str, str]) -> str:
    """
    Formata uma mensagem SDR usando cores da paleta do site.

    Args:
        message: Mensagem original do SDR
        paleta_cores: Dicionário com cores {"primary": "#hex", "secondary": "#hex", "accent": "#hex"}

    Returns:
        Mensagem formatada com emojis coloridos e formatação visual
    """
    if not paleta_cores or not isinstance(paleta_cores, dict):
        return message

    primary = paleta_cores.get("primary", "#374151")
    secondary = paleta_cores.get("secondary", "#f9fafb")
    accent = paleta_cores.get("accent", "#6366f1")

    # Mapear cores para emojis e formatação visual
    color_map = {
        "primary": {
            "emoji": "🔥",  # Fogo para ação principal
            "marker": f"🔥 ",
            "weight": "bold"
        },
        "secondary": {
            "emoji": "✨",  # Brilho para informações secundárias
            "marker": f"✨ ",
            "weight": "normal"
        },
        "accent": {
            "emoji": "💎",  # Diamante para pontos importantes
            "marker": f"💎 ",
            "weight": "bold"
        }
    }

    lines = message.split('\n')
    formatted_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            formatted_lines.append("")
            continue

        # Adicionar marcador de cor baseado no conteúdo
        if any(keyword in line.lower() for keyword in ["agora", "hoje", "vamos", "começar"]):
            formatted_line = f"{color_map['primary']['marker']}{line}"
        elif any(keyword in line.lower() for keyword in ["site", "demonstração", "ver", "mostrar"]):
            formatted_line = f"{color_map['accent']['marker']}{line}"
        elif any(keyword in line.lower() for keyword in ["grátis", "sem custo", "gratuito", "sem compromisso"]):
            formatted_line = f"{color_map['secondary']['marker']}{line}"
        else:
            formatted_line = f"{color_map['secondary']['marker']}{line}"

        formatted_lines.append(formatted_line)

    return "\n".join(formatted_lines)


def get_branding_hint(paleta_cores: Dict[str, str]) -> str:
    """
    Gera uma dica de branding visual para o SDR.

    Args:
        paleta_cores: Dicionário com cores do site

    Returns:
        Dica visual sobre as cores usadas
    """
    if not paleta_cores or not isinstance(paleta_cores, dict):
        return "🎨 *Branding:* Cores padrão do nicho"

    primary = paleta_cores.get("primary", "")
    secondary = paleta_cores.get("secondary", "")
    accent = paleta_cores.get("accent", "")

    colors_info = []
    if primary:
        colors_info.append(f"Primária: {primary}")
    if secondary:
        colors_info.append(f"Secundária: {secondary}")
    if accent:
        colors_info.append(f"Acento: {accent}")

    if colors_info:
        return f"🎨 *Branding:* {', '.join(colors_info)}"
    return "🎨 *Branding:* Cores padrão do nicho"


def validate_color_palette(paleta_cores: Dict[str, str]) -> Dict[str, str]:
    """
    Valida e normaliza a paleta de cores.

    Args:
        paleta_cores: Paleta bruta do formulário

    Returns:
        Paleta validada e normalizada
    """
    if not paleta_cores:
        return {}

    normalized = {}

    # Valida formato hexadecimal
    def is_valid_hex(color: str) -> bool:
        if not color or not isinstance(color, str):
            return False
        if color.startswith('#'):
            return len(color) == 7 and all(c in '0123456789abcdefABCDEF' for c in color[1:])
        return False

    # Mapeia chaves para normalizar
    key_mapping = {
        "primary": "primary",
        "primaria": "primary",
        "main": "primary",
        "principal": "primary",
        "secondary": "secondary",
        "secundaria": "secondary",
        "background": "secondary",
        "accent": "accent",
        "acento": "accent",
        "highlight": "accent",
        "destaque": "accent"
    }

    for key, value in paleta_cores.items():
        if key in key_mapping and value and is_valid_hex(value):
            normalized[key_mapping[key]] = value

    return normalized