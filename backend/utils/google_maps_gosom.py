"""
Google Maps Scraper Client — gosom/google-maps-scraper REST API
Alternativa open-source ao Playwright. Roda como daemon na VPS (porta 8080).
Fallback: se gosom não estiver disponível, usa Playwright (google_local_scraper.py).

Docs: https://github.com/gosom/google-maps-scraper
"""

import httpx
import asyncio
import time
from typing import List, Dict, Optional

GOSOM_BASE_URL = "http://localhost:8080"
GOSOM_TIMEOUT = 180  # 3 min max por job
GOSOM_POLL_INTERVAL = 3  # poll a cada 3s


async def _gosom_disponivel() -> bool:
    """Verifica se o daemon gosom está rodando."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{GOSOM_BASE_URL}/api/v1/health")
            return r.status_code == 200
    except Exception:
        return False


async def buscar_gosom(
    segmento: str,
    cidade: str,
    limite: int = 10,
    lang: str = "pt-BR",
    extra_reviews: bool = True,
) -> Optional[List[Dict]]:
    """
    Busca leads via gosom REST API.
    Retorna lista de dicts no formato compatível com google_local_scraper.
    Retorna None se gosom não estiver disponível (trigger fallback).
    """
    if not await _gosom_disponivel():
        print("[Gosom] Daemon não disponível — fallback para Playwright")
        return None

    query = f"{segmento} em {cidade}"
    payload = {
        "keyword": query,
        "lang": lang,
        "max_depth": 1,
        "extra_reviews": extra_reviews,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Submit job
            r = await client.post(f"{GOSOM_BASE_URL}/api/v1/jobs", json=payload)
            if r.status_code not in (200, 201):
                print(f"[Gosom] Erro ao submeter job: {r.status_code} {r.text}")
                return None

            job_data = r.json()
            job_id = job_data.get("id") or job_data.get("job_id")
            if not job_id:
                print(f"[Gosom] Resposta sem job_id: {job_data}")
                return None

            print(f"[Gosom] Job {job_id} submetido: '{query}' (limite={limite})")

        # Poll for results
        start = time.time()
        async with httpx.AsyncClient(timeout=30) as client:
            while time.time() - start < GOSOM_TIMEOUT:
                await asyncio.sleep(GOSOM_POLL_INTERVAL)
                r = await client.get(f"{GOSOM_BASE_URL}/api/v1/jobs/{job_id}")
                if r.status_code != 200:
                    continue

                data = r.json()
                status = data.get("status", "")

                if status in ("completed", "done", "finished"):
                    results = data.get("results") or data.get("data") or []
                    print(f"[Gosom] Job concluído: {len(results)} resultados")
                    return _normalizar_resultados(results[:limite])

                if status in ("failed", "error"):
                    print(f"[Gosom] Job falhou: {data.get('error', 'unknown')}")
                    return None

        print(f"[Gosom] Timeout ({GOSOM_TIMEOUT}s) — fallback para Playwright")
        return None

    except Exception as e:
        print(f"[Gosom] Erro: {e} — fallback para Playwright")
        return None


def _normalizar_resultados(results: List[Dict]) -> List[Dict]:
    """
    Converte output do gosom pro formato esperado pelo Hunter V2.
    Formato esperado: {nome, tipo, endereco, telefone, rating, reviews,
                       website, logo, fotos, depoimentos, horarios, maps_url,
                       atributos, servicos, faixa_preco}
    """
    normalized = []
    for r in results:
        # gosom usa nomes de campo em inglês
        nome = r.get("title") or r.get("name") or ""
        if not nome or len(nome) < 3:
            continue

        # Reviews/depoimentos
        reviews_raw = r.get("user_reviews") or r.get("reviews") or []
        depoimentos = []
        for rev in reviews_raw:
            depoimentos.append({
                "autor": rev.get("name") or rev.get("author") or "",
                "rating": rev.get("rating") or 5,
                "texto": rev.get("description") or rev.get("text") or "",
                "data": rev.get("when") or rev.get("date") or "",
            })

        # Fotos
        images_raw = r.get("images") or r.get("photos") or []
        fotos = []
        for img in images_raw:
            if isinstance(img, str):
                fotos.append(img)
            elif isinstance(img, dict):
                fotos.append(img.get("image") or img.get("url") or "")

        # Horários
        hours_raw = r.get("open_hours") or r.get("hours") or r.get("opening_hours") or {}
        horarios = []
        if isinstance(hours_raw, dict):
            for day, times in hours_raw.items():
                if isinstance(times, list):
                    for t in times:
                        horarios.append(f"{day}: {t}")
                else:
                    horarios.append(f"{day}: {times}")
        elif isinstance(hours_raw, list):
            horarios = hours_raw

        # Telefone
        telefone = r.get("phone") or r.get("telephone") or ""

        # Website
        website = r.get("website") or r.get("web") or ""

        normalized.append({
            "nome": nome.strip(),
            "tipo": r.get("category") or r.get("categories", [""])[0] if r.get("categories") else "",
            "endereco": r.get("address") or r.get("complete_address") or "",
            "telefone": telefone,
            "rating": float(r.get("rating") or r.get("review_rating") or 0),
            "reviews": int(r.get("review_count") or r.get("reviews_count") or len(depoimentos)),
            "website": website,
            "logo": r.get("thumbnail") or "",
            "fotos": [f for f in fotos if f],
            "depoimentos": depoimentos,
            "horarios": horarios,
            "maps_url": r.get("link") or r.get("url") or r.get("google_maps_url") or "",
            "atributos": r.get("about") or r.get("attributes") or [],
            "servicos": r.get("services") or [],
            "faixa_preco": r.get("price_range") or "",
            "place_id": r.get("place_id") or "",
            "latitude": r.get("latitude") or r.get("lat"),
            "longitude": r.get("longitude") or r.get("lng"),
            "total_avaliacoes": int(r.get("review_count") or r.get("reviews_count") or len(depoimentos)),
        })

    return normalized


async def buscar_negocio_gosom(nome: str, cidade: str) -> Optional[Dict]:
    """
    Busca um negócio específico pelo nome + cidade.
    Retorna dict normalizado ou None.
    """
    results = await buscar_gosom(nome, cidade, limite=1, extra_reviews=True)
    if results and len(results) > 0:
        return results[0]
    return None
