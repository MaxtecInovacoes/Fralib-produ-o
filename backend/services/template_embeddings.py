"""Sprint 7 (v1.10) - RAG Templates.

Lightweight in-memory RAG over `backend/templates/*.html`:
- 64-dim TF-IDF embeddings built with pure Python (no numpy).
- Atomic JSON persistence in `backend/services/_template_index.json`.
- Cosine similarity + best-match lookup for a given `nicho_briefing`.

The module is intentionally self-contained so it can be imported from
both FastAPI endpoints and offline scripts without pulling the rest of
the backend stack.
"""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import time
from collections import Counter
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Tuple

EMBEDDING_DIM = 64
INDEX_FILENAME = "_template_index.json"
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+", re.UNICODE)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_BACKEND_DIR = _HERE.parent
TEMPLATES_DIR = _BACKEND_DIR / "templates"
INDEX_PATH = _HERE / INDEX_FILENAME

# Nicho / briefing vocabulary used to bias feature selection.
# The keys are matched as substrings against the briefing text; the values
# are the bucket ids that will be given extra weight in the embedding.
_NICHO_KEYWORDS: Dict[str, List[str]] = {
    "bold": ["bold", "energia", "energy", "high", "impacto", "vibrante", "fitness", "academia"],
    "minimal": ["minimal", "limpo", "clean", "elegante", "simples", "premium", "consultoria"],
    "editorial": ["editorial", "blog", "artigo", "revista", "jornal", "conteudo", "materia"],
    "immersive": ["immersive", "3d", "imersivo", "imersion", "realidade", "showcase", "portfolio"],
    "kinetic": ["kinetic", "motion", "animacao", "animado", "movimento", "video", "parallax"],
    "scroll": ["scroll", "scrolltelling", "scrolly", "storytelling", "narrativa", "timeline"],
}


# ---------------------------------------------------------------------------
# Tokenization & TF-IDF
# ---------------------------------------------------------------------------
def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _hash_token(token: str, dim: int = EMBEDDING_DIM) -> int:
    """Stable hash bucket for a single token (FNV-1a style)."""
    h = 0x811C9DC5
    for ch in token.encode("utf-8"):
        h ^= ch
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h % dim


def _nicho_bucket(nicho_text: str) -> int:
    """Return a deterministic bucket index based on the nicho text."""
    if not nicho_text:
        return -1
    text = nicho_text.lower()
    # First match wins.
    for i, (name, keywords) in enumerate(_NICHO_KEYWORDS.items()):
        for kw in keywords:
            if kw in text:
                return i
    # Fallback: hash of the whole string.
    return _hash_token(text)


def embed_template(html: str) -> List[float]:
    """Compute a 64-dim TF-IDF embedding of an HTML template.

    Implementation details:
      * Each unique token maps to a deterministic dimension via FNV-1a hash.
      * The raw count is multiplied by `log(1 + 1/df)` where `df` is the
        document frequency derived from the input (we approximate IDF with
        a global-ish weight so single-document calls still produce
        meaningful vectors).
      * Nicho keywords receive a +1.5 boost on their bucket so that
        briefing texts with strong nicho signals cluster with the
        matching template family.
    """
    tokens = _tokenize(html)
    if not tokens:
        return [0.0] * EMBEDDING_DIM

    counts = Counter(tokens)
    total = float(len(tokens)) or 1.0

    # IDF approximation: log(1 + total / (1 + df_token))
    vector: List[float] = [0.0] * EMBEDDING_DIM
    for token, c in counts.items():
        idx = _hash_token(token)
        tf = c / total
        idf = math.log(1.0 + (1.0 / max(1, c)))
        vector[idx] += tf * idf

    # Apply nicho bias based on tokens themselves (heuristic).
    text_lower = " ".join(tokens)
    bucket = _nicho_bucket(text_lower)
    if bucket >= 0 and bucket < EMBEDDING_DIM:
        vector[bucket] += 1.5

    return _normalize(vector)


def _normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 0:
        return vec
    return [v / norm for v in vec]


# ---------------------------------------------------------------------------
# Index operations
# ---------------------------------------------------------------------------
_index_lock = RLock()
_index_cache: Dict[str, List[float]] = {}
_last_indexed_at: float = 0.0


