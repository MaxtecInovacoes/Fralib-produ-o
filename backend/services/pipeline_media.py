"""Media handling functions for pipeline PRD builder.

This module contains functions for handling editorial images, media URLs,
and text cleaning used across the pipeline.
"""

from __future__ import annotations

from urllib.parse import urlsplit

import re
from functools import lru_cache
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx


NICHE_MEDIA_LIBRARY: dict[str, dict[str, Any]] = {
    "nutricionista": {
        "aliases": ("nutricionista", "nutricao", "nutrição", "nutricional"),
        "photos": [
            "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1505576399279-565b52d4ac71?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1467453678174-768ec283a940?auto=format&fit=crop&w=1600&q=80",
        ],
        "og_image": "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=1600&q=80",
    },
    "academia": {
        "aliases": ("academia", "fitness", "gym", "crossfit", "musculacao", "musculação"),
        "photos": [
            "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1571902943202-507ec2618e8f?auto=format&fit=crop&w=1600&q=80",
        ],
        "og_image": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=1600&q=80",
    },
    "clinica": {
        "aliases": ("clinica", "clínica", "medico", "médico", "saude", "saúde"),
        "photos": [
            "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1584515933487-779824d29309?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1666214280557-f1b5022eb634?auto=format&fit=crop&w=1600&q=80",
        ],
        "og_image": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=1600&q=80",
    },
}


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
    """Get default media library for a segment.

    Returns curated photos and OG image for the given segment,
    or generic defaults if segment not found.

    Args:
        segmento: The business segment to get defaults for.

    Returns:
        Dictionary with 'photos' and 'og_image' keys.

    Example:
        >>> defaults = media_defaults_for_segment("nutricionista")
        >>> "photos" in defaults
        True
    """
    from backend.services.pipeline_validators import normalize_segment

    normalized = normalize_segment(segmento)
    for key, item in NICHE_MEDIA_LIBRARY.items():
        aliases = {normalize_segment(alias) for alias in item.get("aliases") or ()}
        if normalized == normalize_segment(key) or normalized in aliases:
            return item
    return {
        "photos": [
            "https://images.unsplash.com/photo-1524758631624-e2822e304c36?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1600&q=80",
        ],
        "og_image": "https://images.unsplash.com/photo-1524758631624-e2822e304c36?auto=format&fit=crop&w=1600&q=80",
    }


def deterministic_media_bundle(
    segmento: Any,
    raw_photos: Any,
    raw_og_image: Any = "",
) -> tuple[list[str], str]:
    """Build a deterministic media bundle from photos and OG image.

    Merges provided photos with defaults, ensuring uniqueness and
    reachability. Selects OG image from photos or defaults.

    Args:
        segmento: The business segment for defaults.
        raw_photos: List of photo URLs or dicts with url/src keys.
        raw_og_image: Optional OG image URL.

    Returns:
        Tuple of (photos list, og_image URL).

    Example:
        >>> photos, og = deterministic_media_bundle("nutricionista", [], "")
        >>> len(photos) > 0
        True
    """
    photos = extract_media_urls(raw_photos)
    defaults = media_defaults_for_segment(segmento)
    default_photos = [
        normalized
        for raw in list(defaults.get("photos") or [])
        if (normalized := normalize_editorial_image_url(raw))
        and editorial_image_reachable(normalized)
    ]
    merged = list(dict.fromkeys(photos + default_photos))[:8]
    og_image = normalize_editorial_image_url(raw_og_image, og=True)
    if not og_image or not editorial_image_reachable(og_image):
        candidate = str((merged[:1] or [defaults.get("og_image") or ""])[0] or "")
        og_image = normalize_editorial_image_url(candidate, og=True)
    if og_image and og_image not in merged and editorial_image_reachable(og_image):
        merged = [og_image, *merged][:8]
    return merged, og_image


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
