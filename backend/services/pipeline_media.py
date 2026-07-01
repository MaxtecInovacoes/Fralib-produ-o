"""Media handling functions for pipeline PRD builder.

This module contains functions for handling editorial images, media URLs,
and text cleaning used across the pipeline.

Fail-fast: não usa fotos hardcoded. Se lead não tem fotos, lança erro.
"""

from __future__ import annotations

from urllib.parse import urlsplit

import re
from functools import lru_cache
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from backend.pipeline_exceptions import ImageNotAvailableError


NICHE_MEDIA_LIBRARY: dict[str, dict[str, Any]] = {}  # Deprecado: não usar mais fallback de fotos


def is_supported_editorial_image_url(url: str) -> bool:
    """Check if a URL points to a supported editorial image host.

    Args:
        url: The URL string to check.

    Returns:
        True if the URL is from Unsplash, Pexels, or Contentful.

    Example:
        >>> is_supported_editorial_image_url("https://images.unsplash.com/photo-123")
        True
        >>> is_supported_editorial_image_url("https://example.com/image.jpg")
        False
    """
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower()
    return host in {
        "images.unsplash.com",
        "images.pexels.com",
        "images.ctfassets.net",
    }


def normalize_editorial_image_url(url: str, *, og: bool = False) -> str:
    """Normalize an editorial image URL with standardized parameters.

    Adds or updates query parameters for format, crop, width, and quality.

    Args:
        url: The image URL to normalize.
        og: If True, sets dimensions for Open Graph images (1200x630).

    Returns:
        Normalized URL string or empty string if not supported.

    Example:
        >>> url = "https://images.unsplash.com/photo-123"
        >>> normalize_editorial_image_url(url)
        'https://images.unsplash.com/photo-123?auto=format&fit=crop&w=1600&q=80'
    """
    raw = str(url or "").strip()
    if not is_supported_editorial_image_url(raw):
        return ""
    parsed = urlparse(raw)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("auto", "format")
    query.setdefault("fit", "crop")
    query["w"] = "1200" if og else str(max(900, int(query.get("w") or 1600)))
    if og:
        query["h"] = "630"
    query.setdefault("q", "80")
    return urlunparse(parsed._replace(query=urlencode(query)))


@lru_cache(maxsize=256)
def editorial_image_reachable(url: str) -> bool:
    """Check if an editorial image URL is reachable via HTTP.

    Uses HEAD request first, then GET with Range header as fallback.

    Args:
        url: The image URL to check.

    Returns:
        True if the image is reachable (status < 400).

    Note:
        This function has HTTP side effects and is cached with LRU.
    """
    target = normalize_editorial_image_url(url)
    if not target:
        return False
    try:
        with httpx.Client(follow_redirects=True, timeout=4.0) as client:
            response = client.head(target)
            if response.status_code < 400:
                return True
            response = client.get(target, headers={"Range": "bytes=0-0"})
            return response.status_code < 400
    except Exception:
        return False


def media_defaults_for_segment(segmento: Any) -> dict[str, Any]:
    """DEPRECADO: Não use mais fotos hardcoded.

    Esta função agora lança erro em vez de retornar fallbacks.

    Raises:
        ImageNotAvailableError: Sempre — não há mais fallbacks de imagem.

    Use fotos reais do lead ou use unsplash_fetcher.buscar_fotos().
    """
    raise ImageNotAvailableError(
        f"media_defaults_for_segment: Sem fotos default para '{segmento}'.",
        context={
            "segmento": str(segmento),
            "acao": "Forneca fotos reais do lead ou use unsplash_fetcher.buscar_fotos()",
        },
    )


def deterministic_media_bundle(
    segmento: Any,
    raw_photos: Any,
    raw_og_image: Any = "",
) -> tuple[list[str], str]:
    """Build a deterministic media bundle from photos provided by lead.

    Fail-fast: se não houver fotos fornecidas, lança erro.
    Não usa mais fallbacks de fotos.

    Args:
        segmento: The business segment (informational only).
        raw_photos: List of photo URLs or dicts with url/src keys. REQUIRED.
        raw_og_image: Optional OG image URL.

    Returns:
        Tuple of (photos list, og_image URL).

    Raises:
        ImageNotAvailableError: Se raw_photos estiver vazio ou inválido.
    """
    photos = extract_media_urls(raw_photos)

    if not photos:
        raise ImageNotAvailableError(
            "deterministic_media_bundle: Nenhuma foto fornecida para o lead.",
            context={
                "segmento": str(segmento),
                "acao": "Forneca fotos reais do cliente ou use unsplash_fetcher.buscar_fotos()",
            },
        )

    og_image = normalize_editorial_image_url(raw_og_image, og=True)
    if not og_image or not editorial_image_reachable(og_image):
        # Usar primeira foto como OG se não fornecer uma
        og_image = normalize_editorial_image_url(photos[0], og=True)

    return photos[:8], og_image


def extract_media_urls(raw: Any) -> list[str]:
    """Extract and normalize media URLs from various input formats.

    Handles lists of strings or dicts with url/src/regular/full keys.

    Args:
        raw: List of URLs (strings) or dicts with image URLs.

    Returns:
        Deduplicated list of normalized reachable image URLs (max 8).

    Example:
        >>> urls = extract_media_urls([
        ...     "https://images.unsplash.com/photo-1",
        ...     {"url": "https://images.unsplash.com/photo-2"}
        ... ])
    """
    if not isinstance(raw, list):
        return []
    urls: list[str] = []
    for item in raw:
        if isinstance(item, str):
            parsed = urlsplit(item)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            normalized = normalize_editorial_image_url(item)
            if normalized and editorial_image_reachable(normalized):
                urls.append(normalized)
        elif isinstance(item, dict):
            url = item.get("url") or item.get("src") or item.get("regular") or item.get("full")
            parsed = urlsplit(str(url or ""))
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            normalized = normalize_editorial_image_url(url)
            if normalized and editorial_image_reachable(normalized):
                urls.append(normalized)
    return list(dict.fromkeys(urls))[:8]


def clean_public_text(value: Any) -> str:
    """Clean text for public display by removing special Unicode ranges.

    Removes private use area characters (E000-F8FF) commonly used
    in icon fonts, and normalizes whitespace.

    Args:
        value: The text value to clean.

    Returns:
        Cleaned text string safe for public display.

    Example:
        >>> clean_public_text("A  ·  B")
        'A B'
    """
    text_value = str(value or "")
    text_value = "".join(ch for ch in text_value if not (0xE000 <= ord(ch) <= 0xF8FF))
    return re.sub(r"\s+", " ", text_value.replace("·", " ")).strip()
