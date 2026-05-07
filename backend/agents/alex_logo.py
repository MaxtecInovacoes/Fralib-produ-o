import os
import sys
sys.path.insert(0, "/root/fralib/backend/agents")
"""
Alex - Processamento de logo: remover fundo, vetorizar, limpar URL
"""
import requests
from PIL import Image
import io
from typing import Optional


def limpar_url_google(url: str) -> str:
    """Remove parametros invalidos de URLs do Google (lh3.googleusercontent.com)"""
    import re as _re_url
    from urllib.parse import unquote as _unquote
    if not url:
        return url
    url_decoded = _unquote(url)
    ctrl_idx = -1
    for i, c in enumerate(url_decoded):
        if ord(c) < 32:
            ctrl_idx = i
            break
    if ctrl_idx > 0:
        url_decoded = url_decoded[:ctrl_idx]
    url_decoded = _re_url.sub(r"(=s[0-9]+)[^a-zA-Z0-9_-].*$", r"", url_decoded)
    url_decoded = _re_url.sub(r"[.][0-9]+-[a-z]+[0-9]+.*$", "", url_decoded)
    return url_decoded


def remover_fundo(logo_url: str) -> str:
    """Remove fundo da logo usando rembg"""
    try:
        logo_url = limpar_url_google(logo_url)
        response = requests.get(logo_url, timeout=10)
        img = Image.open(io.BytesIO(response.content))

        try:
            from rembg import remove
            output = remove(img)
            output_path = f"/tmp/logo_transparent_{hash(logo_url)}.png"
            output.save(output_path)
            return output_path
        except ImportError:
            print("[ALEX] rembg nao instalado, usando logo original")
            output_path = f"/tmp/logo_original_{hash(logo_url)}.png"
            img.save(output_path)
            return output_path

    except Exception as e:
        print(f"[ALEX] Erro ao processar logo: {e}")
        return logo_url


def vetorizar_logo(logo_png: str, assets_dir: str = "/tmp") -> Optional[str]:
    """Tenta vetorizar logo para SVG usando VTracer"""
    try:
        import vtracer

        output_svg = logo_png.replace(".png", ".svg")

        with open(logo_png, "rb") as f:
            img_bytes = f.read()

        svg_str = vtracer.convert_raw_image_to_svg(
            img_bytes,
            img_format="png",
            colormode="color",
            hierarchical="stacked"
        )

        with open(output_svg, "w", encoding="utf-8") as f:
            f.write(svg_str)

        print(f"[ALEX] Logo vetorizado: {output_svg}")

        with open(output_svg, "r", encoding="utf-8") as svg_f:
            svg_content = svg_f.read()
        path_count = svg_content.count("<path")
        if path_count > 80:
            print(f"[ALEX] SVG muito complexo ({path_count} paths) — usando fallback")
            return None

        if assets_dir and assets_dir != "/tmp":
            import shutil
            dest_svg = assets_dir + "/logo.svg"
            shutil.copy2(output_svg, dest_svg)
            output_svg = dest_svg
        return output_svg

    except ImportError:
        print("[ALEX] vtracer nao disponivel, pulando vetorizacao")
        return None
    except Exception as e:
        print(f"[ALEX] Nao foi possivel vetorizar: {e}")
        return None


def processar_logo(logo_url: Optional[str], assets_dir: str = "/tmp") -> dict:
    """Processa logo: remove fundo, vetoriza, gera formatos"""
    from alex_fotos import converter_para_webp

    if not logo_url:
        return {
            "logo_svg": None,
            "logo_webp": "https://via.placeholder.com/512",
            "logo_png": "https://via.placeholder.com/512",
            "logo_original": "https://via.placeholder.com/512"
        }

    logo_url = limpar_url_google(logo_url)
    print("[Alex] Logo URL limpa: " + logo_url[:80])

    logo_sem_fundo = remover_fundo(logo_url)
    logo_svg = vetorizar_logo(logo_sem_fundo, assets_dir=assets_dir)

    if not logo_svg:
        try:
            nome_negocio = assets_dir.split("/")[-2].replace("-", " ").title() if assets_dir else "N"
            inicial = nome_negocio[0].upper() if nome_negocio else "N"
            fallback_svg = (
                "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200' width='200' height='200'>"
                "<rect width='200' height='200' rx='20' fill='#1a1a2e'/>"
                f"<text x='100' y='130' font-size='100' text-anchor='middle' fill='#e94560' "
                f"font-family='Arial, sans-serif' font-weight='bold'>{inicial}</text>"
                "</svg>"
            )
            fallback_path = (
                assets_dir + "/logo.svg"
                if assets_dir and assets_dir != "/tmp"
                else "/tmp/logo_fallback.svg"
            )
            with open(fallback_path, "w", encoding="utf-8") as f_svg:
                f_svg.write(fallback_svg)
            logo_svg = fallback_path
            print(f"[ALEX] Logo fallback SVG gerado: {fallback_path}")
        except Exception as e:
            print(f"[ALEX] Erro ao gerar fallback SVG: {e}")

    logo_webp = converter_para_webp(logo_sem_fundo, qualidade=90, assets_dir=assets_dir, filename="logo.webp")

    return {
        "logo_svg": logo_svg,
        "logo_webp": logo_webp,
        "logo_png": logo_sem_fundo,
        "logo_original": logo_url
    }
