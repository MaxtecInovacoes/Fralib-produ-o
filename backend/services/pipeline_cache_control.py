"""Cache controls used by controlled cold pipeline reruns."""

from __future__ import annotations

import hashlib
import logging
import os

from sqlalchemy import text


_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger = logging.getLogger("uvicorn")


def invalidar_caches_cold_run(
    segmento: str, cidade: str, nome: str, pipeline_id: str, log_fn=None
):
    """Remove caches que podem mascarar um reprocessamento criativo controlado."""
    _log_local = log_fn or (lambda *_args, **_kwargs: None)
    _segmento = (segmento or "").strip()
    _cidade = (cidade or "").strip()
    _nome = (nome or "").strip()

    try:
        try:
            from agents.pipeline_checkpoint import limpar_checkpoint
        except Exception:  # pragma: no cover - package import variant
            from backend.agents.pipeline_checkpoint import limpar_checkpoint

        limpar_checkpoint(pipeline_id)
        _log_local("  Cold run: checkpoint invalidado", "info")
    except Exception as _e:
        logger.warning(f"[Pipeline] Cold run checkpoint skip: {_e}")

    try:
        _cache_key = hashlib.md5((_segmento.lower() + _cidade.lower()).encode()).hexdigest()[:12]
        _jina_file = os.path.join(_BASE, "agents", "jina_cache", f"jina_{_cache_key}.txt")
        if os.path.exists(_jina_file):
            os.remove(_jina_file)
            _log_local("  Cold run: cache Jina invalidado", "info")
    except Exception as _e:
        logger.warning(f"[Pipeline] Cold run Jina cache skip: {_e}")

    try:
        try:
            from database import engine
        except Exception:  # pragma: no cover - package import variant
            from backend.core.database import engine

        with engine.connect() as _conn:
            _conn.execute(
                text("DELETE FROM keyword_cache WHERE lower(segmento)=lower(:s) AND lower(cidade)=lower(:c)"),
                {"s": _segmento, "c": _cidade},
            )
            try:
                _conn.execute(
                    text("DELETE FROM leads_cache WHERE lower(segmento)=lower(:s) AND lower(cidade)=lower(:c)"),
                    {"s": _segmento, "c": _cidade},
                )
            except Exception:
                pass
            _conn.commit()
        _log_local("  Cold run: caches SQL de nicho/cidade invalidados", "info")
    except Exception as _e:
        logger.warning(f"[Pipeline] Cold run SQL cache skip: {_e}")

    try:
        from agents import unsplash_fetcher as _uf

        _query = _uf._build_query(_segmento, _cidade, _nome)
        _key = _uf._cache_key(_segmento, _nome, _cidade, _query)
        _path = os.path.join(_uf.CACHE_DIR, f"unsplash_{_key}.json")
        if os.path.exists(_path):
            os.remove(_path)
            _log_local("  Cold run: cache Unsplash invalidado", "info")
    except Exception as _e:
        logger.warning(f"[Pipeline] Cold run Unsplash cache skip: {_e}")

    try:
        from agents import pexels_video as _pv

        _key = _pv._cache_key(_segmento, _nome, _cidade)
        _path = os.path.join(_pv.CACHE_DIR, f"pexels_{_key}.json")
        if os.path.exists(_path):
            os.remove(_path)
            _log_local("  Cold run: cache Pexels invalidado", "info")
    except Exception as _e:
        logger.warning(f"[Pipeline] Cold run Pexels cache skip: {_e}")


class temporary_prd_cache_disabled:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.previous = None

    def __enter__(self):
        if self.enabled:
            self.previous = os.environ.get("DISABLE_PRD_CACHE")
            os.environ["DISABLE_PRD_CACHE"] = "1"

    def __exit__(self, exc_type, exc, tb):
        if not self.enabled:
            return
        if self.previous is None:
            os.environ.pop("DISABLE_PRD_CACHE", None)
        else:
            os.environ["DISABLE_PRD_CACHE"] = self.previous
