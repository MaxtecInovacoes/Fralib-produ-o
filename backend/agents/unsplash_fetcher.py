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
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unsplash_cache")
CACHE_TTL = 7 * 24 * 3600  # 7 dias por negócio

# Queries base por nicho — termos em inglês convertem melhor no Unsplash
QUERIES_NICHO = {
    "nutricionista": "nutritionist healthy food meal prep",
    "academia": "gym fitness workout training",
    "natacao": "swimming pool swim lessons aquatic fitness",
    "crossfit": "crossfit workout athlete training",
    "barbearia": "barbershop haircut grooming men",
    "salao": "hair salon beauty hairstyle",
    "salao_beleza": "hair salon beauty hairstyle",
    "clinica": "medical clinic doctor health",
    "dentista": "dentist dental clinic smile",
    "odontologia": "dentist dental clinic smile",
    "estetica": "beauty spa aesthetic treatment",
    "restaurante": "restaurant food dining gourmet",
    "churrascaria": "steakhouse barbecue grilled meat fire",
    "lanchonete": "burger sandwich food snack",
    "padaria": "bakery bread pastry artisan",
    "confeitaria": "cake pastry dessert sweet",
    "cafe": "coffee cafe espresso barista",
    "advocacia": "law office lawyer professional",
    "imobiliaria": "real estate house property",
    "escola": "school education classroom learning",
    "farmacia": "pharmacy medicine health",
    "otica": "eyeglasses optical store eyewear",
    "oticas": "eyeglasses optical store eyewear",
    "pet_shop": "pet dog cat veterinary",
    "pet": "pet dog cat veterinary",
    "auto_pecas": "car mechanic garage automotive",
    "psicologia": "psychology therapy mental health",
    "arquitetura": "architecture interior design modern",
    "fotografia": "photography studio camera portrait",
    "personal": "personal trainer fitness coaching",
    "pilates": "pilates yoga studio wellness",
    "fisioterapia": "physiotherapy rehabilitation therapy",
    "pizzaria": "pizza italian food restaurant",
    "contabilidade": "accounting office business finance",
}

# Queries VARIADAS por nicho — usadas pra buscar fotos diversas (1 por query)
QUERIES_VARIADAS = {
    "natacao": [
        "indoor swimming pool lessons",
        "swim class pool coach",
        "aquatic fitness pool training",
        "children swimming lesson pool",
        "lap swimming pool lanes",
    ],
    "academia": [
        "gym training action dark",
        "fitness weights closeup moody",
        "workout group energy",
        "personal trainer coaching",
        "gym equipment modern dark",
    ],
    "crossfit": [
        "crossfit box workout intense",
        "athlete lifting barbell",
        "rope climb fitness dark",
        "crossfit group wod",
        "kettlebell swing action",
    ],
    "hamburgueria": [
        "burger closeup smoke dark",
        "grill fire meat cooking",
        "restaurant dark interior moody",
        "craft beer bar counter",
        "food preparation kitchen",
    ],
    "barbearia": [
        "barbershop vintage interior",
        "haircut men style dark",
        "barber tools razor closeup",
        "barbershop chair leather",
        "beard trim grooming",
    ],
    "restaurante": [
        "restaurant plating food elegant",
        "chef cooking kitchen fire",
        "dining table candlelight",
        "wine glass restaurant dark",
        "food presentation gourmet",
    ],
    "dentista": [
        "dental clinic modern bright",
        "smile confident portrait",
        "dental equipment clean white",
        "dentist office interior",
        "teeth whitening result",
    ],
    "salao": [
        "hair salon colorful modern",
        "beauty treatment spa luxury",
        "hairstyle transformation",
        "salon interior design",
        "hair coloring process",
    ],
    "estetica": [
        "beauty spa treatment luxury",
        "skincare facial closeup",
        "aesthetic clinic modern",
        "massage therapy relaxing",
        "beauty products elegant",
    ],
    "pizzaria": [
        "pizza oven fire wood",
        "pizza making dough hands",
        "italian restaurant cozy",
        "pizza slice cheese pull",
        "pizzeria interior warm",
    ],
    "clinica": [
        "medical clinic modern clean",
        "doctor consultation professional",
        "health clinic interior",
        "medical equipment modern",
        "healthcare professional",
    ],
    "pet": [
        "pet dog happy portrait",
        "veterinary clinic care",
        "pet grooming salon",
        "cat dog together cute",
        "pet shop colorful",
    ],
    "advocacia": [
        "law office professional dark",
        "lawyer desk books",
        "legal office modern",
        "courthouse architecture",
        "business meeting professional",
    ],
    "otica": [
        "eyeglasses optical store eyewear",
        "glasses frames closeup",
        "optometrist eye exam clinic",
        "sunglasses display retail",
        "vision care professional",
    ],
}