def _list_template_files(root: Optional[Path] = None) -> List[Path]:
    root = root or TEMPLATES_DIR
    if not root.exists():
        return []
    files: List[Path] = []
    for entry in sorted(root.rglob("*.html")):
        if entry.is_file():
            files.append(entry)
    return files


def index_templates(root: Optional[Path] = None) -> Dict[str, List[float]]:
    """Walk `backend/templates/*.html` and produce {name: embedding}."""
    global _last_indexed_at

    files = _list_template_files(root)
    new_index: Dict[str, List[float]] = {}

    for fp in files:
        try:
            html = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        name = fp.stem
        # Key by relative path under templates/ when nested, else stem.
        rel = fp.relative_to(root or TEMPLATES_DIR).as_posix()
        key = rel[:-5] if rel.endswith(".html") else rel
        new_index[key] = embed_template(html)

    with _index_lock:
        _index_cache.clear()
        _index_cache.update(new_index)
        _last_indexed_at = time.time()
        snapshot = dict(_index_cache)
    persist_index(snapshot)
    return snapshot


def get_index() -> Dict[str, List[float]]:
    """Return the in-memory index (loads from disk on first call)."""
    with _index_lock:
        if _index_cache:
            return dict(_index_cache)
        loaded = load_index()
        if loaded:
            _index_cache.update(loaded["vectors"])
            return dict(_index_cache)
        # Fall back to a fresh build so callers always get something useful.
    return index_templates()


def persist_index(index: Optional[Dict[str, List[float]]] = None) -> Path:
    """Atomically write the index to JSON on disk."""
    idx = index if index is not None else get_index()
    payload = {
        "version": 1,
        "embedding_dim": EMBEDDING_DIM,
        "created_at": time.time(),
        "count": len(idx),
        "vectors": idx,
    }
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="_template_index_", suffix=".json", dir=INDEX_PATH.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        os.replace(tmp_path, INDEX_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return INDEX_PATH


def load_index(path: Optional[Path] = None) -> Dict[str, object]:
    """Load the persisted index from disk. Returns empty dict on failure."""
    fp = path or INDEX_PATH
    if not fp.exists():
        return {}
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        vectors = data.get("vectors") or {}
        if not isinstance(vectors, dict):
            return {}
        # Validate dimensionality.
        clean: Dict[str, List[float]] = {}
        for k, v in vectors.items():
            if isinstance(v, list) and len(v) == EMBEDDING_DIM:
                clean[k] = [float(x) for x in v]
        return {"vectors": clean, "created_at": data.get("created_at", 0.0)}
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------
def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two equally-sized vectors."""
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        # Pad/truncate to the shorter length to remain defensive.
        n = min(len(a), len(b))
        a = a[:n]
        b = b[:n]
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def find_best_template(
    nicho_briefing: str, top_k: int = 3
) -> List[Dict[str, object]]:
    """Return the top-k templates most similar to the briefing text."""
    idx = get_index()
    if not idx:
        return []
    qvec = embed_template(nicho_briefing or "")
    scored: List[Tuple[str, float]] = []
    for name, vec in idx.items():
        scored.append((name, cosine_similarity(qvec, vec)))
    scored.sort(key=lambda kv: kv[1], reverse=True)
    k = max(1, min(int(top_k), len(scored)))
    return [
        {"template": name, "score": float(score), "rank": i + 1}
        for i, (name, score) in enumerate(scored[:k])
    ]


def get_template_stats() -> Dict[str, object]:
    """Return summary statistics about the template index."""
    idx = get_index()
    last = _last_indexed_at
    if not last:
        # Try to read from disk.
        loaded = load_index()
        last = float(loaded.get("created_at", 0.0) or 0.0) if loaded else 0.0
    return {
        "total": len(idx),
        "embedding_dim": EMBEDDING_DIM,
        "last_indexed": last,
        "index_path": str(INDEX_PATH),
        "templates_dir": str(TEMPLATES_DIR),
        "templates": sorted(idx.keys()),
    }


__all__ = [
    "EMBEDDING_DIM",
    "INDEX_PATH",
    "TEMPLATES_DIR",
    "embed_template",
    "index_templates",
    "get_index",
    "cosine_similarity",
    "find_best_template",
    "persist_index",
    "load_index",
    "get_template_stats",
]