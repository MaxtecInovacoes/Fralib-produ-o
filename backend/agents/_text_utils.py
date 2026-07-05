"""Shared text utilities for the FraLib agent layer.

Canônico para T4, B2 e M2 do plano DRY (codex/dry-refactor).
"""
from __future__ import annotations

import re
import unicodedata


# ── T4: normalize_compare ─────────────────────────────────────────────────────
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


# ── B2: strip_control_chars ───────────────────────────────────────────────────
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def strip_control_chars(text: str) -> str:
    """Replace ASCII control characters that break JSON with a single space."""
    return _CONTROL_CHARS_RE.sub(" ", text or "")


# ── M2: strip_code_fence ─────────────────────────────────────────────────────
# Strips markdown ``` fences from LLM output. Case-insensitive (covers ```JSON,
# ```Json, etc). Trailing whitespace at fence ends handled gracefully.
_FENCE_OPEN_RE = re.compile(r"^```[a-zA-Z0-9_-]*\s*", re.IGNORECASE)
_FENCE_CLOSE_RE = re.compile(r"\s*```$")


def strip_code_fence(text: str) -> str:
    """Remove leading and trailing markdown fences from a code block.

    Returns the text between the fences. If no fence is detected, returns
    the stripped input unchanged.
    """
    text = (text or "").strip()
    if not text.startswith("```"):
        return text
    text = _FENCE_OPEN_RE.sub("", text)
    text = _FENCE_CLOSE_RE.sub("", text)
    return text.strip()


# ── M13: whitespace_normalize ─────────────────────────────────────────────────
def whitespace_normalize(text: str, *, lower: bool = False, strip: bool = True) -> str:
    """Collapse runs of whitespace to a single space, optionally strip + lowercase.

    Replaces 27+ inline ``re.sub(r"\\s+", " ", text).strip()`` patterns across
    backend/agents, backend/services, backend/utils. Uses the pre-compiled
    ``_WHITESPACE_RE`` for performance.

    Args:
        text: Input string (None-safe, coerced to "").
        lower: If True, also lowercases the result.
        strip: If True (default), strips leading/trailing whitespace after
            collapsing.

    Returns:
        Whitespace-normalized string.
    """
    text = _WHITESPACE_RE.sub(" ", text or "")
    if strip:
        text = text.strip()
    if lower:
        text = text.lower()
    return text