CURATED_FALLBACK_IMAGES = {
    "otica": [
        "https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1574258495973-f010dfbb5371?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1556306535-38febf6782e7?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1509695507497-903c140c43b0?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1524255684952-d7185b509571?auto=format&fit=crop&w=1400&q=82",
    ],
    "nutricionista": [
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1505576399279-565b52d4ac71?auto=format&fit=crop&w=1400&q=82",
    ],
    "dentista": [
        "https://images.unsplash.com/photo-1606811971618-4486d14f3f99?auto=format&fit=crop&w=1400&q=82",
    ],
}

WATER_FITNESS_KEYWORDS = (
    "natacao",
    "natação",
    "piscina",
    "hidro",
    "hidroginastica",
    "hidroginástica",
    "aquatica",
    "aquática",
    "aqua",
    "swim",
    "swimming",
)


def _infer_query_key(segmento: str, nome: str = "") -> str:
    haystack = f"{segmento or ''} {nome or ''}".lower()
    haystack = haystack.replace("ç", "c").replace("ã", "a").replace("á", "a")
    normalized_keywords = (
        k.replace("ç", "c").replace("ã", "a").replace("á", "a")
        for k in WATER_FITNESS_KEYWORDS
    )
    if any(keyword in haystack for keyword in normalized_keywords):
        return "natacao"
    seg = (segmento or "").lower().strip().replace("-", "_").replace(" ", "_")
    return seg

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

