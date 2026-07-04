"""URL-safe slug normalization for the FraLib backend.

Canônico para M4 do plano DRY (codex/dry-refactor).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _nfkd_ascii_lower(text: str) -> str:
    """NFKD-decompose, drop combining marks, ASCII-encode, lowercase."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.encode("ascii", "ignore").decode("ascii").lower()


def slugify(
    text: object,
    sep: str = "-",
    max_len: Optional[int] = None,
    fallback: Optional[str] = None,
    collapse_sep: bool = True,
) -> str:
    """Normalize ``text`` to a URL-safe slug.

    Pipeline:
      1. Coerce to str.
      2. NFKD-decompose + drop diacritics + ASCII-encode + lowercase.
      3. Replace any non-alphanumeric run with ``sep``.
      4. If ``collapse_sep``, collapse runs of ``sep`` to a single char.
      5. Strip leading/trailing ``sep``.
      6. Truncate to ``max_len`` if given (re-strip after).
      7. Return ``fallback`` when the result is empty.
    """
    text = _nfkd_ascii_lower(str(text or ""))
    text = _NON_ALNUM_RE.sub(sep, text)
    if collapse_sep and sep:
        text = re.sub(f"({re.escape(sep)})+", sep, text)
    text = text.strip(sep)
    if max_len is not None:
        text = text[:max_len].strip(sep)
    if not text and fallback is not None:
        return fallback
    return text
