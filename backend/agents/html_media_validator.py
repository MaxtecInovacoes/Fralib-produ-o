"""Media validations for generated HTML (images, videos, placeholders, URLs).

Fail-fast: não injeta placeholders nem imagens genéricas quando a mídia real falha.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from backend.pipeline_exceptions import ImageNotAvailableError

if TYPE_CHECKING:
    from typing import Any


_FORBIDDEN_MEDIA_SOURCES = (
    "placehold.co",
    "via.placeholder.com",
    "placeholder.com",
    "picsum.photos",
    "dummyimage.com",
    "fakeimg.pl",
    "source.unsplash.com",
)


def photo_urls(prd) -> list[str]:
    """Extract photo URLs from PRD."""
    raw = _get_field(prd, "photos", "fotos", default=[]) or []
    urls: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.startswith("http"):
            urls.append(item)
        elif isinstance(item, dict):
            url = item.get("url") or item.get("src") or item.get("regular")
            if isinstance(url, str) and url.startswith("http"):
                urls.append(url)
    return urls


def minimum_required_media(prd, photos: list[str]) -> int:
    """Require provided editorial media once the pipeline fetched usable photos."""
    explicit = _get_field(prd, "minimum_required_media", default=None)
    if isinstance(explicit, int) and explicit >= 0:
        return explicit
    if photos:
        return min(5, len(photos))
    return 0


def media_urls_from_html(html: str) -> set[str]:
    """Extract media URLs from HTML (img, source, url(), unsplash)."""
    raw_urls = set()
    for match in re.findall(
        r"""(?is)<img\b[^>]*?\bsrc=["']([^"']+)["']""", html or ""
    ):
        raw_urls.add(match.strip())
    for match in re.findall(
        r"""(?is)<source\b[^>]*\bsrcset=["']([^"']+)["']""", html or ""
    ):
        raw_urls.add(match.split()[0].strip())
    for match in re.findall(r"""(?is)url\(["']?([^"')]+)["']?\)""", html or ""):
        raw_urls.add(match.strip())
    for match in re.findall(
        r"""(?is)https://images\.unsplash\.com/[^\s"'<>),;]+""", html or ""
    ):
        raw_urls.add(match.strip())

    media_urls = set()
    for url in raw_urls:
        low = url.lower()
        if not low.startswith(("http://", "https://", "/")):
            continue
        if any(bad in low for bad in _FORBIDDEN_MEDIA_SOURCES):
            continue
        if low.endswith((".css", ".js", ".ico")):
            continue
        media_urls.add(url)
    return media_urls


def has_placeholder_media(html: str, text: str) -> bool:
    """Check if HTML contains placeholder media markers."""
    bodyish = re.sub(r"(?is)<script\b.*?</script>", " ", html or "")
    bodyish = re.sub(r"(?is)<style\b.*?</style>", " ", bodyish)
    low = bodyish.lower()
    if "ph-img" in low or "placeholder" in low:
        return True
    return bool(
        re.search(
            r"\[[^\]]*(?:16:9|4:3|imagem|image|foto|photo|piscina|pool)[^\]]*\]",
            text,
            re.I,
        )
    )


def validate_media_count(
    html: str, prd, photos: list[str]
) -> list[str]:
    """Validate media count meets minimum requirements."""
    problems: list[str] = []
    media_refs = media_urls_from_html(html)
    real_media_count = len(media_refs)
    min_required = minimum_required_media(prd, photos)
    if real_media_count < min_required:
        problems.append(
            f"HTML usou {real_media_count} midias finais; "
            f"minimo exigido={min_required}"
        )
    return problems


def validate_address_in_html(html: str, text: str, address: str, normalized_text: str) -> list[str]:
    """Check that real business address appears in visible HTML."""
    if not address:
        return []
    if _normalize(address) not in normalized_text:
        return ["Endereco real do lead nao aparece de forma visivel no HTML"]
    return []


def safe_photo_url(url: str, prd) -> str:
    """Return safe photo URL or raise when media is missing/unsafe."""
    low = (url or "").lower()
    if not url or any(bad in low for bad in _FORBIDDEN_MEDIA_SOURCES):
        raise ImageNotAvailableError(
            "safe_photo_url: URL de imagem ausente ou proibida.",
            context={"url": url, "segmento": _get_field(prd, "segmento", "segment", "nicho", default="")},
        )
    return url


def image_fallback_for_segment(prd) -> str:
    """Compatibility shim: image fallbacks are forbidden."""
    raise ImageNotAvailableError(
        "image_fallback_for_segment: fallback de imagem desativado.",
        context={"segmento": _get_field(prd, "segmento", "segment", "nicho", default="")},
    )


def _get_field(obj: Any, *names: str, default=None) -> Any:
    """Get value from dict or object attribute, trying multiple field names."""
    if isinstance(obj, dict):
        for name in names:
            value = obj.get(name)
            if value not in (None, "", [], {}):
                return value
        return default
    for name in names:
        value = getattr(obj, name, None)
        if value not in (None, "", [], {}):
            return value
    return default


def _normalize(value: str) -> str:
    """Normalize text for comparison (ASCII, lowercase, spaces)."""
    import unicodedata

    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
    return re.sub(r"\s+", " ", text).strip()
