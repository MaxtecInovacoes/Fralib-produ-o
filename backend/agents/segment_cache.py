"""
segment_cache.py - Cache inteligente por segmento para reduzir tokens.
Cacheia briefings, PRDs e contextos por nicho para reutilizar entre leads do mesmo segmento.
Economia estimada: -40% tokens no Theo, -40% no Arquiteto, -30% no Liam.
"""
import os
import json
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

CACHE_DIR = Path("/root/fralib/backend/agents/segment_knowledge")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# TTL por tipo de cache (em segundos)
TTL = {
    "briefing": 7 * 24 * 3600,      # 7 dias - briefing do Theo por segmento
    "prd_base": 7 * 24 * 3600,      # 7 dias - PRD base do Arquiteto por segmento
    "design_context": 7 * 24 * 3600, # 7 dias - contexto visual por segmento
    "jina_research": 48 * 3600,      # 48h - pesquisa Jina por segmento+cidade
}


def _cache_key(tipo: str, segmento: str, cidade: str = "") -> str:
    """Gera chave de cache deterministica."""
    raw = f"{tipo}:{segmento.lower().strip()}:{cidade.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _cache_path(tipo: str, segmento: str, cidade: str = "") -> Path:
    """Retorna path do arquivo de cache."""
    key = _cache_key(tipo, segmento, cidade)
    return CACHE_DIR / f"{tipo}_{key}.json"


def get_cached(tipo: str, segmento: str, cidade: str = "") -> Optional[Dict[str, Any]]:
    """
    Busca cache por tipo+segmento+cidade.
    Retorna None se nao existe ou expirou.
    """
    path = _cache_path(tipo, segmento, cidade)
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Verificar TTL
        ttl = TTL.get(tipo, 24 * 3600)
        age = time.time() - data.get("timestamp", 0)
        if age > ttl:
            print(f"[SegCache] EXPIRED: {tipo}/{segmento} (age={int(age/3600)}h, ttl={int(ttl/3600)}h)")
            path.unlink(missing_ok=True)
            return None

        print(f"[SegCache] HIT: {tipo}/{segmento} (age={int(age/3600)}h)")
        return data.get("payload")

    except (json.JSONDecodeError, KeyError) as e:
        print(f"[SegCache] CORRUPT: {tipo}/{segmento} - {e}")
        path.unlink(missing_ok=True)
        return None


def set_cached(tipo: str, segmento: str, payload: Any, cidade: str = "") -> None:
    """Salva no cache."""
    path = _cache_path(tipo, segmento, cidade)
    data = {
        "tipo": tipo,
        "segmento": segmento,
        "cidade": cidade,
        "timestamp": time.time(),
        "payload": payload,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[SegCache] SAVED: {tipo}/{segmento} ({len(json.dumps(payload))} chars)")
    except Exception as e:
        print(f"[SegCache] SAVE ERROR: {e}")


def get_briefing_cached(segmento: str, cidade: str = "") -> Optional[str]:
    """Busca briefing do Theo cacheado por segmento."""
    data = get_cached("briefing", segmento, cidade)
    return data if isinstance(data, str) else None


def set_briefing_cached(segmento: str, briefing: str, cidade: str = "") -> None:
    """Salva briefing do Theo no cache por segmento."""
    set_cached("briefing", segmento, briefing, cidade)


def get_prd_base_cached(segmento: str) -> Optional[Dict]:
    """Busca PRD base do Arquiteto cacheado por segmento."""
    return get_cached("prd_base", segmento)


def set_prd_base_cached(segmento: str, prd_data: Dict) -> None:
    """Salva PRD base no cache por segmento."""
    set_cached("prd_base", segmento, prd_data)


def get_design_context_cached(segmento: str) -> Optional[Dict]:
    """Busca design context cacheado por segmento."""
    return get_cached("design_context", segmento)


def set_design_context_cached(segmento: str, context: Dict) -> None:
    """Salva design context no cache por segmento."""
    set_cached("design_context", segmento, context)


def get_jina_cached(segmento: str, cidade: str = "") -> Optional[str]:
    """Busca pesquisa Jina cacheada por segmento+cidade."""
    data = get_cached("jina_research", segmento, cidade)
    return data if isinstance(data, str) else None


def set_jina_cached(segmento: str, resultado: str, cidade: str = "") -> None:
    """Salva pesquisa Jina no cache."""
    set_cached("jina_research", segmento, resultado, cidade)


def cache_stats() -> Dict[str, int]:
    """Retorna estatisticas do cache."""
    stats = {"total": 0, "expired": 0, "valid": 0, "size_kb": 0}
    if not CACHE_DIR.exists():
        return stats
    for f in CACHE_DIR.glob("*.json"):
        stats["total"] += 1
        stats["size_kb"] += f.stat().st_size // 1024
        try:
            with open(f, "r") as fh:
                data = json.load(fh)
            tipo = data.get("tipo", "")
            ttl = TTL.get(tipo, 24 * 3600)
            age = time.time() - data.get("timestamp", 0)
            if age > ttl:
                stats["expired"] += 1
            else:
                stats["valid"] += 1
        except Exception:
            stats["expired"] += 1
    return stats


def clear_expired() -> int:
    """Remove caches expirados. Retorna quantidade removida."""
    removed = 0
    if not CACHE_DIR.exists():
        return 0
    for f in CACHE_DIR.glob("*.json"):
        try:
            with open(f, "r") as fh:
                data = json.load(fh)
            tipo = data.get("tipo", "")
            ttl = TTL.get(tipo, 24 * 3600)
            age = time.time() - data.get("timestamp", 0)
            if age > ttl:
                f.unlink()
                removed += 1
        except Exception:
            f.unlink()
            removed += 1
    if removed:
        print(f"[SegCache] Limpeza: {removed} caches expirados removidos")
    return removed