ARCHETYPE_MEDIA_MODIFIERS = {
    "BOLD_ENERGY": "cinematic lighting high contrast moody professional photography dynamic action",
    "TRUST_ELITE": "premium professional editorial photography trust elegant minimal architecture",
    "ZEN_PURE": "wellness calm natural light premium editorial photography soft organic",
    "MODERN_TECH": "modern technology glassmorphism neon gradient clean interface",
    "LUXURY_ELITE": "luxury minimal dramatic light refined texture editorial photography",
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


def _build_query(segmento: str, cidade: str = "", nome: str = "", archetype: str = "") -> str:
    """Monta query enriquecida com contexto do negócio para fotos únicas."""
    query_key = _infer_query_key(segmento, nome)
    base = _get_query_base(query_key)
    city_mod = _get_city_modifier(cidade)
    mood_mod = ARCHETYPE_MEDIA_MODIFIERS.get((archetype or "").upper(), "")
    # Combinar base + modificador de cidade para diversidade geográfica
    parts = [base]
    if mood_mod:
        parts.append(mood_mod)
    if city_mod:
        parts.append(city_mod)
    return " ".join(parts)


def _cache_key(segmento: str, nome: str = "", cidade: str = "", query: str = "") -> str:
    """Cache key única por negócio — cada cliente tem seu próprio conjunto de fotos."""
    raw = f"{segmento.lower()}|{nome.lower()}|{cidade.lower()}|{query.lower()}"
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
    archetype: str = "",
) -> list:
    """
    Busca fotos do Unsplash para o negócio.
    Retorna lista de URLs (formato 'regular' — 1080px).

    Cache por negócio (segmento+nome+cidade) — 7 dias.
    Busca pool de 20 fotos e seleciona 8 com seed do nome para unicidade.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    query = _build_query(segmento, cidade, nome, archetype)
    ck = _cache_key(segmento, nome, cidade, query)
    cache_file = os.path.join(CACHE_DIR, f"unsplash_{ck}.json")

    # Cache hit — pool já existe para este negócio
    if (
        os.path.exists(cache_file)
        and (time.time() - os.path.getmtime(cache_file)) < CACHE_TTL
    ):
        try:
            with open(cache_file) as f:
                pool = json.load(f)
            selected = _select_unique(pool, nome or segmento, quantidade)
            print(
                f"[Unsplash] Cache HIT: {len(selected)}/{len(pool)} fotos para '{nome or segmento}'"
            )
            return selected
        except Exception:
            pass

    # Sem chave — fallback curado com URLs diretas e estáveis do Unsplash.
    if not UNSPLASH_ACCESS_KEY:
        print(
            f"[Unsplash] AVISO: UNSPLASH_ACCESS_KEY nao configurada. Usando fallback."
        )
        urls = _fallback_urls(query, quantidade, nome, segmento)
        try:
            with open(cache_file, "w") as f:
                json.dump(urls, f)
        except Exception:
            pass
        return urls

    # API oficial — busca pool de 20 para ter variedade
    pool_size = min(20, 50)  # máximo razoável sem estourar rate limit
    try:
        # Usar queries variadas se disponíveis (fotos mais diversas)
        seg_key = _infer_query_key(segmento, nome)
        _variadas = None
        for k in QUERIES_VARIADAS:
            if k in seg_key or seg_key in k:
                _variadas = QUERIES_VARIADAS[k]
                break

        pool = []
        if _variadas and UNSPLASH_ACCESS_KEY:
            # Buscar 4 fotos por query variada (5 queries × 4 = 20 fotos diversas)
            print(
                f"[Unsplash] Queries variadas: {len(_variadas)} queries para '{nome or segmento}'..."
            )
            for vq in _variadas[:5]:
                try:
                    resp = requests.get(
                        "https://api.unsplash.com/search/photos",
                        params={
                            "query": vq,
                            "per_page": 4,
                            "orientation": "landscape",
                            "content_filter": "high",
                        },
                        headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        for photo in resp.json().get("results", []):
                            url = photo["urls"]["regular"]
                            if url not in pool:
                                pool.append(url)
                except Exception:
                    continue
            print(f"[Unsplash] Queries variadas: {len(pool)} fotos únicas coletadas")

        # Fallback: query única se variadas não deram resultado suficiente
        if len(pool) < quantidade:
            print(
                f"[Unsplash] Buscando '{query}' (pool={pool_size}) para '{nome or segmento}'..."
            )
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
            for photo in data.get("results", []):
                url = photo["urls"]["regular"]
                if url not in pool:
                    pool.append(url)

        if not pool:
            print(f"[Unsplash] Sem resultados para '{query}', usando fallback")
            return _fallback_urls(query, quantidade, nome, segmento)

        # Salvar pool completo no cache
        try:
            with open(cache_file, "w") as f:
                json.dump(pool, f)
        except Exception:
            pass

        selected = _select_unique(pool, nome or segmento, quantidade)
        print(
            f"[Unsplash] OK: {len(selected)}/{len(pool)} fotos selecionadas para '{nome or segmento}'"
        )
        return selected

    except Exception as e:
        print(f"[Unsplash] Erro API: {e}. Usando fallback.")
        return _fallback_urls(query, quantidade, nome, segmento)


def _fallback_urls(query: str, quantidade: int, nome: str = "", segmento: str = "") -> list:
    """Fallback com URLs diretas e estáveis; source.unsplash.com não é confiável."""
    query_key = _infer_query_key(segmento or query, nome)
    pool: list[str] = []
    for key, urls in CURATED_FALLBACK_IMAGES.items():
        if key in query_key or key in (query or "").lower():
            pool.extend(urls)
    if not pool:
        pool = [
            "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1400&q=82",
            "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82",
            "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82",
            "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82",
            "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1400&q=82",
        ]
    selected = _select_unique(pool, nome or segmento or query, min(quantidade, len(pool)))
    while len(selected) < quantidade:
        selected.append(pool[len(selected) % len(pool)])
    return selected[:quantidade]
