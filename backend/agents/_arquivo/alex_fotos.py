import os
import sys
sys.path.insert(0, "/root/fralib/backend/agents")
"""
Alex - Processamento de fotos: WebP, upscale, redimensionar, thumbnail
"""
import requests
from PIL import Image
import io
from typing import List, Dict
from pathlib import Path


def obter_dimensoes(url: str) -> Dict[str, int]:
    """Obtém largura e altura da imagem"""
    from alex_logo import limpar_url_google
    try:
        url = limpar_url_google(url)
        response = requests.get(url, timeout=10)
        img = Image.open(io.BytesIO(response.content))
        return {"width": img.width, "height": img.height}
    except:
        return {"width": 800, "height": 600}


def upscale_foto(foto_url: str) -> str:
    """Aumenta resolucao usando Real-ESRGAN (TODO: Replicate API)"""
    print("[ALEX] Upscaling foto de baixa resolucao...")
    return foto_url


def redimensionar_foto(foto_url: str, max_width: int) -> str:
    """Redimensiona foto mantendo aspect ratio"""
    try:
        foto_url = limpar_url_google(foto_url)
        response = requests.get(foto_url, timeout=10)
        img = Image.open(io.BytesIO(response.content))

        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)

        output_path = f"/tmp/foto_resized_{hash(foto_url)}.jpg"
        img.save(output_path, quality=90)
        return output_path

    except Exception as e:
        print(f"[ALEX] Erro ao redimensionar: {e}")
        return foto_url


def converter_para_webp(imagem_path: str, qualidade: int = 85, assets_dir: str = "", filename: str = "") -> str:
    """Converte imagem para WebP"""
    try:
        if imagem_path.startswith("http"):
            imagem_path = limpar_url_google(imagem_path)
            response = requests.get(imagem_path, timeout=10)
            img = Image.open(io.BytesIO(response.content))
        else:
            img = Image.open(imagem_path)

        if assets_dir and assets_dir != "/tmp" and filename:
            os.makedirs(assets_dir, exist_ok=True)
            output_path = assets_dir + "/" + filename
        elif assets_dir and assets_dir != "/tmp":
            os.makedirs(assets_dir, exist_ok=True)
            output_path = assets_dir + "/" + str(abs(hash(imagem_path))) + ".webp"
        elif imagem_path.startswith("http"):
            output_path = f"/tmp/{abs(hash(imagem_path))}.webp"
        else:
            output_path = imagem_path.replace(".jpg", ".webp").replace(".png", ".webp")
            if output_path == imagem_path:
                output_path = f"/tmp/{abs(hash(imagem_path))}.webp"

        img.save(output_path, format="WEBP", quality=qualidade)
        return output_path

    except Exception as e:
        print(f"[ALEX] Erro ao converter WebP: {e}")
        return imagem_path


def gerar_thumbnail(imagem_path: str, width: int = 400, assets_dir: str = "", filename: str = "") -> str:
    """Gera thumbnail da imagem"""
    try:
        if imagem_path.startswith("http"):
            imagem_path = limpar_url_google(imagem_path)
            response = requests.get(imagem_path, timeout=10)
            img = Image.open(io.BytesIO(response.content))
        else:
            img = Image.open(imagem_path)

        ratio = width / img.width
        height = int(img.height * ratio)
        img = img.resize((width, height), Image.LANCZOS)

        if assets_dir and assets_dir != "/tmp" and filename:
            os.makedirs(assets_dir, exist_ok=True)
            output_path = assets_dir + "/" + filename
        elif assets_dir and assets_dir != "/tmp":
            os.makedirs(assets_dir, exist_ok=True)
            output_path = assets_dir + "/" + str(abs(hash(imagem_path))) + "_thumb.webp"
        elif imagem_path.startswith("http"):
            output_path = f"/tmp/{abs(hash(imagem_path))}_thumb.webp"
        else:
            output_path = imagem_path.replace(".webp", "_thumb.webp")
            if not output_path.endswith("_thumb.webp"):
                output_path = f"/tmp/{abs(hash(imagem_path))}_thumb.webp"

        img.save(output_path, format="WEBP", quality=80)
        return output_path

    except Exception as e:
        print(f"[ALEX] Erro ao gerar thumbnail: {e}")
        return imagem_path


def processar_fotos(fotos: List[str], assets_dir: str = "/tmp") -> Dict:
    """Processa fotos: upscale, WebP, thumbnails"""
    fotos_webp = []
    qualidade = {"baixa": [], "media": [], "alta": []}
    total_upscaled = 0

    for foto_url in fotos:
        foto_url = limpar_url_google(foto_url)
        dimensoes = obter_dimensoes(foto_url)
        largura = dimensoes["width"]

        if largura < 800:
            qualidade["baixa"].append(foto_url)
            foto_processada = upscale_foto(foto_url)
            total_upscaled += 1
        elif largura < 1200:
            qualidade["media"].append(foto_url)
            foto_processada = foto_url
        else:
            qualidade["alta"].append(foto_url)
            foto_processada = redimensionar_foto(foto_url, max_width=1920)

        foto_webp = converter_para_webp(foto_processada, qualidade=85)
        if assets_dir and assets_dir != "/tmp" and foto_webp and os.path.exists(foto_webp):
            import shutil
            dest = assets_dir + "/foto_" + str(len(fotos_webp)+1) + ".webp"
            shutil.copy2(foto_webp, dest)
            foto_webp = dest

        thumb_filename = "thumb_" + str(len(fotos_webp)+1) + ".webp"
        thumbnail = gerar_thumbnail(foto_processada, width=400, assets_dir=assets_dir, filename=thumb_filename)

        fotos_webp.append({
            "original": foto_url,
            "webp": foto_webp,
            "thumbnail": thumbnail,
            "dimensoes": dimensoes
        })

    return {
        "fotos_webp": fotos_webp,
        "qualidade": qualidade,
        "total_upscaled": total_upscaled
    }


def obter_tamanho_arquivo(path: str) -> int:
    """Obtém tamanho do arquivo em bytes"""
    try:
        if path.startswith("http"):
            response = requests.head(path, timeout=5)
            return int(response.headers.get("Content-Length", 0))
        else:
            return Path(path).stat().st_size
    except:
        return 0


def baixar_imagem_seguro(url: str, dest_path: str) -> str:
    """Baixa imagem de URL externa e salva localmente"""
    try:
        response = requests.get(url, timeout=10)
        img = Image.open(io.BytesIO(response.content))
        img.save(dest_path, format="WebP", quality=85)
        print(f"[Alex] Imagem baixada: {url[:50]}... -> {dest_path}")
        return dest_path
    except Exception as e:
        print(f"[Alex] Erro ao baixar imagem: {e}")
        return url
