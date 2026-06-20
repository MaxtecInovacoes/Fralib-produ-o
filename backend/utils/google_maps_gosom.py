"""
Google Maps Scraper Client — gosom/google-maps-scraper
Alternativa open-source ao Playwright. Roda como daemon na VPS (porta 8085).
Fallback: se gosom não estiver disponível, usa Playwright (google_local_scraper.py).

Modo de operação:
1. POST /api/v1/jobs → cria job
2. Poll GET /api/v1/jobs/{id} → espera status "ok"
3. Lê CSV de /root/gmapsdata/{id}.csv

Docs: https://github.com/gosom/google-maps-scraper
"""

import httpx
import asyncio
import csv
import json
import time
import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional

GOSOM_BASE_URL = "http://localhost:8085"
GOSOM_DATA_FOLDER = "/root/gmapsdata"
GOSOM_ENABLED = os.getenv("GOSOM_ENABLED", "0").lower() in {"1", "true", "yes", "on"}
GOSOM_TIMEOUT = int(os.getenv("GOSOM_TIMEOUT", "45"))
GOSOM_POLL_INTERVAL = int(os.getenv("GOSOM_POLL_INTERVAL", "3"))
GOSOM_STALE_WORKING_SECS = int(os.getenv("GOSOM_STALE_WORKING_SECS", "120"))
GOSOM_MAX_PENDING = int(os.getenv("GOSOM_MAX_PENDING", "3"))
GOSOM_CIRCUIT_OPEN_SECS = int(os.getenv("GOSOM_CIRCUIT_OPEN_SECS", "900"))

_CIRCUIT_OPEN_UNTIL = 0.0


def _abrir_circuito(motivo: str) -> None:
    global _CIRCUIT_OPEN_UNTIL
    _CIRCUIT_OPEN_UNTIL = time.time() + GOSOM_CIRCUIT_OPEN_SECS
    print(f"[Gosom] Circuito aberto por {GOSOM_CIRCUIT_OPEN_SECS}s: {motivo}")


def _parse_job_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        # Go/RFC3339Nano pode vir com 9 digitos; datetime aceita microssegundos.
        match = re.match(r"^(.+\.)(\d{6})\d+([+-]\d\d:\d\d)$", normalized)
        if match:
            normalized = "".join(match.groups())
        return datetime.fromisoformat(normalized)
    except Exception:
        return None


def _job_age_seconds(job: Dict) -> Optional[float]:
    dt = _parse_job_date(job.get("Date") or job.get("date") or "")
    if not dt:
        return None
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds()


async def _gosom_disponivel() -> bool:
    """Verifica se o daemon gosom está rodando."""
    if not GOSOM_ENABLED:
        print("[Gosom] Desativado por contrato (GOSOM_ENABLED!=1)")
        return False
    if time.time() < _CIRCUIT_OPEN_UNTIL:
        print("[Gosom] Circuito aberto — fallback imediato")
        return False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{GOSOM_BASE_URL}/api/v1/jobs")
            if r.status_code != 200:
                return False
            try:
                jobs = r.json()
            except Exception:
                return True
            if not isinstance(jobs, list):
                return True
            pending = 0
            stale_working = []
            for job in jobs:
                status = (job.get("Status") or job.get("status") or "").lower()
                if status == "pending":
                    pending += 1
                elif status in {"working", "running"}:
                    age = _job_age_seconds(job)
                    if age is not None and age > GOSOM_STALE_WORKING_SECS:
                        stale_working.append(job.get("ID") or job.get("id") or "?")
            if stale_working:
                _abrir_circuito(f"job working stale: {', '.join(stale_working[:3])}")
                return False
            if pending > GOSOM_MAX_PENDING:
                _abrir_circuito(f"fila interna alta: {pending} pending")
                return False
            return True
    except Exception as e:
        print(f"[Gosom] Health falhou: {e}")
        return False


