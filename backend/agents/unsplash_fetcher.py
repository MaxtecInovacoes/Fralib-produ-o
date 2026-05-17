"""
Unsplash Fetcher — busca fotos de alta qualidade por nicho.
Usa UNSPLASH_ACCESS_KEY do .env.
Cache por negócio (segmento+nome+cidade) — cada cliente tem fotos únicas.
Rate limit: 50 req/hora no plano free.
"""
import os
import json
import time
import hashlib
import random
import requests

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
CACHE_DIR = "/root/fralib/backend/agents/unsplash_cache"
CACHE_TTL = 7 * 24 * 3600  # 7 dias por negócio

# Queries base por nicho — termos em inglês convertem melhor no Unsplash
QUERIES_NICHO = {
    "nutricionista":  "nutritionist healthy food meal prep",
    "academia":       "gym fitness workout training",
    "crossfit":       "crossfit workout athlete training",
    "barbearia":      "barbershop haircut grooming men",
    "salao":          "hair salon beauty hairstyle",
    "salao_beleza":   "hair salon beauty hairstyle",
    "clinica":        "medical clinic doctor health",
    "dentista":       "dentist dental clinic smile",
    "odontologia":    "dentist dental clinic smile",
    "estetica":       "beauty spa aesthetic treatment",
    "restaurante":    "restaurant food dining gourmet",
    "churrascaria":   "steakhouse barbecue grilled meat fire",
    "lanchonete":     "burger sandwich food snack",
    "padaria":        "bakery bread pastry artisan",
    "confeitaria":    "cake pastry dessert sweet",
    "cafe":           "coffee cafe espresso barista",
    "advocacia":      "law office lawyer professional",
    "imobiliaria":    "real estate house property",
    "escola":         "school education classroom learning",
    "farmacia":       "pharmacy medicine health",
    "pet_shop":       "pet dog cat veterinary",
    "pet":            "pet dog cat veterinary",
    "auto_pecas":     "car mechanic garage automotive",
    "psicologia":     "psychology therapy mental health",
    "arquitetura":    "architecture interior design modern",
    "fotografia":     "photography studio camera portrait",
    "personal":       "personal trainer fitness coaching",
    "pilates":        "pilates yoga studio wellness",
    "fisioterapia":   "physiotherapy rehabilitation therapy",
    "pizzaria":       "pizza italian food restaurant",
    "contabilidade":  "accounting office business finance",
}

# Modificadores de contexto por cidade — enriquecem a query sem mudar o nicho
# Tornam as fotos mais específicas ao contexto geográfico/cultural
CITY_MODIFIERS = {
    "são paulo": "urban modern city",
    "rio de janeiro": "tropical vibrant coastal",
    "belo horizonte": "cozy traditional warm",
    "curitiba": "modern clean contemporary",
    "porto alegre": "european style traditional",
    "salvador": "colorful vibrant cultural",
    "recife": "tropical coastal warm",
    "fortaleza": "sunny coastal bright",
    "manaus": "tropical lush green",
    "brasilia": "modern architectural clean",
}


def _get_query_base(segmento: str) -> str:
    seg = segmento.lower().strip().replace("-", "_").replace(" ", "_")
    for key, q in QUERIES_NICHO.items():
        if key in seg or seg in key:
            return q
    return seg.replace("_", " ") + " professional business"


def _get_city_modifier(cidade: str) -> str:
    if not cidade:
        return ""
    cidade_lower = cidade.lower().strip()
    for city, mod in CITY_MODIFIERS.items():
        if city in cidade_lower or cidade_lower in city:
            return mod
    return ""


def _build_query(segmento: str, cidade: str = "", nome: str = "") -> str:
    """Monta query enriquecida com contexto do negócio para fotos únicas."""
    base = _get_query_base(segmento)
    city_mod = _get_city_modifier(cidade)
    # Combinar base + modificador de cidade para diversidade geográfica
    if city_mod:
        return f"{base} {city_mod}"
    return base


