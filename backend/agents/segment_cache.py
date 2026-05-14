"""
segment_cache.py - Cache inteligente por segmento para reduzir tokens.
Cacheia briefings, PRDs e contextos por nicho para reutilizar entre leads do mesmo segmento.
Economia estimada: -40% tokens no Theo, -40% no Arquiteto, -30% no Liam.

Multi-tenant: todas as chaves sao prefixadas por user_id para evitar vazamento
de briefings/PRDs entre usuarios distintos.
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


def _cache_key(tipo: str, user_id: int, segmento: str, cidade: str = "") -> str:
    """Gera chave de cache deterministica, escopada ao user_id."""
    raw = f"{tipo}:u{int(user_id)}:{segmento.lower().strip()}:{cidade.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _cache_path(tipo: str, user_id: int, segmento: str, cidade: str = "") -> Path:
    """Retorna path do arquivo de cache."""
    key = _cache_key(tipo, user_id, segmento, cidade)
    return CACHE_DIR / f"{tipo}_u{int(user_id)}_{key}.json"


def get_cached(tipo: str, user_id: int, segmento: str, cidade: str = "") -> Optional[Dict[str, Any]]:
    """
    Busca cache por tipo+user_id+segmento+cidade.
    Retorna None se nao existe ou expirou.
    """
    if not user_id:
        return None
    path = _cache_path(tipo, user_id, segmento, cidade)
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        ttl = TTL.get(tipo, 24 * 3600)
        age = time.time() - data.get("timestamp", 0)
        if age > ttl:
            print(f"[SegCache] EXPIRED: {tipo}/u{user_id}/{segmento} (age={int(age/3600)}h, ttl={int(ttl/3600)}h)")
            path.unlink(missing_ok=True)
            return None

        print(f"[SegCache] HIT: {tipo}/u{user_id}/{segmento} (age={int(age/3600)}h)")
        return data.get("payload")

    except (json.JSONDecodeError, KeyError) as e:
        print(f"[SegCache] CORRUPT: {tipo}/u{user_id}/{segmento} - {e}")
        path.unlink(missing_ok=True)
        return None


def set_cached(tipo: str, user_id: int, segmento: str, payload: Any, cidade: str = "") -> None:
    """Salva no cache (escopado ao user_id)."""
    if not user_id:
        print(f"[SegCache] SKIP: tentativa de salvar sem user_id (tipo={tipo})")
        return
    path = _cache_path(tipo, user_id, segmento, cidade)
    data = {
        "tipo": tipo,
        "user_id": int(user_id),
        "segmento": segmento,
        "cidade": cidade,
        "timestamp": time.time(),
        "payload": payload,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[SegCache] SAVED: {tipo}/u{user_id}/{segmento} ({len(json.dumps(payload))} chars)")
    except Exception as e:
        print(f"[SegCache] SAVE ERROR: {e}")


def get_briefing_cached(user_id: int, segmento: str, cidade: str = "") -> Optional[str]:
    """Busca briefing do Theo cacheado por user_id+segmento."""
    data = get_cached("briefing", user_id, segmento, cidade)
    return data if isinstance(data, str) else None


def set_briefing_cached(user_id: int, segmento: str, briefing: str, cidade: str = "") -> None:
    """Salva briefing do Theo no cache por user_id+segmento."""
    set_cached("briefing", user_id, segmento, briefing, cidade)


def get_prd_base_cached(user_id: int, segmento: str) -> Optional[Dict]:
    """Busca PRD base do Arquiteto cacheado por user_id+segmento."""
    return get_cached("prd_base", user_id, segmento)


def set_prd_base_cached(user_id: int, segmento: str, prd_data: Dict) -> None:
    """Salva PRD base no cache por user_id+segmento."""
    set_cached("prd_base", user_id, segmento, prd_data)


def get_design_context_cached(user_id: int, segmento: str) -> Optional[Dict]:
    """Busca design context cacheado por user_id+segmento."""
    return get_cached("design_context", user_id, segmento)


def set_design_context_cached(user_id: int, segmento: str, context: Dict) -> None:
    """Salva design context no cache por user_id+segmento."""
    set_cached("design_context", user_id, segmento, context)


def get_jina_cached(user_id: int, segmento: str, cidade: str = "") -> Optional[str]:
    """Busca pesquisa Jina cacheada por user_id+segmento+cidade."""
    data = get_cached("jina_research", user_id, segmento, cidade)
    return data if isinstance(data, str) else None


def set_jina_cached(user_id: int, segmento: str, resultado: str, cidade: str = "") -> None:
    """Salva pesquisa Jina no cache."""
    set_cached("jina_research", user_id, segmento, resultado, cidade)


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


def clear_pre_tenant_caches() -> int:
    """
    Remove caches antigos sem prefixo de user_id (pre multi-tenant).
    Padrao novo: '{tipo}_u{id}_{hash}.json' (sempre contem '_u<digito>')
    Padrao antigo: '{tipo}_{hash}.json' (sem '_u<digito>')
    """
    import re as _re
    removed = 0
    if not CACHE_DIR.exists():
        return 0
    tenant_pat = _re.compile(r"_u\d+_")
    for f in CACHE_DIR.glob("*.json"):
        if not tenant_pat.search(f.name):
            try:
                f.unlink()
                removed += 1
            except Exception:
                pass
    if removed:
        print(f"[SegCache] Limpeza: {removed} caches pre-tenant removidos")
    return removed
