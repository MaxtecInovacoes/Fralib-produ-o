import os
import sys
sys.path.insert(0, "/root/fralib/backend/agents")
"""
alex_cores.py - Extração de paleta via Colorthief + filtro HSV (zero LLM).
Busca de fotos premium via Unsplash API (sem pessoas).
"""
import requests
import colorsys
from PIL import Image
import io
from typing import List, Dict

UNSPLASH_ACCESS_KEY = "UHSOjHTUALqtfLxYwzrO7WYPe9HHG8zeCC4sVbwLErU"
UNSPLASH_API = "https://api.unsplash.com"

# Termos de exclusão de pessoas por segmento
SEGMENT_QUERIES = {
    "academia": "gym equipment weights interior architecture",
    "crossfit": "crossfit gym equipment barbell architecture",
    "barbearia": "barbershop interior chairs tools architecture",
    "advocacia": "law office interior architecture books",
    "clinica": "clinic interior architecture medical",
    "estetica": "beauty salon interior architecture",
    "doceria": "bakery pastry food architecture interior",
    "restaurante": "restaurant interior architecture food",
    "default": "business interior architecture premium",
}


def rgb_para_hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])


def _is_neutral(rgb) -> bool:
    """Retorna True se a cor é neutra (branco, cinza, preto)."""
    r, g, b = rgb[0] / 255, rgb[1] / 255, rgb[2] / 255
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return s < 0.15 or v > 0.93 or v < 0.10


def _saturacao_vibrancia(rgb) -> float:
    r, g, b = rgb[0] / 255, rgb[1] / 255, rgb[2] / 255
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return s * v


def extrair_paleta(logo_path: str) -> Dict[str, str]:
    """Extrai paleta via Colorthief com filtro HSV. Zero LLM."""
    from alex_logo import limpar_url_google
    PAD = {
        "primaria": "#2C3E50", "secundaria": "#34495E",
        "acento": "#E74C3C", "complementar_1": "#ECF0F1", "complementar_2": "#95A5A6",
    }
    try:
        from colorthief import ColorThief
        if "placeholder" in logo_path.lower():
            return PAD
        if logo_path.startswith("http"):
            logo_path = limpar_url_google(logo_path)
            r = requests.get(logo_path, timeout=10, verify=False)
            img = Image.open(io.BytesIO(r.content))
            tp = "/tmp/lfc_{}.png".format(abs(hash(logo_path)))
            img.save(tp)
            logo_path = tp

        ct = ColorThief(logo_path)
        pal = ct.get_palette(color_count=10, quality=1)

        vibrantes = [c for c in pal if not _is_neutral(c)]
        neutras = [c for c in pal if _is_neutral(c)]
        vibrantes.sort(key=_saturacao_vibrancia, reverse=True)
        t = vibrantes + neutras
        if len(t) < 5:
            t += [pal[0]] * (5 - len(t))

        return {
            "primaria": rgb_para_hex(t[0]),
            "secundaria": rgb_para_hex(t[1]) if len(t) > 1 else "#f9fafb",
            "acento": rgb_para_hex(t[2]) if len(t) > 2 else "#e85d04",
            "complementar_1": rgb_para_hex(t[3]) if len(t) > 3 else "#e5e7eb",
            "complementar_2": rgb_para_hex(t[4]) if len(t) > 4 else "#d1d5db",
        }
    except Exception as e:
        print("[Alex] Erro paleta: {}".format(e))
        return PAD