async def buscar_gosom(
    segmento: str,
    cidade: str,
    limite: int = 10,
    lang: str = "pt",
) -> Optional[List[Dict]]:
    """
    Busca leads via gosom REST API + CSV output.
    Retorna lista de dicts no formato compatível com google_local_scraper.
    Retorna None se gosom não estiver disponível (trigger fallback).
    """
    if not await _gosom_disponivel():
        print("[Gosom] Daemon não disponível — fallback para Playwright")
        return None

    query = f"{segmento} em {cidade}"
    payload = {
        "name": f"{segmento}_{cidade}_{int(time.time())}",
        "keywords": [query],
        "lang": lang,
        "depth": 1,
        "max_time": GOSOM_TIMEOUT,
        "fast_mode": True,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Submit job
            r = await client.post(f"{GOSOM_BASE_URL}/api/v1/jobs", json=payload)
            if r.status_code not in (200, 201):
                print(f"[Gosom] Erro ao submeter job: {r.status_code} {r.text}")
                return None

            job_data = r.json()
            job_id = job_data.get("id") or job_data.get("ID")
            if not job_id:
                print(f"[Gosom] Resposta sem job_id: {job_data}")
                return None

            print(f"[Gosom] Job {job_id} submetido: '{query}'")

        # Poll for completion
        start = time.time()
        async with httpx.AsyncClient(timeout=30) as client:
            while time.time() - start < GOSOM_TIMEOUT:
                await asyncio.sleep(GOSOM_POLL_INTERVAL)
                r = await client.get(f"{GOSOM_BASE_URL}/api/v1/jobs/{job_id}")
                if r.status_code != 200:
                    continue

                try:
                    data = r.json()
                    status = data.get("Status", "")
                    if status == "ok":
                        print(f"[Gosom] Job concluído!")
                        break
                    elif status in ("failed", "error"):
                        print(f"[Gosom] Job falhou")
                        _abrir_circuito("job falhou")
                        return None
                except Exception:
                    continue
            else:
                print(f"[Gosom] Timeout ({GOSOM_TIMEOUT}s)")
                _abrir_circuito("timeout aguardando job")
                return None

        # Read CSV results
        csv_path = f"{GOSOM_DATA_FOLDER}/{job_id}.csv"
        results = await _ler_csv_resultados(csv_path, limite)
        if results:
            print(f"[Gosom] {len(results)} leads extraídos do CSV")
            return results
        else:
            print(f"[Gosom] CSV vazio ou não encontrado: {csv_path}")
            return None

    except Exception as e:
        print(f"[Gosom] Erro: {e} — fallback para Playwright")
        _abrir_circuito(str(e))
        return None


async def _ler_csv_resultados(csv_path: str, limite: int) -> Optional[List[Dict]]:
    """Lê CSV do gosom e normaliza pro formato do pipeline."""
    try:
        # Ler via cat remoto (o arquivo está na VPS, não local)
        # Como este código roda NA VPS, podemos ler direto
        if not os.path.exists(csv_path):
            return None

        results = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                normalized = _normalizar_row(row)
                if normalized:
                    results.append(normalized)
                if len(results) >= limite:
                    break

        return results if results else None
    except Exception as e:
        print(f"[Gosom] Erro lendo CSV: {e}")
        return None


def _normalizar_row(row: Dict) -> Optional[Dict]:
    """
    Converte uma row do CSV gosom pro formato esperado pelo Hunter V2.
    """
    nome = (row.get("title") or "").strip()
    if not nome or len(nome) < 3:
        return None

    # Reviews
    depoimentos = []
    try:
        reviews_raw = json.loads(row.get("user_reviews") or "[]")
        for rev in reviews_raw:
            depoimentos.append({
                "autor": rev.get("Name") or rev.get("name") or "",
                "rating": rev.get("Rating") or rev.get("rating") or 5,
                "texto": rev.get("Description") or rev.get("description") or rev.get("Text") or "",
                "data": rev.get("When") or rev.get("when") or rev.get("Date") or "",
            })
    except (json.JSONDecodeError, TypeError):
        pass

    # Fotos: não usar do Google Maps (pipeline usa Unsplash)
    fotos = []

    # Horários
    horarios = []
    try:
        hours_raw = json.loads(row.get("open_hours") or "{}")
        if isinstance(hours_raw, dict):
            for day, times in hours_raw.items():
                if isinstance(times, list):
                    for t in times:
                        horarios.append(f"{day}: {t}")
                else:
                    horarios.append(f"{day}: {times}")
    except (json.JSONDecodeError, TypeError):
        pass

    # Atributos
    atributos = []
    try:
        about_raw = json.loads(row.get("about") or "[]")
        if isinstance(about_raw, list):
            for section in about_raw:
                if isinstance(section, dict):
                    options = section.get("options") or []
                    for opt in options:
                        if isinstance(opt, dict):
                            atributos.append(opt.get("name") or "")
    except (json.JSONDecodeError, TypeError):
        pass

    # Endereço
    endereco = row.get("address") or ""
    try:
        complete = json.loads(row.get("complete_address") or "{}")
        if isinstance(complete, dict):
            parts = [complete.get("street", ""), complete.get("borough", ""), complete.get("city", "")]
            endereco = ", ".join(p for p in parts if p) or endereco
    except (json.JSONDecodeError, TypeError):
        pass

    review_count = int(row.get("review_count") or 0)
    rating = float(row.get("review_rating") or 0)

    # Gerar embed Google Maps por coordenadas ou nome+cidade
    google_maps_embed = ""
    lat = row.get("latitude")
    lng = row.get("longitude")
    try:
        if lat and lng:
            google_maps_embed = (f'<iframe width="100%" height="450" style="border:0;" loading="lazy" '
                f'src="https://maps.google.com/maps?q={lat},{lng}&output=embed&z=16"></iframe>')
        elif nome:
            import urllib.parse as _urlp
            _q = _urlp.quote_plus(f"{nome} {row.get('address', '')}")
            google_maps_embed = (f'<iframe width="100%" height="450" style="border:0;" loading="lazy" '
                f'src="https://maps.google.com/maps?q={_q}&output=embed&z=16"></iframe>')
    except Exception:
        pass

    return {
        "nome": nome,
        "tipo": row.get("category") or "",
        "endereco": endereco,
        "telefone": row.get("phone") or "",
        "rating": rating,
        "reviews": review_count,
        "total_avaliacoes": review_count,
        "website": row.get("website") or "",
        "logo": row.get("thumbnail") or "",
        "fotos": [f for f in fotos if f][:10],
        "depoimentos": depoimentos[:10],
        "horarios": horarios,
        "maps_url": row.get("link") or "",
        "atributos": [a for a in atributos if a],
        "servicos": [],
        "faixa_preco": row.get("price_range") or "",
        "place_id": row.get("place_id") or "",
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "google_maps_embed": google_maps_embed,
    }


async def buscar_negocio_gosom(nome: str, cidade: str) -> Optional[Dict]:
    """
    Busca um negócio específico pelo nome + cidade.
    Retorna dict normalizado ou None.
    """
    results = await buscar_gosom(nome, cidade, limite=3)
    if not results:
        return None

    # Tentar match exato pelo nome
    nome_lower = nome.lower().strip()
    for r in results:
        if nome_lower in r["nome"].lower():
            return r

    # Se não achou match exato, retorna o primeiro
    return results[0] if results else None
