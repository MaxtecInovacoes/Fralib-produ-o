"""HTML utilities for the FraLib agent layer.

Canônico para T3 do plano DRY (codex/dry-refactor).

Quatro cópias idênticas desta função existiam em:
  - backend/agents/html_content_validator.py
  - backend/agents/html_quality_gate.py
  - backend/agents/html_builder_repair.py
  - backend/agents/html_publication_helpers.py

``html_content_validator``/``visual_contract_gate`` continuam definindo cópias
locais por motivos diferentes — o último diverge (não remove comentários nem
aplica html.unescape) e foi explicitamente excluído deste refactor.
"""
from __future__ import annotations

import html as _html
import re


_SCRIPT_RE = re.compile(r"(?is)<script\b.*?</script>")
_STYLE_RE = re.compile(r"(?is)<style\b.*?</style>")
_COMMENT_RE = re.compile(r"(?is)<!--.*?-->")
_TAG_RE = re.compile(r"(?is)<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def visible_text(html: str) -> str:
    """Return visible text from an HTML string.

    Strips ``<script>``, ``<style>``, comments, and all tags, then collapses
    whitespace and unescapes HTML entities.
    """
    clean = _SCRIPT_RE.sub(" ", html or "")
    clean = _STYLE_RE.sub(" ", clean)
    clean = _COMMENT_RE.sub(" ", clean)
    clean = _TAG_RE.sub(" ", clean)
    return _html.unescape(_WHITESPACE_RE.sub(" ", clean)).strip()