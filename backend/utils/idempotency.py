"""Sprint 1.4: normalize_for_hash + throttle rate limit.

Problema P1:
  - 50 msgs em batch sem throttle = WhatsApp ban
  - Hash exato faz "Oi" e "Oi!" serem diferentes (idempotencia quebrada)

Fix:
  - normalize_for_hash(text): text.strip().lower().rstrip('.!?,' + aspas)
  - whatsapp_throttle: helper que garante min 3s entre envios
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from typing import Optional


# Pontuacao que deve ser removida antes/depois do texto (apenas bordas)
_PUNCT_RE = re.compile(r"^[\.\!\?\,\;\"\']+|[\.\!\?\,\;\"\']+$")


def normalize_for_hash(text: str) -> str:
    """Normaliza texto pra geracao de hash idempotente.

    Regras:
    1. Strip de bordas whitespace
    2. Lowercase
    3. Pontuacao ISOLADA (depois de letra + na borda) removida
    4. Pontuacao DENTRO de palavra preservada (emails, urls)

    Examples:
        >>> normalize_for_hash("Oi")
        'oi'
        >>> normalize_for_hash("Oi!")
        'oi'
        >>> normalize_for_hash("Ola.")
        'ola'
        >>> normalize_for_hash("  Oi?!  ")
        'oi'
        >>> normalize_for_hash("Ola! Tudo bem?")
        'ola tudo bem'
        >>> normalize_for_hash("Ola, tudo bem")
        'ola tudo bem'
    """
    if not text:
        return ""
    s = text.strip().lower()
    # Remove aspas (mais simples, nao interfere com regex de palavra)
    s = s.replace('"', " ").replace("'", " ")
    # Separa pontuacao adjacente a letra com espaco (ex: "Ola!" -> "Ola !")
    s = re.sub(r"([a-záéíóúãõâêôàç])\.", r"\1 .", s)
    s = re.sub(r"([a-záéíóúãõâêôàç])\,", r"\1 ,", s)
    s = re.sub(r"([a-záéíóúãõâêôàç])\!", r"\1 !", s)
    s = re.sub(r"([a-záéíóúãõâêôàç])\?", r"\1 ?", s)
    s = re.sub(r"([a-záéíóúãõâêôàç])\;", r"\1 ;", s)
    # Remove pontuacao que ficou sozinha (entre espacos ou borda)
    s = re.sub(r"(^|\s)[\.\!\?\,\;]+($|\s)", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def hash_idempotency_key(text: str) -> str:
    """Hash SHA256 do texto normalizado. Usado como dedup key."""
    normalized = normalize_for_hash(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


# ── Throttle ──────────────────────────────────────────────────────────────


class WhatsappThrottle:
    """Garante min N segundos entre envios WhatsApp.

    Uso:
        throttle = WhatsappThrottle(min_interval_sec=3.0)
        for msg in batch:
            await throttle.wait()
            await send(msg)
    """

    def __init__(self, min_interval_sec: float = 3.0):
        self.min_interval = min_interval_sec
        self._last_send: float = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> float:
        """Espera ate poder enviar. Retorna tempo esperado em segundos."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_send
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                await asyncio.sleep(wait_time)
                self._last_send = time.monotonic()
                return wait_time
            self._last_send = now
            return 0.0

    def wait_sync(self) -> float:
        """Versao sincrona. Retorna tempo esperado."""
        now = time.monotonic()
        elapsed = now - self._last_send
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            time.sleep(wait_time)
            self._last_send = time.monotonic()
            return wait_time
        self._last_send = now
        return 0.0
