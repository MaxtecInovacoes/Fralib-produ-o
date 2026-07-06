"""Language guard for Portuguese-only outputs.

Centraliza a validação de idioma para evitar vazamento de CJK, cirilico,
arabe e copy claramente em ingles sem traducao no SDR e no builder.
"""

from __future__ import annotations

import re
import unicodedata


class LanguageGuard:
    _CJK_RE = re.compile(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]")
    _CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")
    _ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
    _WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]+")

    _ENGLISH_MARKERS = {
        "about",
        "and",
        "athletic",
        "book",
        "call",
        "consultation",
        "day",
        "evening",
        "free",
        "food",
        "for",
        "get",
        "good",
        "help",
        "hello",
        "hi",
        "here",
        "there",
        "learn",
        "more",
        "need",
        "now",
        "personalized",
        "page",
        "please",
        "best",
        "can",
        "results",
        "recovery",
        "that",
        "site",
        "this",
        "want",
        "schedule",
        "team",
        "services",
        "today",
        "thanks",
        "thank",
        "okay",
        "ok",
        "test",
        "training",
        "welcome",
        "with",
        "would",
        "could",
        "should",
        "morning",
        "afternoon",
        "contact",
        "your",
        "we",
        "you",
        "is",
        "are",
        "the",
        "our",
    }

    _PORTUGUESE_MARKERS = {
        "agendar",
        "agende",
        "atendimento",
        "cliente",
        "com",
        "claro",
        "certo",
        "dia",
        "entendi",
        "favor",
        "bom",
        "noite",
        "tarde",
        "oi",
        "contato",
        "consulta",
        "de",
        "do",
        "da",
        "em",
        "mais",
        "nutrição",
        "nutricao",
        "para",
        "plano",
        "resultados",
        "sim",
        "saiba",
        "serviço",
        "servico",
        "serviços",
        "servicos",
        "seu",
        "sua",
        "tudo",
        "vamos",
        "treino",
        "perfeito",
        "você",
        "voce",
        "whatsapp",
        "obrigado",
        "obrigada",
        "pode",
        "me",
        "por",
        "favor",
        "passar",
        "explicar",
        "olá",
        "ola",
    }

    _REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
        (re.compile(r"\bbook\s+now\b", re.IGNORECASE), "agende agora"),
        (re.compile(r"\blearn\s+more\b", re.IGNORECASE), "saiba mais"),
        (re.compile(r"\bcall\s+us\s+today\b", re.IGNORECASE), "fale conosco hoje"),
        (re.compile(r"\bconversa\s+us\s+today\b", re.IGNORECASE), "fale conosco hoje"),
        (re.compile(r"\bget\s+in\s+touch\b", re.IGNORECASE), "fale com a gente"),
        (re.compile(r"\bappointment\s+today\b", re.IGNORECASE), "agendamento hoje"),
        (re.compile(r"\bappointment\b", re.IGNORECASE), "agendamento"),
        (re.compile(r"\bgood\s+morning\b", re.IGNORECASE), "bom dia"),
        (re.compile(r"\bgood\s+afternoon\b", re.IGNORECASE), "boa tarde"),
        (re.compile(r"\bgood\s+evening\b", re.IGNORECASE), "boa noite"),
        (re.compile(r"\bthank\s+you\b", re.IGNORECASE), "obrigado"),
        (re.compile(r"\bthanks\b", re.IGNORECASE), "obrigado"),
        (re.compile(r"\bhello\b", re.IGNORECASE), "olá"),
        (re.compile(r"\bhi\b", re.IGNORECASE), "oi"),
        (re.compile(r"\bthere\b", re.IGNORECASE), "aí"),
        (re.compile(r"\bhere\b", re.IGNORECASE), "aqui"),
        (re.compile(r"\bplease\b", re.IGNORECASE), "por favor"),
        (re.compile(r"\bconversa\b", re.IGNORECASE), "fale"),
        (re.compile(r"\bus\b", re.IGNORECASE), "conosco"),
        (re.compile(r"\btoday\b", re.IGNORECASE), "hoje"),
        (re.compile(r"\bhelp\b", re.IGNORECASE), "ajuda"),
        (re.compile(r"\bneed\b", re.IGNORECASE), "preciso"),
        (re.compile(r"\bwant\b", re.IGNORECASE), "quero"),
        (re.compile(r"\bbest\b", re.IGNORECASE), "melhor"),
        (re.compile(r"\bfree\b", re.IGNORECASE), "grátis"),
        (re.compile(r"\bthis\b", re.IGNORECASE), "isso"),
        (re.compile(r"\bthat\b", re.IGNORECASE), "aquilo"),
        (re.compile(r"\bthis\s+is\s+a\s+test\b", re.IGNORECASE), "isso é um teste"),
        (re.compile(r"\bis\s+a\s+test\b", re.IGNORECASE), "é um teste"),
        (re.compile(r"\btest\b", re.IGNORECASE), "teste"),
        (re.compile(r"\bservices\b", re.IGNORECASE), "serviços"),
        (re.compile(r"\bconsultation\b", re.IGNORECASE), "consulta"),
        (re.compile(r"\bpersonalized\b", re.IGNORECASE), "personalizado"),
        (re.compile(r"\btraining\b", re.IGNORECASE), "treino"),
        (re.compile(r"\bresults\b", re.IGNORECASE), "resultados"),
        (re.compile(r"\brecovery\b", re.IGNORECASE), "recuperação"),
        (re.compile(r"\bnutrition\b", re.IGNORECASE), "nutrição"),
        (re.compile(r"\bfood\b", re.IGNORECASE), "alimentação"),
        (re.compile(r"\bschedule\b", re.IGNORECASE), "agende"),
        (re.compile(r"\bday\b", re.IGNORECASE), "dia"),
        (re.compile(r"\bmore\b", re.IGNORECASE), "mais"),
        (re.compile(r"\bwith\b", re.IGNORECASE), "com"),
        (re.compile(r"\byour\b", re.IGNORECASE), "seu"),
        (re.compile(r"\bour\b", re.IGNORECASE), "nosso"),
        (re.compile(r"\band\b", re.IGNORECASE), "e"),
        (re.compile(r"\bfor\b", re.IGNORECASE), "para"),
        (re.compile(r"\babout\b", re.IGNORECASE), "sobre"),
        (re.compile(r"\bnow\b", re.IGNORECASE), "agora"),
        (re.compile(r"\bcall\b", re.IGNORECASE), "fale"),
        (re.compile(r"\bbook\b", re.IGNORECASE), "agende"),
        (re.compile(r"\blearn\b", re.IGNORECASE), "saiba"),
        (re.compile(r"\bget\b", re.IGNORECASE), "fale"),
    )

    @classmethod
    def _normalize(cls, text: str | None) -> str:
        return unicodedata.normalize("NFKC", str(text or ""))

    @classmethod
    def _strip_foreign_scripts(cls, text: str) -> str:
        text = cls._CJK_RE.sub(" ", text)
        text = cls._CYRILLIC_RE.sub(" ", text)
        text = cls._ARABIC_RE.sub(" ", text)
        return text

    @classmethod
    def is_clean_portuguese(cls, text: str | None) -> bool:
        value = cls._normalize(text).strip()
        if not value:
            return True
        if cls._CJK_RE.search(value) or cls._CYRILLIC_RE.search(value) or cls._ARABIC_RE.search(value):
            return False

        words = [word.lower() for word in cls._WORD_RE.findall(value)]
        if not words:
            return True

        english_hits = sum(1 for word in words if word in cls._ENGLISH_MARKERS)
        portuguese_hits = sum(1 for word in words if word in cls._PORTUGUESE_MARKERS)

        if english_hits == 0:
            return True
        if portuguese_hits == 0:
            return False
        if english_hits >= 2 and english_hits >= portuguese_hits:
            return False
        return True

    @classmethod
    def sanitize_output(cls, text: str | None) -> str:
        value = cls._normalize(text).strip()
        if not value:
            return ""

        value = cls._strip_foreign_scripts(value)
        for pattern, replacement in cls._REPLACEMENTS:
            value = pattern.sub(replacement, value)

        value = re.sub(r"\s+", " ", value).strip(" \t\r\n-–—,;:./")
        if not value:
            return ""

        if cls.is_clean_portuguese(value):
            return value

        words = cls._WORD_RE.findall(value)
        if words:
            cleaned_words = [
                word
                for word in words
                if word.lower() not in cls._ENGLISH_MARKERS
            ]
            value = re.sub(r"\s+", " ", " ".join(cleaned_words)).strip(
                " \t\r\n-–—,;:./"
            )

        if not value:
            return ""
        return value if cls.is_clean_portuguese(value) else ""


__all__ = ["LanguageGuard"]