def buscar_fotos_unsplash(segmento: str, count: int = 6) -> List[str]:
    """
    Busca fotos premium no Unsplash sem pessoas.
    Retorna lista de URLs das fotos.
    """
    seg_lower = segmento.lower().strip()
    query = None
    for key in SEGMENT_QUERIES:
        if key in seg_lower:
            query = SEGMENT_QUERIES[key]
            break
    if not query:
        query = SEGMENT_QUERIES["default"]

    # Adicionar termos anti-pessoas
    query_final = query + " no people no faces architecture"

    try:
        resp = requests.get(
            "{}/search/photos".format(UNSPLASH_API),
            headers={"Authorization": "Client-ID {}".format(UNSPLASH_ACCESS_KEY)},
            params={
                "query": query_final,
                "per_page": count,
                "orientation": "landscape",
                "content_filter": "high",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        urls = []
        for photo in data.get("results", []):
            url = photo.get("urls", {}).get("regular", "")
            if url:
                urls.append(url)
        print("[Alex] Unsplash: {} fotos premium para segmento '{}'".format(len(urls), segmento))
        return urls
    except Exception as e:
        print("[Alex] Unsplash falhou: {}".format(e))
        return []


def calcular_economia(fotos_originais, fotos_processadas) -> Dict:
    from alex_fotos import obter_tamanho_arquivo
    try:
        so = sum(obter_tamanho_arquivo(u) for u in fotos_originais)
        st = sum(
            obter_tamanho_arquivo(f["webp"]) + obter_tamanho_arquivo(f["thumbnail"])
            for f in fotos_processadas
        )
        ep = ((so - st) / so) * 100 if so else 0
        return {"original_mb": so / 1048576, "otimizado_mb": st / 1048576, "economia_percentual": ep}
    except Exception as e:
        print("[ALEX] Erro economia: {}".format(e))
        return {"original_mb": 0, "otimizado_mb": 0, "economia_percentual": 0}


def classificar_fotos_por_tipo(fotos_webp, segmento) -> Dict:
    """Classifica fotos por tipo usando Claude Vision (mantido - e classificacao, nao logica)."""
    if not fotos_webp:
        return {}
    res = {
        "fachada": [], "ambiente_interno": [], "equipamento": [],
        "equipe": [], "produto": [], "outro": [],
    }
    ent = []
    for f in fotos_webp[:9]:
        w = f.get("webp", "")
        o = f.get("original", "")
        lp = w if w and w.startswith("/var/www/") else None
        url = (
            w if w.startswith("http")
            else (w.replace("/var/www/fralib/sites/", "https://seunegociofralib.site/sites/") if w.startswith("/var/www/") else o)
        )
        ent.append({"local": lp, "url": url})
    if not ent:
        return res
    try:
        import base64 as b64
        import re
        from llm_direct import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL
        cp = []
        iv = []
        for i, e in enumerate(ent):
            if e["local"] and os.path.exists(e["local"]):
                d = b64.b64encode(open(e["local"], "rb").read()).decode()
                cp.append({"type": "image", "source": {"type": "base64", "media_type": "image/webp", "data": d}})
                cp.append({"type": "text", "text": "[Foto {}]".format(i + 1)})
                iv.append(i)
            elif e["url"] and e["url"].startswith("http"):
                cp.append({"type": "image", "source": {"type": "url", "url": e["url"]}})
                cp.append({"type": "text", "text": "[Foto {}]".format(i + 1)})
                iv.append(i)
        if not iv:
            raise Exception("Nenhuma imagem carregada")
        cp.append({"type": "text", "text": "Classifique fotos de {}. Formato: 1:fachada 2:ambiente_interno. Tipos: fachada|ambiente_interno|equipamento|equipe|produto|outro. Responda APENAS nesse formato.".format(segmento)})
        ua = ANTHROPIC_BASE_URL + "/v1/messages"
        hd = {"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        pl = {
            "model": "claude-sonnet-4-6", "max_tokens": 200, "temperature": 0.0,
            "system": "Classifica fotos. Responda apenas: 1:tipo 2:tipo etc.",
            "messages": [{"role": "user", "content": cp}],
        }
        r = requests.post(ua, headers=hd, json=pl, timeout=60)
        r.raise_for_status()
        data = r.json()
        resp = next((b["text"].strip() for b in data.get("content", []) if b.get("type") == "text"), "")
        for m in re.finditer(r"(\d+):(\w+)", resp):
            seq = int(m.group(1)) - 1
            tipo = m.group(2).lower()
            if 0 <= seq < len(iv):
                ir = iv[seq]
                uf = ent[ir]["url"] or ent[ir]["local"] or ""
                if tipo in res and uf:
                    res[tipo].append(uf)
        if not any(res.values()):
            raise Exception("Nenhuma foto classificada: {}".format(resp[:80]))
        return res
    except Exception as e:
        print("[ALEX] Classificacao falhou: {}".format(e))
        raise
