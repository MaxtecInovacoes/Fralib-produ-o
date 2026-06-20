"""
Pexels Video Fetcher — busca vídeos de fundo por nicho.
Usa PEXELS_API_KEY do .env.
Cache por negócio (segmento+nome+cidade) — cada cliente tem vídeos únicos.
Rate limit: 200 req/hora no plano free.
"""

import os
import json
import time
import hashlib
import random
import requests

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pexels_cache")
CACHE_TTL = 7 * 24 * 3600  # 7 dias

QUERIES_NICHO = {
    "nutricionista": "healthy food preparation",
    "academia": "gym workout fitness",
    "crossfit": "crossfit training athlete",
    "barbearia": "barbershop haircut",
    "salao": "hair salon beauty",
    "salao_beleza": "hair salon beauty",
    "clinica": "medical clinic health",
    "dentista": "dental clinic",
    "odontologia": "dental clinic",
    "estetica": "beauty spa treatment",
    "restaurante": "restaurant food cooking",
    "churrascaria": "steakhouse grill fire",
    "lanchonete": "burger food fast",
    "padaria": "bakery bread artisan",
    "confeitaria": "cake dessert pastry",
    "cafe": "coffee cafe barista",
    "advocacia": "law office professional",
    "imobiliaria": "real estate house",
    "escola": "school education",
    "farmacia": "pharmacy health",
    "pet_shop": "pet dog cat",
    "pet": "pet dog cat",
    "auto_pecas": "car mechanic garage",
    "psicologia": "therapy wellness calm",
    "arquitetura": "architecture interior design",
    "fotografia": "photography studio",
    "personal": "personal trainer fitness",
    "pilates": "pilates yoga wellness",
    "fisioterapia": "physiotherapy rehabilitation",
    "pizzaria": "pizza italian cooking",
    "contabilidade": "business office finance",
    "loja_roupas": "fashion clothing store",
    "floricultura": "flowers florist arrangement",
    "mecanica": "car repair mechanic",
    "lavanderia": "laundry clean clothes",
}

FALLBACK_QUERY = "business professional"


def _cache_key(segmento: str, nome: str = "", cidade: str = "") -> str:
    raw = f"{segmento.lower()}|{nome.lower()}|{cidade.lower()}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _get_cache(key: str) -> list | None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"pexels_{key}.json")
    if not os.path.exists(path):
        return None
    if time.time() - os.path.getmtime(path) > CACHE_TTL:
        os.remove(path)
        return None
    with open(path, "r") as f:
        return json.load(f)


def _set_cache(key: str, data: list):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"pexels_{key}.json")
    with open(path, "w") as f:
        json.dump(data, f)


def buscar_videos_pexels(
    segmento: str,
    quantidade: int = 3,
    nome: str = "",
    cidade: str = "",
    orientacao: str = "landscape",
    min_duracao: int = 5,
    max_duracao: int = 30,
) -> list[dict]:
    """
    Busca vídeos no Pexels por nicho.
    Retorna lista de dicts: {url, width, height, duration, thumbnail, quality}
    """
    if not PEXELS_API_KEY:
        return []

    key = _cache_key(segmento, nome, cidade)
    cached = _get_cache(key)
    if cached:
        random.shuffle(cached)
        return cached[:quantidade]

    query = QUERIES_NICHO.get(segmento.lower(), FALLBACK_QUERY)
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "per_page": min(quantidade * 3, 15),
        "orientation": orientacao,
        "size": "medium",
    }

    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    videos = []
    for item in data.get("videos", []):
        duracao = item.get("duration", 0)
        if duracao < min_duracao or duracao > max_duracao:
            continue

        best_file = None
        for vf in item.get("video_files", []):
            if vf.get("quality") == "hd" and vf.get("width", 0) >= 1280:
                best_file = vf
                break
        if not best_file:
            for vf in item.get("video_files", []):
                if vf.get("quality") == "sd" and vf.get("width", 0) >= 640:
                    best_file = vf
                    break
        if not best_file and item.get("video_files"):
            best_file = item["video_files"][0]

        if not best_file:
            continue

        thumbnail = ""
        for pic in item.get("video_pictures", []):
            if pic.get("picture"):
                thumbnail = pic["picture"]
                break

        videos.append(
            {
                "url": best_file["link"],
                "width": best_file.get("width", 0),
                "height": best_file.get("height", 0),
                "duration": duracao,
                "thumbnail": thumbnail,
                "quality": best_file.get("quality", "sd"),
                "pexels_id": item.get("id"),
            }
        )

    if videos:
        _set_cache(key, videos)

    random.shuffle(videos)
    return videos[:quantidade]