def _cache_key(segmento: str, nome: str = "", cidade: str = "") -> str:
    """Cache key única por negócio — cada cliente tem seu próprio conjunto de fotos."""
    raw = f"{segmento.lower()}|{nome.lower()}|{cidade.lower()}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _select_unique(urls: list, nome: str, quantidade: int) -> list:
    """Seleciona fotos com shuffle seeded pelo nome — mesma pool, ordem única por cliente."""
    if len(urls) <= quantidade:
        return urls
    seed = int(hashlib.md5(nome.lower().encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    pool = list(urls)
    rng.shuffle(pool)
    return pool[:quantidade]


def buscar_fotos_unsplash(
    segmento: str,
    quantidade: int = 8,
    nome: str = "",
    cidade: str = "",
) -> list:
    """
    Busca fotos do Unsplash para o negócio.
    Retorna lista de URLs (formato 'regular' — 1080px).

    Cache por negócio (segmento+nome+cidade) — 7 dias.
    Busca pool de 20 fotos e seleciona 8 com seed do nome para unicidade.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    ck = _cache_key(segmento, nome, cidade)
    cache_file = os.path.join(CACHE_DIR, f"unsplash_{ck}.json")

    # Cache hit — pool já existe para este negócio
    if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file)) < CACHE_TTL:
        try:
            with open(cache_file) as f:
                pool = json.load(f)
            selected = _select_unique(pool, nome or segmento, quantidade)
            print(f"[Unsplash] Cache HIT: {len(selected)}/{len(pool)} fotos para '{nome or segmento}'")
            return selected
        except Exception:
            pass

    query = _build_query(segmento, cidade, nome)

    # Sem chave — fallback source.unsplash.com com sig único por negócio
    if not UNSPLASH_ACCESS_KEY:
        print(f"[Unsplash] AVISO: UNSPLASH_ACCESS_KEY nao configurada. Usando fallback.")
        seed = int(hashlib.md5((nome + segmento).lower().encode()).hexdigest()[:8], 16)
        query_encoded = query.replace(" ", ",")
        urls = [
            f"https://source.unsplash.com/1200x800/?{query_encoded}&sig={seed + i}"
            for i in range(quantidade)
        ]
        try:
            with open(cache_file, "w") as f:
                json.dump(urls, f)
        except Exception:
            pass
        return urls

    # API oficial — busca pool de 20 para ter variedade
    pool_size = min(20, 50)  # máximo razoável sem estourar rate limit
    try:
        print(f"[Unsplash] Buscando '{query}' (pool={pool_size}) para '{nome or segmento}'...")
        resp = requests.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": query,
                "per_page": pool_size,
                "orientation": "landscape",
                "content_filter": "high",
                "order_by": "relevant",
            },
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        pool = [photo["urls"]["regular"] for photo in data.get("results", [])]

        if not pool:
            print(f"[Unsplash] Sem resultados para '{query}', usando fallback")
            return _fallback_urls(query, quantidade, nome)

        # Salvar pool completo no cache
        try:
            with open(cache_file, "w") as f:
                json.dump(pool, f)
        except Exception:
            pass

        selected = _select_unique(pool, nome or segmento, quantidade)
        print(f"[Unsplash] OK: {len(selected)}/{len(pool)} fotos selecionadas para '{nome or segmento}'")
        return selected

    except Exception as e:
        print(f"[Unsplash] Erro API: {e}. Usando fallback.")
        return _fallback_urls(query, quantidade, nome)


def _fallback_urls(query: str, quantidade: int, nome: str = "") -> list:
    """Fallback com URLs diretas do Unsplash sem API — sig único por negócio."""
    seed = int(hashlib.md5(nome.lower().encode()).hexdigest()[:8], 16) if nome else 0
    q = query.replace(" ", ",")
    return [
        f"https://source.unsplash.com/1200x800/?{q}&sig={seed + i}"
        for i in range(quantidade)
    ]
