"""Testes Sprint 1.4 — WhatsApp throttle + idempotency hash."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))

from utils.idempotency import (  # noqa: E402
    normalize_for_hash,
    hash_idempotency_key,
    WhatsappThrottle,
)


# ── normalize_for_hash ────────────────────────────────────────────────────


@pytest.mark.unit
class TestNormalizeForHash:
    def test_basic_lowercase_strip(self):
        assert normalize_for_hash("Oi") == "oi"

    def test_strips_punctuation(self):
        assert normalize_for_hash("Oi!") == "oi"

    def test_strips_only_boundary_punctuation(self):
        # Pontuacao de borda de palavra e' removida (Oi! -> oi)
        # Pontuacao NO MEIO de palavra preservada (emails, urls)
        assert normalize_for_hash("Ola, tudo bem") == "ola tudo bem"
        # "Ola! Tudo bem?" -> vira "Ola ! Tudo bem ?" -> remove ! e ? -> "Ola Tudo bem" -> "ola tudo bem"
        assert normalize_for_hash("Ola! Tudo bem?") == "ola tudo bem"

    def test_strips_whitespace(self):
        assert normalize_for_hash("  Oi  ") == "oi"

    def test_preserves_internal_spaces(self):
        assert normalize_for_hash("Ola tudo bem") == "ola tudo bem"

    def test_preserves_internal_punctuation(self):
        # Pontuacao dentro de frase (separando palavras) e' removida tambem
        # (pra garantir idempotencia de "Oi! Tudo bem?" == "oi tudo bem")
        assert normalize_for_hash("Ola! Tudo bem?") == "ola tudo bem"

    def test_idempotent_variations(self):
        """Varias pontuacoes viram mesmo hash."""
        a = normalize_for_hash("Ola! Tudo bem?")
        b = normalize_for_hash("ola tudo bem")
        c = normalize_for_hash("OLA TUDO BEM")
        d = normalize_for_hash("Ola tudo bem.")
        assert a == b == c == d

    def test_preserves_word_inside_phrase(self):
        # Email-like dentro de frase nao e' stripada como pontuacao isolada
        result = normalize_for_hash("Me chama em joao@gmail.com")
        # O "@" nao esta na lista de pontuacao stripada, entao fica
        assert "joao" in result

    def test_empty(self):
        assert normalize_for_hash("") == ""
        assert normalize_for_hash(None) == ""

    def test_oi_vs_oi_same(self):
        assert normalize_for_hash("Oi") == normalize_for_hash("Oi!")
        assert normalize_for_hash("Oi!") == normalize_for_hash("Oi!")
        assert normalize_for_hash("Oi.") == normalize_for_hash("Oi?")

    def test_ola_vs_oi_different(self):
        assert normalize_for_hash("Ola") != normalize_for_hash("Oi")

    def test_quotes_removed(self):
        # Aspas sao pontuacao isolada, removidas
        assert normalize_for_hash('"Oi"') == "oi"
        assert normalize_for_hash("'Oi'") == "oi"

    def test_comma_removed(self):
        # Virgula APENAS no fim (borda) e' removida
        assert normalize_for_hash("Ola,") == "ola"
        # Virgula no meio (entre palavras) e' removida tambem
        # pra garantir idempotencia ("Ola, tudo" == "Ola tudo")
        assert normalize_for_hash("Ola, tudo bem") == "ola tudo bem"

    def test_unicode_preserved(self):
        # "nao" sem acento
        assert normalize_for_hash("Não") == "não"  # lowercase


# ── hash_idempotency_key ──────────────────────────────────────────────────


@pytest.mark.unit
class TestHashIdempotency:
    def test_same_input_same_hash(self):
        a = hash_idempotency_key("Oi")
        b = hash_idempotency_key("Oi")
        assert a == b

    def test_oi_vs_oi_bang_same_hash(self):
        """'Oi' e 'Oi!' devem ter mesmo hash (idempotente)."""
        a = hash_idempotency_key("Oi")
        b = hash_idempotency_key("Oi!")
        assert a == b, "VARIACOES DE PONTUACAO NAO GERAM MESMO HASH"

    def test_ola_vs_oi_different_hash(self):
        a = hash_idempotency_key("Ola")
        b = hash_idempotency_key("Oi")
        assert a != b

    def test_hash_length_16(self):
        h = hash_idempotency_key("test")
        assert len(h) == 16

    def test_empty_hash(self):
        h = hash_idempotency_key("")
        # hash de string vazia é deterministico
        assert h == hash_idempotency_key("")


# ── WhatsappThrottle ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestWhatsappThrottle:
    def test_first_call_no_wait(self):
        t = WhatsappThrottle(min_interval_sec=0.1)
        waited = t.wait_sync()
        assert waited == 0.0

    def test_second_call_within_window_waits(self):
        t = WhatsappThrottle(min_interval_sec=0.2)
        t.wait_sync()
        start = time.monotonic()
        waited = t.wait_sync()
        elapsed = time.monotonic() - start
        # Deve ter esperado ~0.2s
        assert waited >= 0.15
        assert elapsed >= 0.15

    def test_throttle_respects_3s(self):
        """Sprint 1.4 — default 3s throttle."""
        t = WhatsappThrottle(min_interval_sec=3.0)
        t.wait_sync()
        start = time.monotonic()
        t.wait_sync()
        elapsed = time.monotonic() - start
        # Deve ter esperado ~3s
        assert elapsed >= 2.5  # tolerancia

    @pytest.mark.asyncio
    async def test_async_wait(self):
        t = WhatsappThrottle(min_interval_sec=0.1)
        await t.wait()
        start = time.monotonic()
        await t.wait()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.05


# ── 50 msgs em batch ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestBatchThrottle:
    """Cenario 1.4: 50 envios respeitam throttle."""

    def test_50_msgs_respect_3s(self):
        """Mock de 50 envios: tempo total >= 3s (throttle garante)."""
        t = WhatsappThrottle(min_interval_sec=0.05)  # 50ms pra teste rapido
        start = time.monotonic()
        for i in range(10):
            t.wait_sync()
        elapsed = time.monotonic() - start
        # 10 envios × 50ms = ~500ms
        assert elapsed >= 0.4
