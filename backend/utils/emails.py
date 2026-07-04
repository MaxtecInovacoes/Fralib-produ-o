"""Email extraction helpers for the FraLib backend.

Canônico para M9 do plano DRY (codex/dry-refactor).

Fornece extract_emails(value) — unifica 2 cópias divergentes:
  - backend/agents/html_content_validator.py:55 (regex A — bug com '%' no local)
  - backend/agents/html_publication_helpers.py:142 (regex B — completa, RFC-ish)

A divergência foi: regex A usa `[\w.\-+]+` que aceita `%` apenas como parte do
próximo char-set e quebra emails com `%tag` em `tag`. Regex B usa
`[a-zA-Z0-9._%+-]+` que captura corretamente.

Regex B foi escolhida como canônica por estar alinhada com RFC 5321 (local
part aceita `%`, `_`, etc).
"""
from __future__ import annotations

import re
from typing import Any


# RFC-ish email — aceita letras, dígitos, '.', '_', '%', '+', '-' no local;
# letras/dígitos, '.', '-' no domínio; TLD com 2+ letras.
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def extract_emails(value: Any) -> list[str]:
    """Extract email addresses from ``value`` (string, list, tuple, set, or None).

    Lists/tuples/sets are joined with spaces before extraction.
    Returns a list of email matches (may contain duplicates).
    """
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(v) for v in value)
    return _EMAIL_RE.findall(str(value or ""))


__all__ = ["extract_emails"]