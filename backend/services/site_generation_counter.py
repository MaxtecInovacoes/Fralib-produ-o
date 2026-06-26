"""site_generation_counter — Sprint 14.6.

Helpers para memoria anti-repeticao por counter rotation.

Cada tenant+subnicho tem um counter que representa quantos sites ja foram
gerados. Counter 0 = primeiro site, counter 1 = segundo, etc.

Pipeline usa o counter para fazer XOR no variation_seed e o lead novo
pega layout/motion/copy DIFERENTE do anterior.

Tabela: public.site_generation_log (criada por alembic)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_TABLE = "site_generation_log"


def _engine():
    """Lazy import para evitar circular dep."""
    try:
        from backend.core.database import engine as _eng
    except ImportError:
        from core.database import engine as _eng  # type: ignore
    return _eng


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_counter(tenant_id: int | str | None, subnicho: str | None) -> int:
    """Conta quantos sites ja foram gerados para tenant+subnicho.

    Retorna 0 se nada encontrado. Counter e deterministicamente baseado
    no estado atual da tabela — prox render pega counter+1.
    """
    if not subnicho:
        return 0
    _t = _to_int(tenant_id)
    if _t is None:
        return 0
    _subnicho = str(subnicho).strip().lower()
    if not _subnicho:
        return 0

    try:
        from sqlalchemy import text
        with _engine().connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT COUNT(*) FROM public.{_TABLE} "
                    f"WHERE tenant_id = :tid AND subnicho = :sub"
                ),
                {"tid": _t, "sub": _subnicho},
            ).fetchone()
            return int(row[0] or 0) if row else 0
    except Exception as e:
        logger.warning(f"[site_generation_counter] get_counter falhou: {e}")
        return 0


def log_generation(
    *,
    tenant_id: int | str | None,
    lead_id: str | None,
    subnicho: str | None,
    segmento: str | None,
    layout_variant: str,
    motion_variant: str,
    copy_variant: str,
    color_palette_hash: str,
    hero_classes: str,
    section_order: list[str],
) -> bool:
    """Registra geracao no log. Retorna True se inseriu, False se falhou.

    NAO LANCA EXCECAO — falhar aqui nao pode quebrar o pipeline.
    """
    _t = _to_int(tenant_id)
    if _t is None or not lead_id or not subnicho:
        return False
    try:
        from sqlalchemy import text
        with _engine().connect() as conn:
            conn.execute(
                text(
                    f"""
                    INSERT INTO public.{_TABLE}
                        (tenant_id, lead_id, subnicho, segmento,
                         layout_variant, motion_variant, copy_variant,
                         color_palette_hash, hero_classes, section_order_json)
                    VALUES
                        (:tid, :lid, :sub, :seg,
                         :lv, :mv, :cv,
                         :cph, :hc, :soj)
                    """
                ),
                {
                    "tid": _t,
                    "lid": str(lead_id)[:100],
                    "sub": str(subnicho).strip().lower()[:100],
                    "seg": (str(segmento or "")[:100]),
                    "lv": str(layout_variant)[:20],
                    "mv": str(motion_variant)[:20],
                    "cv": str(copy_variant)[:20],
                    "cph": str(color_palette_hash)[:64],
                    "hc": str(hero_classes)[:2000],
                    "soj": json.dumps(section_order or []),
                },
            )
            conn.commit()
        return True
    except Exception as e:
        logger.warning(f"[site_generation_counter] log_generation falhou: {e}")
        return False


def hash_color_palette(palette: dict[str, Any] | None) -> str:
    """Hash estavel da paleta para detectar 'mesma cor mesmo briefing'."""
    if not isinstance(palette, dict):
        return ""
    keys = ("primary", "secondary", "accent", "background", "text", "surface")
    canonical = json.dumps(
        {k: str(palette.get(k, "")) for k in keys},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def get_recent_for_subnicho(tenant_id: int | str | None, subnicho: str | None, limit: int = 5) -> list[dict[str, Any]]:
    """Retorna os ultimos N sites gerados para o subnicho.

    Usado para anti-repeticao: o pipeline injeta contexto dos ultimos
    sites para o LLM saber o que NAO repetir.
    """
    if not subnicho:
        return []
    _t = _to_int(tenant_id)
    if _t is None:
        return []
    try:
        from sqlalchemy import text
        with _engine().connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT layout_variant, motion_variant, copy_variant,
                           section_order_json, created_at
                    FROM public.{_TABLE}
                    WHERE tenant_id = :tid AND subnicho = :sub
                    ORDER BY created_at DESC LIMIT :lim
                    """
                ),
                {"tid": _t, "sub": str(subnicho).strip().lower(), "lim": limit},
            ).fetchall()
        results = []
        for r in rows:
            results.append({
                "layout_variant": r[0],
                "motion_variant": r[1],
                "copy_variant": r[2],
                "section_order": r[3] if isinstance(r[3], list) else [],
                "created_at": str(r[4]) if r[4] else "",
            })
        return results
    except Exception as e:
        logger.warning(f"[site_generation_counter] get_recent_for_subnicho falhou: {e}")
        return []
