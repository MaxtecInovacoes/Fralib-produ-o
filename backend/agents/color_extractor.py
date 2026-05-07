"""
Color Extractor - Extrai paleta de cores de logo/fotos
Usa ColorThief para análise de cores dominantes
"""

from colorthief import ColorThief
from PIL import Image
import requests
from io import BytesIO
from typing import Dict, List, Tuple, Optional
import colorsys
import os

def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Converte RGB para HEX"""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

def calcular_contraste(cor1: Tuple[int, int, int], cor2: Tuple[int, int, int]) -> float:
    """Calcula contraste WCAG entre duas cores RGB"""
    def luminancia(rgb):
        r, g, b = [x / 255.0 for x in rgb]
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    l1 = luminancia(cor1)
    l2 = luminancia(cor2)

    if l1 > l2:
        return (l1 + 0.05) / (l2 + 0.05)
    else:
        return (l2 + 0.05) / (l1 + 0.05)

def extrair_cores_imagem(url: str, num_cores: int = 5) -> List[Tuple[int, int, int]]:
    # Limpar caracteres de controle e espacos da URL
    url = url.strip().rstrip("\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f")
    """
    Extrai cores dominantes de uma imagem (URL ou arquivo local)
    """
    try:
        if url.startswith('/tmp/') or url.startswith('./') or os.path.exists(url):
            img = Image.open(url)
        else:
            # Limpar URL do Google (remove parametros invalidos tipo .03751-ya359)
            import re as _re_ce
            url = _re_ce.sub(r'(=s[0-9]+)[.][0-9]+.*$', r'', url)
            url = _re_ce.sub(r'[.][0-9]+-[a-z]+[0-9]+.*$', '', url)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))

        if img.mode != 'RGB':
            img = img.convert('RGB')

        temp_path = "/tmp/temp_color_extract.jpg"
        img.save(temp_path)

        color_thief = ColorThief(temp_path)
        cor_dominante = color_thief.get_color(quality=1)

        if num_cores > 1:
            paleta = color_thief.get_palette(color_count=num_cores, quality=1)
            return paleta
        else:
            return [cor_dominante]

    except Exception as e:
        print(f"[Color Extractor] Erro ao extrair cores de {url}: {str(e)}")
        return []

def gerar_paleta_completa(
    logo_url: Optional[str] = None,
    fotos: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Gera paleta de cores completa a partir de logo e fotos
    """
    print(f"\n[Color Extractor] Extraindo cores...")

    cores_extraidas = []

    if logo_url:
        print(f"[Color Extractor] Analisando logo...")
        cores_logo = extrair_cores_imagem(logo_url, num_cores=3)
        if cores_logo:
            cores_extraidas.extend(cores_logo)
            print(f"[Color Extractor] {len(cores_logo)} cores da logo")

    if fotos and len(fotos) > 0:
        print(f"[Color Extractor] Analisando {len(fotos)} fotos...")
        for i, foto_url in enumerate(fotos[:3], 1):
            cores_foto = extrair_cores_imagem(foto_url, num_cores=2)
            if cores_foto:
                cores_extraidas.extend(cores_foto)
                print(f"[Color Extractor] Foto {i}: {len(cores_foto)} cores")

    if not cores_extraidas:
        print(f"[Color Extractor] Nenhuma cor extraida, usando fallback")
        return {
            "primaria": "#4A90E2",
            "secundaria": "#f9fafb",
            "acento": "#e85d04",
            "background": "#ffffff",
            "texto": "#1f2937"
        }

    cores_ordenadas = sorted(
        cores_extraidas,
        key=lambda c: colorsys.rgb_to_hsv(c[0]/255, c[1]/255, c[2]/255)[1],
        reverse=True
    )

    cor_primaria = cores_ordenadas[0]

    contraste = calcular_contraste(cor_primaria, (255, 255, 255))
    if contraste < 3.0:
        print(f"[Color Extractor] Cor primaria ajustada para melhor contraste")
        h, s, v = colorsys.rgb_to_hsv(cor_primaria[0]/255, cor_primaria[1]/255, cor_primaria[2]/255)
        v = max(0.3, v - 0.2)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        cor_primaria = (int(r * 255), int(g * 255), int(b * 255))

    # Acento: segunda cor mais saturada (diferente da primaria)
    cor_acento = None
    for c in cores_ordenadas[1:]:
        h_p, s_p, v_p = colorsys.rgb_to_hsv(cor_primaria[0]/255, cor_primaria[1]/255, cor_primaria[2]/255)
        h_c, s_c, v_c = colorsys.rgb_to_hsv(c[0]/255, c[1]/255, c[2]/255)
        # Escolher cor com matiz diferente (>15 graus) e saturacao razoavel
        if abs(h_p - h_c) > 0.04 and s_c > 0.1:
            cor_acento = c
            break
    if not cor_acento:
        cor_acento = cores_ordenadas[1] if len(cores_ordenadas) > 1 else cor_primaria

    paleta = {
        "primaria": rgb_to_hex(cor_primaria),
        "secundaria": "#f9fafb",
        "acento": rgb_to_hex(cor_acento),
        "background": "#ffffff",
        "texto": "#1f2937"
    }

    print(f"[Color Extractor] Paleta gerada:")
    for nome, cor in paleta.items():
        print(f"   {nome}: {cor}")

    return paleta
