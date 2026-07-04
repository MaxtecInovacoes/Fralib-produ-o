"""Shared text utilities for the FraLib agent layer.

Canônico para T4 e B2 do plano DRY (codex/dry-refactor).
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
# Strip ASCII control chars that break JSON parsing (0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F).
# Excludes tab (0x09), newline (0x0A) and carriage return (0x0D) — those are legit.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def strip_control_chars(text: str) -> str:
    """Replace ASCII control characters that break JSON with a single space."""
    return _CONTROL_CHARS_RE.sub(" ", text or "")
