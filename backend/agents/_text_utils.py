"""Text utilities for the FraLib agent layer.

Canônico para T4 do plano DRY (codex/dry-refactor).

Três cópias idênticas desta função (Família 1: NFKD + ascii + lower) existiam em:
  - backend/agents/html_content_validator.py
  - backend/agents/html_quality_gate.py
  - backend/agents/html_publication_helpers.py

``visual_contract_gate.py`` e ``html_phase6_repair.py`` definem variantes
(Famílias 2 e 3) que divergem — divergência intencional documentada no plano.
"""
from __future__ import annotations

import re
import unicodedata


_NON_ALNUM_RE = re.compile(r"[^a-zA-Z0-9]+")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_compare(value: object) -> str:
    """Normalize text to lowercase ASCII tokens separated by single spaces.

    Strips accents via NFKD, drops non-ASCII, replaces non-alphanumeric runs
    with single space, collapses whitespace, lowercases. Returns empty string
    for empty/None input.
    """
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = _NON_ALNUM_RE.sub(" ", text).lower()
    return _WHITESPACE_RE.sub(" ", text).strip()