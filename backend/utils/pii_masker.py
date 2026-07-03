"""PII masker — mascara PII (telefone, email, documento) em logs.

Regra LGPD: PII nunca em logs/stdout/stderr. Substituir por mascarado.

Phone format BR:
  - 5511945612345 (13 digitos, com 55) → "****1234"
  - 11945612345 (11 digitos)            → "****1234"
  - 9456-1234 (curto)                   → "****1234"
"""

from __future__ import annotations

import re
from typing import Optional

# Telefone BR: 10-13 digitos, opcionalmente com codigo pais 55
# Aceita: 5511945612345, 11945612345, (11) 94561-2345, +55 11 94561-2345
# Estrategia: match DDD opcional + 9 + 4digitos + 4digitos
_PHONE_RE = re.compile(
    r"(?:\+?55[\s.-]?)?"
    r"(?:\(?\d{2}\)?[\s.-]?)?"
    r"9[\s.-]?\d{4}[\s.-]?\d{4}"
    r"|"
    r"(?:\+?55[\s.-]?)?"
    r"\(?\d{2}\)?[\s.-]?\d{4}[\s.-]?\d{4}"
)


def mask_phone(phone: Optional[str]) -> str:
    """Mascara telefone mantendo apenas os ultimos 4 digitos.

    Returns "****XXXX" onde XXXX sao os ultimos 4 digitos.
    Se phone vazio/None, retorna "[PHONE]".
    """
    if not phone:
        return "[PHONE]"

    digits = re.sub(r"\D", "", str(phone))
    if len(digits) < 4:
        return "[PHONE]"

    last4 = digits[-4:]
    return f"****{last4}"


def mask_email(email: Optional[str]) -> str:
    """Mascara email mantendo primeira letra e dominio."""
    if not email or "@" not in email:
        return "[EMAIL]"
    local, domain = email.split("@", 1)
    if not local:
        return "[EMAIL]"
    return f"{local[0]}****@{domain}"


def _mask_match(match: "re.Match[str]") -> str:
    """Callback do re.sub que mascara cada match de telefone."""
    return mask_phone(match.group(0))


def sanitize_message(text: Optional[str], max_len: int = 80) -> str:
    """Sanitiza texto de mensagem: limita tamanho + mascara telefones/emails."""
    if not text:
        return "[empty]"

    s = str(text)
    s = _PHONE_RE.sub(_mask_match, s)
    s = re.sub(
        r"([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
        lambda m: mask_email(f"{m.group(1)}x@{m.group(2)}"),
        s,
    )
    if len(s) > max_len:
        s = s[:max_len] + f"... ({len(text)} chars)"
    return s
